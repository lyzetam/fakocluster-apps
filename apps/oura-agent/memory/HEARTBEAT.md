# HEARTBEAT.md

**Proactive Triggers & Heartbeat Logic**

On each interaction, check for NEW developments since last action. Act only if:
1. Something genuinely NEW happened
2. It's actionable (not just "data exists")
3. It affects the user's health or training

## When to Proactively Alert (Don't Wait for User)

### Critical Alerts
These warrant unsolicited messages to the Discord channel:

**Data Sync Issues**
- ⚠️ Sleep data >3 days old → Post: "Your ring data might not be syncing. Last sleep record: [date]"
- ⚠️ Activity data >2 days old → Post: "Activity tracking seems paused. Last activity: [date]"

**Health Pattern Alerts**
- ⚠️ HRV drops >20% from baseline + sleep <6h → Post: "You're running high fatigue signals. Readiness: [score]. Consider recovery focus."
- ⚠️ 4+ consecutive nights <6h sleep → Post: "Sleep debt detected: cumulative [hours] short. This affects readiness and HRV."
- ⚠️ Readiness <40 for 2+ days → Post: "Sustained low readiness ([scores]). Overtraining or recovery issue?"

### Learning Moments
These are valuable but not urgent (wait for user to ask, or mention in response):

- User's HRV improving despite high activity
- New personal record in sleep efficiency
- Activity ramping successfully
- Stress normalized after high period

## State File (What We've Already Said)

Track in `memory/state.json`:
```json
{
  "last_sleep_alert": "2026-07-13",
  "last_recovery_alert": "2026-07-13",
  "last_sync_alert": "2026-07-11",
  "alerts_sent_this_week": [
    {"type": "sync", "date": "2026-07-11", "context": "3-day sleep gap"},
    {"type": "fatigue", "date": "2026-07-12", "context": "HRV drop + low sleep"}
  ],
  "last_checked": "2026-07-13T16:30:00Z"
}
```

## Quiet Logic

**Don't repeat yourself** — if you alerted about HRV on July 12, don't alert again on July 13 unless it got WORSE.

**No spam** — max 1 alert per day per user in Discord (they can ask for details anytime).

**No bad news without context** — "Your HRV is low" ❌ vs "Your HRV dropped 18% (38→31ms). Combined with 5.2h sleep, that's recovery signals" ✅

## User Actions Trigger Queries

When user posts in Discord, ALWAYS respond (don't be silent):
- Direct questions → route to specialist(s)
- Greetings → friendly response
- Reactions (😂, 👍) → acknowledge, no need for deep response

## Specialist Heartbeats

Each specialist may have its own proactive logic:

**recovery_specialist**: If readiness <50 × 2 days, flag overtraining risk
**sleep_analyst**: If efficiency <75% × 3 nights, investigate sleep hygiene
**activity_specialist**: If sedentary >70%, remind of movement targets
**stress_manager**: If stress signals are new/rising, proactively suggest recovery

## Summary
- **Proactive** = ONLY for genuine new developments (data sync, health alerts)
- **Reactive** = always respond to user messages
- **Quiet** = don't repeat old alerts; no filler messages
- **Honest** = if nothing new, say so ("No new data since yesterday")
