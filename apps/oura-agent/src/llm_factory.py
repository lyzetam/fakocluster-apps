"""LLM provider factory — switch the agent between Anthropic (Claude) and a
local Ollama model via environment variables.

Env:
    LLM_PROVIDER          "anthropic" (default) | "ollama"
    LLM_MODEL             Claude model name (used when provider == anthropic)
    OLLAMA_CHAT_MODEL     local model name    (used when provider == ollama;
                          default "glm-4.7-flash:latest" — present on ms1/ms2/ms3)
    OLLAMA_CHAT_BASE_URLS comma-separated Ollama endpoints tried in order until one
                          responds (default the ms1/ms2/ms3 homelab nodes)

Keeping this in one place means supervisor + specialists all honour the same
switch, so flipping LLM_PROVIDER=ollama moves the entire briefing pipeline
(routing, specialists, and Dr. Oura synthesis) onto the homelab — health data
never leaves the cluster.
"""

import logging
import os
import urllib.request

from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)

# Homelab Ollama nodes. glm-4.7-flash is the model present on all three, so
# whichever node answers first can serve the request.
DEFAULT_OLLAMA_URLS = (
    "http://ms1.landryzetam.net:11434,"
    "http://ms2.landryzetam.net:11434,"
    "http://ms3.landryzetam.net:11434"
)
DEFAULT_OLLAMA_MODEL = "glm-4.7-flash:latest"


def _pick_ollama_url(urls: list[str]) -> str:
    """Return the first Ollama endpoint that answers /api/tags, else the first."""
    for url in urls:
        try:
            urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=3)
            return url.rstrip("/")
        except Exception:
            continue
    logger.warning(f"No Ollama node responded; defaulting to {urls[0]}")
    return urls[0].rstrip("/")


def build_chat_llm(
    model: str,
    api_key: str | None = None,
    temperature: float = 0,
    max_tokens: int = 4096,
):
    """Build a chat LLM for the configured provider.

    Args:
        model: Claude model name (used only when provider == anthropic)
        api_key: Anthropic API key (anthropic only)
        temperature: Sampling temperature
        max_tokens: Max output tokens

    Returns:
        A LangChain chat model (ChatAnthropic or ChatOllama)
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        urls = [
            u.strip()
            for u in os.getenv("OLLAMA_CHAT_BASE_URLS", DEFAULT_OLLAMA_URLS).split(",")
            if u.strip()
        ]
        base_url = _pick_ollama_url(urls)
        ollama_model = os.getenv("OLLAMA_CHAT_MODEL", DEFAULT_OLLAMA_MODEL)
        logger.info(f"LLM provider=ollama model={ollama_model} url={base_url}")
        return ChatOllama(
            base_url=base_url,
            model=ollama_model,
            temperature=temperature,
            num_predict=max_tokens,  # Ollama's name for max output tokens
        )

    # Default: Anthropic
    kwargs = {"model": model, "temperature": temperature, "max_tokens": max_tokens}
    if api_key:
        kwargs["api_key"] = api_key
    logger.info(f"LLM provider=anthropic model={model}")
    return ChatAnthropic(**kwargs)
