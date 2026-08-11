# Deep Agent Architecture (Migration Guide)

## Overview

This document describes the **Deep Agent version** of oura-agent using LangChain's `deepagents` framework.

### Why Deep Agent?

| Aspect | LangGraph (Old) | Deep Agent (New) |
|--------|-----------------|------------------|
| **Lines of Code** | ~3000 | ~500 |
| **Specialist Definition** | Python classes | Dict config |
| **Behavior Definition** | Hardcoded prompts | Instruction markdown files |
| **Orchestration** | Manual LangGraph graph | Automatic (Claude decides) |
| **Memory** | Manual checkpointer + pgvector | Built-in long-term memory |
| **Planning** | Custom | Built-in `write_todos` tool |
| **Filesystem** | Manual | Virtual filesystem |

**Key Difference:** Code-driven → Instruction-driven

## Architecture

```
Master Agent (Claude Sonnet)
    ├─ sleep_analyst         [sleep data, quality, trends]
    ├─ activity_specialist   [steps, intensity, workouts]
    ├─ readiness_advisor     [recovery status, exercise readiness]
    ├─ heart_health_monitor  [HR, HRV, cardiovascular]
    ├─ stress_manager        [stress, mental recovery]
    ├─ recovery_specialist   [training load, sleep debt]
    ├─ memory_keeper         [goals, recall, baselines]
    └─ data_auditor          [data freshness, sync]
         ↓
    PostgreSQL (55+ queries)
         ↓
    Discord
```

## Key Files

### Code
- **`src/deepagent_main.py`** — Main entry point, tool definitions, polling loop
- **`src/config.py`** — Config loading (unchanged)
- **`discord/client.py`** — Discord API (unchanged)
- **`database/queries.py`** — Database queries (unchanged)

### Behavior (Instruction Files)
- **`memory/SOUL.md`** — Agent identity, voice, boundaries
- **`memory/AGENTS.md`** — Routing rules, specialist descriptions, response structure
- **`memory/HEARTBEAT.md`** — Proactive triggers, when to alert vs. wait
- **`memory/state.json`** — Tracking what agent has already said (dedupe, context)

## How It Works

### Query Flow

1. **User sends message** in Discord #health channel
2. **Polling loop** fetches message, passes to `agent.ainvoke()`
3. **Master Agent (Claude)** reads:
   - System prompt (high-level instructions)
   - SOUL.md (identity, voice)
   - AGENTS.md (routing rules, specialist list)
   - Message history
4. **Claude decides** which specialist(s) to call based on:
   - Specialist descriptions in AGENTS.md
   - Query intent
   - Complexity (single vs. multi-domain)
5. **Specialists run in parallel** via `asyncio.gather()`:
   - Each calls their tools (database queries)
   - Each produces a structured response
6. **Claude synthesizes** specialist outputs into one coherent answer
7. **Response sent** to Discord
8. **Conversation saved** to episodic memory for future recall

### Example: "How did I sleep and am I ready to train?"

```
User: "How did I sleep and am I ready to train?"
   ↓
Master Agent reads AGENTS.md routing rules
   ↓
Route to: sleep_analyst, readiness_advisor
   ↓
PARALLEL:
  - sleep_analyst.get_last_night_sleep() → "7.2h, 85 score, 22% deep..."
  - readiness_advisor.get_daily_readiness() → "72/100, good for moderate intensity"
   ↓
Claude synthesizes:
  "You had good sleep (7.2h, solid deep sleep). Readiness is 72/100 — good for 
  moderate intensity workout, but not ideal for peak performance day. Light 
  cardio or strength work recommended."
   ↓
Send to Discord + save conversation
```

## Behavior Definition (The Novel Part)

Instead of hardcoding routing logic in Python:

```python
# OLD (LangGraph)
class SupervisorAgent:
    def route_query(self, query):
        if "sleep" in query:
            return "sleep_analyst"
        elif "workout" in query:
            return "fitness_coach"
```

We define rules in **AGENTS.md**:

```markdown
# AGENTS.md
| Query | Specialist |
| "How did I sleep?" | sleep_analyst |
| "Should I work out?" | readiness_advisor |
| "Sleep + readiness?" | sleep_analyst + readiness_advisor |
```

**Claude reads AGENTS.md and decides routing.** This is:
- ✅ Maintainable (edit markdown, not Python)
- ✅ Debuggable (see the routing rules plainly)
- ✅ Flexible (Claude handles edge cases)
- ✅ Transparent (rules visible to team)

## Running the Deep Agent

### Install
```bash
pip install deepagents langchain-anthropic
```

### Local Development
```bash
# Single poll cycle (testing)
RUN_ONCE=true python -m src.deepagent_main

# Continuous polling
python -m src.deepagent_main
```

### Kubernetes Deployment
```bash
# Build image
docker build -t lzetam/oura-agent:deepagent-latest .

# Push
docker push lzetam/oura-agent:deepagent-latest

# Deploy (fako-cluster)
kubectl set image deployment/oura-agent -n oura-agent \
  oura-agent=lzetam/oura-agent:deepagent-latest

# Verify
kubectl logs -n oura-agent -l app=oura-agent -f
```

## Scaling & Extending

### Adding a New Specialist

1. **Define in `src/deepagent_main.py`:**
```python
{
    "name": "nutrition_tracker",
    "description": "Tracks food intake, macros, and nutrition patterns",
    "system_prompt": "You are a nutrition specialist...",
    "tools": [get_nutrition_data, analyze_macros],
}
```

2. **Add to AGENTS.md:**
```markdown
| "What should I eat?" | nutrition_tracker |
| "My energy is low" | nutrition_tracker + energy_advisor |
```

3. **Implement tools** (query your nutrition database).

### Adding a New Tool

1. **Define in `OuraToolFactory.get_*_tools()`:**
```python
@tool
async def get_vo2_max_trends() -> str:
    """Fetch VO2 max trends"""
    data = await queries.get_vo2_max_trends()
    return format_vo2_data(data)
```

2. **Attach to specialist** in subagents list.

3. **Claude automatically discovers it** via tool descriptions (docstrings).

## Memory Management

### Working Memory
- Built-in: conversation state per thread_id
- Persists within a thread
- Thread ID: `oura-{user_id}-{channel_id}`

### Long-term Memory
- Files: SOUL.md, AGENTS.md, HEARTBEAT.md, state.json
- Loaded at startup
- Updated after each interaction
- Enables personalization & deduplication

### State File Updates
```json
{
  "last_sleep_alert": "2026-07-13",
  "alerts_sent": [...],
  "users": {
    "123456789": {
      "last_interaction": "2026-07-13T15:45:00Z",
      "known_baselines": { "hrv": 42, "resting_hr": 58 }
    }
  }
}
```

**Why?** Avoid repeating alerts. Track what you've already told each user.

## Debugging

### Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python -m src.deepagent_main
```

### Check which specialist was called:
Logs will show: `[master_agent] route decision: sleep_analyst,readiness_advisor`

### Inspect tool calls:
Deep Agent middleware logs all tool invocations. Watch for:
- Which tools each specialist called
- Query execution time
- Tool response format

## Migration from LangGraph

If you're coming from the old `src/main.py`:

| Old Component | Maps To |
|---------------|---------|
| `SupervisorAgent` | Master agent system prompt + AGENTS.md routing |
| `SleepAnalystAgent` | sleep_analyst subagent + SOUL.md voice |
| `BaseAgent` | Deep agent framework (no class needed) |
| Manual routing logic | AGENTS.md + Claude's decision |
| Checkpointer | Built-in memory system |
| Message processing loop | `polling_loop()` (largely same) |

## Troubleshooting

### "Agent doesn't route correctly"
→ Check AGENTS.md routing rules. Make sure specialist descriptions are clear.

### "Same alert keeps firing"
→ Update `memory/state.json` to track what you've already alerted about.

### "Response doesn't synthesize well"
→ Tweak SOUL.md voice or AGENTS.md specialist descriptions. Let Claude read clearer intent.

### "Performance is slow"
→ Parallel specialist execution should be fast. Check if tools (DB queries) are slow.
