"""Health check endpoint for Kubernetes.

Provides /health and /ready endpoints for K8s probes.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Response
from pydantic import BaseModel

from database.connection import test_connection
from src.config import get_config

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    database: str
    details: Optional[dict] = None


# Global state for health checks
_health_state = {
    "database_ok": False,
    "discord_ok": False,
    "last_poll": None,
}


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
        "endpoints": ["/health", "/ready"],
    }


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
