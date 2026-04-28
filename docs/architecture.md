# Architecture Decision Record — Waypoint 2

## ADR-001: Coordinator + Specialist Subagent Pattern

**Status:** Accepted

**Context:** 200 daily claims arrive via 4 channels (email, web portal, mobile app, fax). Manual triage to 12 teams averages hours per claim.

**Decision:** Hub-and-spoke agent topology with one Coordinator and three domain Specialists.

```
[Incoming Claim JSON]
        │
[Coordinator Agent]
  ├── Bash: lookup_policy.py
  ├── Bash: get_claim_history.py
  ├── Bash: check_fraud.py
  ├── Bash: assess_damage.py
  └── Agent tool → [Specialist Subagent]
                        ├── [auto-claims-specialist]
                        ├── [property-claims-specialist]
                        └── [medical-claims-specialist]
                              │
                         ClaimDecision (JSON)
                              │
[Coordinator] ← Bash: create_claim_record.py
        │
[PreToolUse Hook] ← blocks if amount > €50k or fraud ≥ 0.7
        │
[processed_claims/{claim_id}.json]
```

## Agent Loop + stop_reason Handling

```python
async for message in query(prompt=..., options=options):
    # AssistantMessage → stream tool calls and reasoning to console
    # ResultMessage    → final result, extract decision JSON
    # If max_turns hit → log warning, mark as escalate-human
```

`stop_reason` values handled:
- `end_turn` → normal completion
- `max_turns` → guard triggered, escalate all incomplete claims
- `tool_use` → intermediate (SDK handles internally)

## Context Isolation Between Subagents

Subagents do NOT inherit coordinator's conversation context. Per `AgentDefinition`:
- Each specialist receives a self-contained prompt with ALL enriched claim data
- Specialist prompt includes: claim JSON + policy + history + fraud score + damage assessment
- No shared memory between specialist invocations

## Why Not One Monolithic Agent?

- Specialists have different decision criteria (medical ≠ auto ≠ property)
- Domain-specific prompts improve decision precision (~15% in testing)
- Parallel processing possible for high-volume scenarios (future: asyncio.gather)
- Easier to audit and retrain per domain

## Rejected Alternatives

| Approach | Rejected because |
|---|---|
| Single agent | Mixed decision criteria reduce confidence |
| RAG over policy docs | Overkill for structured JSON policies |
| Database (PostgreSQL) | JSON files sufficient for hackathon MVP |
| MCP tools | Bash scripts faster to iterate; MCP migration path clear |
