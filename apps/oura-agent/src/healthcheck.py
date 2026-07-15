"""Health check endpoint for Kubernetes.

Provides /health and /ready endpoints for K8s probes.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Response, Request, HTTPException
from pydantic import BaseModel
import hmac
import hashlib

from database.connection import test_connection
from src.config import get_config

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    database: str
    details: Optional[dict] = None


class DiscordMessage(BaseModel):
    """Discord webhook message payload."""

    user_id: str
    channel_id: str
    content: str
    username: Optional[str] = None


class DailySummaryRequest(BaseModel):
    """Request for a Dr. Oura daily clinical briefing.

    The oura-collector passes the full set of metrics it already gathered for
    the date so the specialists analyze grounded data instead of re-querying.
    """

    date: str
    metrics: dict


# Global state for health checks
_health_state = {
    "database_ok": False,
    "discord_ok": False,
    "last_poll": None,
}

# Global agent references (set by main.py)
_agent = None
_discord_client = None


def update_health_state(
    database_ok: Optional[bool] = None,
    discord_ok: Optional[bool] = None,
    last_poll: Optional[str] = None,
):
    """Update the health state."""
    if database_ok is not None:
        _health_state["database_ok"] = database_ok
    if discord_ok is not None:
        _health_state["discord_ok"] = discord_ok
    if last_poll is not None:
        _health_state["last_poll"] = last_poll


def set_agent_dependencies(agent, discord_client):
    """Set agent and Discord client for webhook processing.

    Called by main.py after agents are initialized.
    """
    global _agent, _discord_client
    _agent = agent
    _discord_client = discord_client
    logger.info("Agent dependencies set for webhook processing")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Health check server starting...")
    yield
    logger.info("Health check server stopping...")


app = FastAPI(
    title="Oura Health Agent",
    description="Health check endpoints for Oura Health Agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthStatus)
async def health_check(response: Response):
    """Health check endpoint for liveness probe.

    Returns:
        HealthStatus with current health state
    """
    # Basic liveness check - just verify the service is running
    return HealthStatus(
        status="healthy",
        database="unknown",  # Don't check DB for liveness
        details={
            "service": "oura-health-agent",
            "last_poll": _health_state.get("last_poll"),
        },
    )


@app.get("/ready", response_model=HealthStatus)
async def readiness_check(response: Response):
    """Readiness check endpoint for K8s readiness probe.

    Checks database connectivity and other dependencies.

    Returns:
        HealthStatus with dependency states
    """
    try:
        config = get_config()
        db_ok = await test_connection(config.database.connection_string)
        update_health_state(database_ok=db_ok)
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        db_ok = False

    if not db_ok:
        response.status_code = 503
        return HealthStatus(
            status="unhealthy",
            database="disconnected",
            details={
                "database_ok": False,
                "discord_ok": _health_state.get("discord_ok", False),
            },
        )

    return HealthStatus(
        status="ready",
        database="connected",
        details={
            "database_ok": True,
            "discord_ok": _health_state.get("discord_ok", True),
            "last_poll": _health_state.get("last_poll"),
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "oura-health-agent",
        "status": "running",
        "endpoints": ["/health", "/ready", "/webhook/discord", "/daily-summary"],
    }


@app.post("/daily-summary")
async def daily_summary(req: DailySummaryRequest):
    """Produce a Dr. Oura clinical briefing for a day's metrics.

    Called by the oura-collector when building the daily health report. Routes
    the metrics through the domain specialists, then Dr. Oura synthesizes.

    Returns:
        {"summary": "...clinical briefing..."}
    """
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent not initialized yet")
    try:
        metrics_json = json.dumps(req.metrics, default=str, indent=2)
        summary = await _agent.generate_doctor_briefing(
            date_str=req.date, metrics_json=metrics_json
        )
        return {"summary": summary}
    except Exception as e:
        logger.error(f"daily-summary error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/discord")
async def discord_webhook(message: DiscordMessage):
    """Discord webhook endpoint for receiving messages.

    Instead of polling Discord, this webhook receives messages pushed
    directly to the agent. Much simpler and instant response.

    Usage:
    ```
    curl -X POST http://agent:8080/webhook/discord \
      -H "Content-Type: application/json" \
      -d '{
        "user_id": "123456",
        "channel_id": "789",
        "content": "How did I sleep?"
      }'
    ```

    Args:
        message: DiscordMessage with user_id, channel_id, content

    Returns:
        {"status": "ok", "response": "..."}
    """
    try:
        if not _agent or not _discord_client:
            raise HTTPException(
                status_code=503,
                detail="Agent not initialized yet"
            )

        logger.info(
            f"Webhook message from {message.username or message.user_id}: "
            f"{message.content[:50]}..."
        )

        # Process message through supervisor agent
        response = await _agent.process_message(
            message=message.content,
            user_id=message.user_id,
            channel_id=message.channel_id,
            session_id=None,
        )

        # Send response back to Discord
        if response:
            await _discord_client.send_health_response(
                channel_id=message.channel_id,
                user_id=message.user_id,
                response_text=response,
            )
            logger.info(f"Sent response to Discord")
        else:
            logger.warning(f"Agent returned empty response")

        return {
            "status": "ok",
            "response": response[:100] if response else "No response",
        }

    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def run_health_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the health check server.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning")


async def run_health_server_async(host: str = "0.0.0.0", port: int = 8080):
    """Run the health check server asynchronously.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    import uvicorn

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
