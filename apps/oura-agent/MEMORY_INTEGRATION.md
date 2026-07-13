# Supabase Memory Integration for Oura Agent

## What Can Agents Remember Now?

Agents have **4 types of memory** stored in Supabase:

### 1. **Episodic Memory** (Conversations)
*What did I tell you and when?*

```
User: "Remember when you told me to increase deep sleep?"

Agent: Queries conversations table → finds similar past responses
       → "Yes! On July 10, I suggested better sleep hygiene..."
```

**Table:** `conversations`
- Every query/response pair stored with embedding
- Searchable: "Find all times I mentioned HRV"
- Timestamped: know when advice was given
- Specialist tracking: which agents were involved

### 2. **Semantic Memory** (Goals & Baselines)
*What are your personal targets and baseline metrics?*

```
User: "Set a goal: 8 hours sleep"
Agent: Saves to user_profiles.goals
       Future responses: "You have an 8h sleep goal..."

Agent analyzing sleep: "Your HRV baseline is 42ms. Today: 39ms (slight dip)"
```

**Table:** `user_profiles`
- User goals: sleep hours, step targets, workout frequency, etc.
- Personal baselines: HRV, resting HR, deep sleep %, efficiency %
- Preferences: "prefer concise responses", "early bird"
- Agent state: tracking what we've learned about this user

### 3. **Procedural Memory** (What Worked)
*Did my recommendations actually help?*

```
Agent (July 10): "Consider a rest day today (readiness: 42)"
User (July 12): "Thanks, I rested and feel much better!"

Agent learns: Rest day recommendations → positive outcomes for this user
Future: Weights this recommendation more heavily for them
```

**Tables:**
- `agent_decisions` — Track what we recommended and the outcome
- `agent_learning` — Aggregate patterns (sleep advice works, rest days effective)

### 4. **Procedural Memory** (Alert Deduplication)
*What have I already alerted you about?*

```
Agent (July 12): Posts "Your HRV dropped 20% — recovery needed"
Agent (July 13): Checks alerts_history → "Already alerted about this yesterday"
                 Only alerts if: NEW development or >24hrs since last alert
```

**Table:** `alerts_history`
- Timestamp of each alert sent
- Type: "sync_alert", "fatigue_alert", "overtraining_alert"
- Context: what triggered it
- Prevents spam: enforces min hours between same alert type

---

## How to Set Up

### 1. Create Supabase Project

```bash
# Go to supabase.com and create a new project
# Get your credentials:
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..."  # Anon key (for client use)
```

### 2. Run Migrations

```bash
# Copy the SQL from supabase_migrations.sql
# Go to Supabase dashboard → SQL Editor → New Query
# Paste and run all the SQL

# This creates:
# - user_profiles
# - conversations
# - alerts_history
# - agent_decisions
# - agent_learning
# Plus indexes, RLS policies, and triggers
```

### 3. Set Environment Variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="eyJhbGciOiJIUzI1NiIs..."
```

### 4. Update Agent Entry Point

```bash
# Use the memory-integrated version:
python -m src.deepagent_with_memory

# Not: python -m src.deepagent_main (old version without memory)
```

---

## Usage Examples

### Example 1: User Sets a Goal

```
Discord:
User: "I want to sleep 8 hours every night"

Agent (sleep_analyst):
  1. Extracts goal: {"sleep_hours": 8}
  2. Calls: memory.update_user_goals(user_id, {"sleep_hours": 8})
  3. Saves to Supabase: user_profiles.goals
  4. Responds: "✓ Goal set: 8h sleep. I'll track this!"

Next time user asks about sleep:
  Agent retrieves goal → "You have an 8h goal. Last night: 7.2h (close!)"
```

### Example 2: Agent Recalls Past Advice

```
Discord:
User: "I'm having trouble sleeping. What did you recommend before?"

Agent (memory_keeper):
  1. Queries: conversations table for sleep-related responses
  2. Finds: ["Sleep hygiene tips", "Bedtime routine advice", "Screen time recommendations"]
  3. Responds: "Yes! I've given you this advice before:
              • Stick to a consistent bedtime
              • No screens 30min before sleep
              • Keep room cool (65-68°F)
              Would you like me to expand on any of these?"
```

### Example 3: Learning from Outcomes

```
Discord (July 10):
Agent: "Your readiness is 40 — consider an easy day today"
User: "OK, taking it easy"

Discord (July 13):
User: "That rest day really helped! My sleep improved after that"

Agent learns:
  1. Logs to agent_decisions: recommendation_type="rest_day", outcome="positive"
  2. Increments specialist_effectiveness["readiness_advisor"]
  3. Next time similar situation → higher confidence in rest day recommendation
```

### Example 4: Alert Deduplication

```
Discord (July 11, 9:00 AM):
Agent: "⚠️ Your sleep data is 3 days old. Ring may not be syncing."

Discord (July 11, 11:00 AM):
User asks: "How did I sleep?"
Agent checks: should_alert(user_id, "sync_alert", min_hours=24)
  → Returns False (already alerted 2 hours ago)
  → Doesn't spam the same alert
  → Only mentions data freshness in response

Discord (July 12, 11:00 AM):
  → 26 hours passed → can alert again if still stale
```

---

## Database Schema Reference

### user_profiles
```
{
  "user_id": "123456",           # Discord user ID
  "goals": {
    "sleep_hours": 8,            # How many hours they want
    "steps": 10000,              # Daily step target
    "deep_sleep_pct": 20         # Target deep sleep %
  },
  "baselines": {
    "hrv_ms": 42,                # Their normal HRV
    "resting_hr": 58,            # Their normal resting HR
    "sleep_efficiency": 85       # Their normal efficiency %
  },
  "preferences": {
    "prefer_concise": true,      # Response style
    "early_bird": true           # When they're most active
  },
  "agent_state": {
    "last_sleep_alert": "2026-07-12",
    "preferred_specialists": ["sleep_analyst", "readiness_advisor"]
  }
}
```

### conversations
```
{
  "id": "uuid",
  "user_id": "123456",
  "query": "How did I sleep?",
  "response": "Great! 7.2h with 22% deep sleep...",
  "specialists": ["sleep_analyst"],
  "embedding": [0.12, -0.45, ...],  # 768-dim vector for similarity search
  "created_at": "2026-07-13T10:30:00Z"
}
```

### alerts_history
```
{
  "id": "uuid",
  "user_id": "123456",
  "alert_type": "sync_alert",          # Type of alert
  "context": {
    "days_old": 3,
    "last_sync": "2026-07-10"
  },
  "created_at": "2026-07-11T09:00:00Z"
}
```

### agent_decisions
```
{
  "id": "uuid",
  "user_id": "123456",
  "decision_type": "recommend_rest_day",
  "context": {
    "readiness": 40,
    "hrv_drop": 20,
    "sleep_hours": 5.8
  },
  "outcome": {
    "user_feedback": "positive",
    "follow_up_readiness": 65,
    "follow_up_hrv": 45
  },
  "created_at": "2026-07-10T...",
  "updated_at": "2026-07-13T..."  # When outcome was logged
}
```

### agent_learning
```
{
  "user_id": "123456",
  "learned_patterns": {
    "high_stress_correlates_with": ["poor_sleep", "low_hrv"],
    "recovery_takes_about": 3,  # days
    "rest_day_effectiveness": 0.92
  },
  "specialist_effectiveness": {
    "sleep_analyst": 0.94,      # % of advice that had positive outcomes
    "readiness_advisor": 0.88,
    "memory_keeper": 0.95       # (goal-setting works great)
  },
  "user_response_patterns": {
    "prefers_concise": true,
    "responds_to_data": true,
    "actionable_advice_preferred": true
  },
  "total_interactions": 42,
  "last_updated": "2026-07-13T..."
}
```

---

## The Benefits

### For the Agent
✅ **Personalization** — "Based on your 8h sleep goal and HRV baseline..."
✅ **Context** — Recalls past advice and outcomes
✅ **Intelligence** — Learns which recommendations work for this user
✅ **Efficiency** — Doesn't repeat alerts uselessly
✅ **Growth** — Improves over time with more interactions

### For the User
✅ **"Remember when..."** — Long-term conversation continuity
✅ **Goal tracking** — Agent tracks progress toward goals
✅ **Personalized advice** — Not generic, tailored to their patterns
✅ **No spam** — Smart alert deduplication
✅ **Learning** — Agent gets better at helping them specifically

---

## Migration Path

### Phase 1: Core Memory (this week)
- Deploy Supabase + schema
- Integrate conversations (episodic memory)
- Add goal setting (semantic memory)

### Phase 2: Learning (next week)
- Track agent decisions and outcomes
- Calculate specialist effectiveness
- Extract learned patterns

### Phase 3: Advanced (following week)
- Vector similarity search for "remember when..."
- Predictive recommendations based on patterns
- Autonomously update baselines from data

---

## Next Steps

1. **Create Supabase project** at supabase.com
2. **Run migrations** from `supabase_migrations.sql`
3. **Update environment variables** in deployment
4. **Switch to `deepagent_with_memory.py`** entry point
5. **Test**: Set a goal, give advice, verify it's saved
6. **Monitor**: Check Supabase dashboard for data flow

All your existing Oura data + Discord integration stays the same. The memory layer wraps around it.
