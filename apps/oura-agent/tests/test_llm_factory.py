"""The Ollama model must not spend its whole output budget thinking.

glm-4.7-flash reasons before answering. On a real briefing (2026-09-23) it
used all 4096 output tokens on hidden reasoning (done_reason="length") and
returned an empty answer, twice in a row. Thinking is off unless asked for.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import llm_factory  # noqa: E402


@pytest.fixture
def ollama_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_CHAT_BASE_URLS", "http://gateway:9080")
    monkeypatch.delenv("OLLAMA_REASONING", raising=False)
    monkeypatch.setattr(llm_factory, "_pick_ollama_url", lambda urls: urls[0])


def test_build_chat_llm_ollama_disables_thinking_by_default(ollama_env):
    llm = llm_factory.build_chat_llm(model="unused", api_key="", temperature=0, max_tokens=4096)
    assert llm.reasoning is False


@pytest.mark.parametrize("value", ["true", "1", "yes"])
def test_build_chat_llm_ollama_thinking_can_be_enabled(ollama_env, monkeypatch, value):
    monkeypatch.setenv("OLLAMA_REASONING", value)
    llm = llm_factory.build_chat_llm(model="unused", api_key="", temperature=0, max_tokens=4096)
    assert llm.reasoning is True
