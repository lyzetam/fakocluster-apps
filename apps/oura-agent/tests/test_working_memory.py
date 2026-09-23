"""Working memory must survive its database connection being dropped.

Reproduces the 2026-09 failure: the checkpointer held one connection for the
life of the pod, Postgres closed it, and every later briefing raised
"the connection is closed" until the pod was replaced.

Needs a real Postgres: set OURA_AGENT_TEST_PG to a psycopg connection string.
"""

import os
import sys
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory.working import WorkingMemory  # noqa: E402

PG = os.environ.get("OURA_AGENT_TEST_PG")
pytestmark = pytest.mark.skipif(not PG, reason="OURA_AGENT_TEST_PG not set")

CONFIG = {"configurable": {"thread_id": "t1", "checkpoint_ns": ""}}


def _kill_other_backends() -> int:
    with psycopg.connect(PG, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        ).fetchall()
    return len(rows)


@pytest.mark.asyncio
async def test_working_memory_checkpointer_recovers_after_connection_killed():
    wm = WorkingMemory(PG)
    await wm.setup()
    try:
        saver = await wm.get_checkpointer()
        await saver.aget_tuple(CONFIG)

        assert _kill_other_backends() >= 1

        # Must not raise "the connection is closed".
        await saver.aget_tuple(CONFIG)
    finally:
        await wm.close()


@pytest.mark.asyncio
async def test_working_memory_clear_thread_recovers_after_connection_killed():
    wm = WorkingMemory(PG)
    await wm.setup()
    try:
        _kill_other_backends()
        assert await wm.clear_thread("u1", "c1") is True
    finally:
        await wm.close()
