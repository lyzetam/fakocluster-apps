"""A blank model reply must not become a blank Dr. Oura briefing.

On the homelab Ollama model, one real briefing in three came back as an empty
string with no error (2026-09-23), and the daily report went out without it.
"""

import sys
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.supervisor import invoke_nonempty  # noqa: E402


class FakeLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        return AIMessage(content=self.replies.pop(0))


@pytest.mark.asyncio
async def test_invoke_nonempty_retries_once_after_blank_reply():
    llm = FakeLLM(["", "# Briefing"])
    assert await invoke_nonempty(llm, [HumanMessage(content="go")]) == "# Briefing"
    assert llm.calls == 2


@pytest.mark.asyncio
async def test_invoke_nonempty_treats_whitespace_as_blank():
    llm = FakeLLM(["  \n", "# Briefing"])
    assert await invoke_nonempty(llm, [HumanMessage(content="go")]) == "# Briefing"


@pytest.mark.asyncio
async def test_invoke_nonempty_returns_first_reply_when_not_blank():
    llm = FakeLLM(["# Briefing", "unused"])
    assert await invoke_nonempty(llm, [HumanMessage(content="go")]) == "# Briefing"
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_invoke_nonempty_gives_up_after_attempts():
    llm = FakeLLM(["", ""])
    assert await invoke_nonempty(llm, [HumanMessage(content="go")], attempts=2) == ""
    assert llm.calls == 2
