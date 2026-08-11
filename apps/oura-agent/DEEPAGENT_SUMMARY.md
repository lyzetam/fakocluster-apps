# Deep Agent Scaffold Summary

## What Was Built

A **complete Deep Agent refactor** of oura-agent with **8 specialist subagents** covering ALL health data sources:

### Specialists

1. **sleep_analyst** — Sleep periods, stages, quality, trends, efficiency
2. **activity_specialist** — Daily activity, steps, intensity, workouts, movement
3. **readiness_advisor** — Recovery status, exercise readiness, training load
4. **heart_health_monitor** — Heart rate, HRV, cardiovascular age, resting HR
5. **stress_manager** — Stress levels, mental recovery, stress management
6. **recovery_specialist** — Sleep debt, training load, recovery days
7. **memory_keeper** — Goals, recalls, baselines, personal history
8. **data_auditor** — Data freshness, sync status, quality validation

### Files Created

**Code:**
- `src/deepagent_main.py` — Main entry point (500 lines, fully documented)

**Behavior (Instruction Files — the innovation):**
- `memory/SOUL.md` — Agent identity, voice, boundaries
- `memory/AGENTS.md` — Routing rules, specialist descriptions, response structure
- `memory/HEARTBEAT.md` — Proactive triggers, alert logic
- `memory/state.json` — Tracking what agent has already said

**Documentation:**
- `CLAUDE_DEEPAGENT.md` — Architecture, scaling, debugging guide
- `DEEPAGENT_SUMMARY.md` — This file

## Key Improvements Over LangGraph

| Metric | LangGraph | Deep Agent | Improvement |
|--------|-----------|-----------|------------|
| **Code Lines** | ~3,000 | ~500 | -83% |
| **Complexity** | Custom orchestration | Framework handles it | Much simpler |
| **Adding Specialist** | New class + register | Dict + AGENTS.md entry | Faster |
| **Behavior Changes** | Edit Python | Edit markdown | No deploy needed |
| **Built-in Features** | Manual | Planning, filesystem, memory | Out-of-box |
| **Readability** | Scattered logic | Centralized AGENTS.md | Easier to understand |

## Architecture Comparison

### LangGraph (Old)
```
User Message
   ↓
SupervisorAgent.process_message()
   ├─ route_query() [LLM call]
   ├─ call_specialists() [parallel]
   ├─ synthesize_response() [LLM call]
   └─ Manual routing logic
   ↓
Discord
```

### Deep Agent (New)
```
User Message
   ↓
Agent.ainvoke()
   ├─ Claude reads SOUL.md (voice)
   ├─ Claude reads AGENTS.md (routing rules)
   ├─ Claude routes to specialist(s)
   ├─ Specialists run in parallel
   ├─ Claude synthesizes
   └─ Built-in memory/filesystem
   ↓
Discord
```

**The key: Claude handles routing automatically** based on AGENTS.md descriptions. No custom orchestration code.

## How to Deploy

### Step 1: Install Dependencies
```bash
pip install deepagents langchain-anthropic asyncio
```

### Step 2: Run Locally (Testing)
```bash
# Single poll
RUN_ONCE=true python -m src.deepagent_main

# Continuous
python -m src.deepagent_main
```

### Step 3: Deploy to Kubernetes
```bash
# Update image in deployment
kubectl set image deployment/oura-agent -n oura-agent \
  oura-agent=lzetam/oura-agent:deepagent-latest

# Verify
kubectl logs -n oura-agent -l app=oura-agent -f
```

### Step 4: Update Discord
The agent automatically runs with 8 specialists. No changes to Discord setup needed.

## Quick Start for Development

### To Add a New Specialist

1. **Define subagent** in `deepagent_main.py`:
```python
{
    "name": "your_specialist",
    "description": "What this specialist does",
    "system_prompt": "...",
    "tools": [your_tools],
}
```

2. **Add routing** in `memory/AGENTS.md`:
```markdown
| "Your query type" | your_specialist |
```

3. **Done.** Claude automatically routes to it.

### To Change Behavior

Edit `memory/AGENTS.md` or `memory/SOUL.md` — **no code deploy needed!**

Changes take effect immediately in next run.

## Behavior Innovation: Instruction Files

Instead of hardcoded routing logic, behavior is in **markdown files**:

**SOUL.md** — Agent identity
- "You are a health coach"
- "Be data-grounded"
- "Don't diagnose"

**AGENTS.md** — Routing rules
- Single-domain queries → one specialist
- Multi-domain → multiple specialists
- Response structure

**HEARTBEAT.md** — Proactive alerts
- When to alert without being asked
- Don't spam; only new developments
- Track what you've already said

**state.json** — Memory of what you've done
- Last alert timestamp
- User baselines
- Interaction history

This is the **OpenClaw/Pundit pattern** mentioned in the essentials.

## Data Sources Covered

The 8 specialists collectively handle:

✅ Sleep periods (+ timeseries with new fields)
✅ Daily activity (+ MET timeseries with new fields)
✅ Daily readiness (+ new contributors)
✅ Workouts
✅ Heart rate & HRV
✅ Stress data
✅ Recovery metrics
✅ Cardiovascular age
✅ Sleep efficiency
✅ Training load

**Plus:** Memory system (goals, recalls), Data quality validation

## Next Steps

1. **Test locally** — Run `RUN_ONCE=true python -m src.deepagent_main`
2. **Build Docker image** — `docker build -t lzetam/oura-agent:deepagent .`
3. **Deploy to K8s** — Update image, verify logs
4. **Monitor behavior** — Adjust AGENTS.md/SOUL.md based on Discord feedback
5. **Extend** — Add more specialists as more data sources come online

## Support

See `CLAUDE_DEEPAGENT.md` for:
- Full architecture walkthrough
- Scaling & extending guide
- Troubleshooting
- Migration from LangGraph
