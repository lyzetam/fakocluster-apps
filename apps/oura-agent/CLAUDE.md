# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Oura-agent is a Discord bot powered by Claude that answers natural language health questions using Oura Ring data. It implements a **hierarchical multi-agent architecture** where specialist agents handle domain-specific queries and a supervisor agent orchestrates routing.

## Build & Run Commands

```bash
# Local development
python -m src.main                    # Start polling loop
RUN_ONCE=true python -m src.main      # Single poll cycle (testing)

# Docker
docker build -t lzetam/oura-agent:latest .
docker push lzetam/oura-agent:latest

# Database migration (memory tables)
python scripts/init_memory_tables.py

# Syntax validation
python -m py_compile src/main.py src/agents/*.py src/config.py database/data_quality.py

# Import test
python -c "from src.agents import SupervisorAgent; print('OK')"
```

## Multi-Agent Architecture

```
Discord #health channel
    ↓ polling (30s)
┌────────────────────────────────────────────────────────────────────┐
│                      SUPERVISOR AGENT                               │
│  src/agents/supervisor.py                                          │
│  • Routes queries to specialist agents based on intent             │
│  • Handles multi-domain queries (parallel agent calls)             │
│  • Synthesizes responses from multiple specialists                 │
└──────────────────────────┬─────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┬───────────────────┐
        ↓                  ↓                  ↓                   ↓
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ SLEEP ANALYST │  │ FITNESS COACH │  │ MEMORY KEEPER │  │ DATA AUDITOR  │
│    AGENT      │  │    AGENT      │  │    AGENT      │  │    AGENT      │
├───────────────┤  ├───────────────┤  ├───────────────┤  ├───────────────┤
│ • Sleep data  │  │ • Activity    │  │ • Goal mgmt   │  │ • Freshness   │
│ • Stages      │  │ • Readiness   │  │ • Recall      │  │ • Quality     │
│ • Trends      │  │ • Workouts    │  │ • Insights    │  │ • Validation  │
│ • Quality     │  │ • Recovery    │  │ • Baselines   │  │ • Sync status │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
        │                  │                  │                   │
        └──────────────────┼──────────────────┴───────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL + PGVECTOR                            │
│  database/queries.py (55+ query methods)                           │
│  database/data_quality.py (freshness validation)                   │
│  19 Oura tables + memory tables                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Specialist Agents

| Agent | File | Domain | Example Queries |
|-------|------|--------|-----------------|
| SleepAnalystAgent | `src/agents/sleep_analyst.py` | Sleep data, stages, quality | "How did I sleep?", "My sleep trends" |
| FitnessCoachAgent | `src/agents/fitness_coach.py` | Activity, readiness, workouts | "Should I work out?", "My step count" |
| MemoryKeeperAgent | `src/agents/memory_keeper.py` | Goals, recall, baselines | "Set a goal for 8h sleep", "What did you tell me about HRV?" |
| DataAuditorAgent | `src/agents/data_auditor.py` | Data quality, sync status | "Is my ring syncing?", "Why is my data old?" |

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | Entry point, polling loop, message orchestration |
| `src/agents/supervisor.py` | Supervisor agent - routes to specialists |
| `src/agents/base.py` | BaseAgent abstract class for all agents |
| `src/agents/sleep_analyst.py` | Sleep analysis specialist |
| `src/agents/fitness_coach.py` | Fitness coaching specialist |
| `src/agents/memory_keeper.py` | Memory management specialist |
| `src/agents/data_auditor.py` | Data quality auditing specialist |
| `src/config.py` | Config from AWS Secrets Manager + env fallback |
| `database/queries.py` | All Oura data queries (async SQLAlchemy) |
| `database/data_quality.py` | DataQualityValidator for freshness checks |
| `memory/working.py` | LangGraph PostgresSaver checkpointer |
| `memory/episodic.py` | pgvector semantic search for past conversations |
| `discord/client.py` | Discord API (fetch, send, react) |

## Environment Variables

Required:
- `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_HEALTH_CHANNEL_ID`
- `ANTHROPIC_API_KEY`
- `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`
- `OLLAMA_BASE_URL`

Optional:
- `POLL_INTERVAL` (default: 30s)
- `MESSAGE_WINDOW_MINUTES` (default: 30)
- `LLM_MODEL` (default: claude-sonnet-4-20250514)
- `RUN_ONCE` (true for single-poll testing)

## Memory Systems

1. **Working Memory** - LangGraph checkpointer for conversation state
   - Thread ID: `oura-health-{user_id}-{channel_id}`
   - Persists across restarts

2. **Episodic Memory** - pgvector semantic search
   - Table: `health_episodic_memory`
   - 768-dim embeddings via Ollama nomic-embed-text
   - Enables "What did you tell me about HRV last week?"

3. **Long-Term Memory** - User goals and baselines
   - Tables: `health_user_goals`, `health_baselines`

## Data Quality Validation

The `DataQualityValidator` in `database/data_quality.py` ensures agents acknowledge stale data:

| Data Type | Freshness Threshold |
|-----------|-------------------|
| Sleep/Activity | ≤2 days |
| Daily scores | ≤1 day |
| Workouts | ≤7 days |
| VO2 Max | ≤30 days |

All specialist agents validate data quality before responding and include staleness warnings.

## Discord Integration

- **Polling-based** (not webhooks) - checks every 30s
- **Message filtering**: non-bot, recent, unprocessed (no 🩺 reaction)
- **Response format**: Rich embeds with color-coded health status
- **Processing marker**: Adds 🩺 reaction to skip on next poll

## Database Tables

**Oura Data (19 tables):** `oura_sleep_periods`, `oura_daily_sleep`, `oura_activity`, `oura_workouts`, `oura_readiness`, `oura_stress`, `oura_resilience`, `oura_vo2_max`, `oura_spo2`, `oura_sessions`, etc.

**Memory Tables:** `health_episodic_memory`, `health_user_goals`, `health_baselines`

## Agent Guardrails

Each specialist agent has guardrails in its system prompt:
- No medical diagnoses (escalate serious concerns to doctors)
- Oura is a wellness device disclaimer
- Data privacy guidelines
- Domain boundaries (stay in lane)
- Data staleness acknowledgment

## Routing Examples

The supervisor routes based on query intent:

| Query | Routed To |
|-------|-----------|
| "How did I sleep?" | sleep_analyst |
| "Should I work out?" | fitness_coach |
| "Set a goal for 10k steps" | memory_keeper |
| "Is my ring syncing?" | data_auditor |
| "Sleep and activity trends" | sleep_analyst, fitness_coach |
| "Hello!" | supervisor (direct) |

## K8s Deployment

Manifests in `fako-cluster` repo:
- Namespace: `oura-agent`
- External Secrets: `oura-agent/discord`, `oura-agent/anthropic`, `postgres/app-user`
- Health endpoint: `/health` on port 8080
- Single replica (Discord polling pattern)
