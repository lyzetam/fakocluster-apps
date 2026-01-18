
## Tech Debt: Family Manager → Oura Agent Delegation

**Created**: 2026-01-18

### Problem
Both `family-manager-bot` and `oura-agent` respond to health queries in TheZetams `#health` channel (shared 2109Homebot token).

### Current Behavior
- User: "how did I sleep last night?"
- Family Manager: Generic response asking for data
- Oura Agent: Actual Oura data response (correct)

### Desired Behavior
Family Manager should detect health-related intents and delegate to Oura Health Agent.

### Options
1. **Intent routing**: Family Manager detects health intent → calls oura-agent API
2. **Agent registry**: Shared registry to avoid duplicate responses  
3. **Channel separation**: Family Manager ignores #health channel
4. **Separate bots**: Each service gets its own Discord bot token

### Related
- `apps/oura-agent/` - Multi-agent health system
- `~/dev/family-manager-bot/` - Family bot (separate repo)
