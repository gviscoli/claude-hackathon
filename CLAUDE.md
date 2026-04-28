# CLAUDE.md — Insurance Claims Agentic Solution

## Project
Scenario 5 hackathon: agentic triage of insurance claims using Claude Agent SDK.
Decisions: fast-track / investigate / deny / escalate-human.

## Stack
- Runtime: Python 3.12
- AI: Claude Agent SDK (`claude-agent-sdk`) — `claude-sonnet-4-20250514`
- Tools: custom Bash scripts in `src/tools/`
- Data: JSON files in `src/data/`
- Tests: pytest

## Architecture
- **Coordinator**: `src/agents/coordinator.py` — reads claim, enriches context, routes to specialist
- **Specialists**: `AgentDefinition` in coordinator — auto / property / medical
- **Hooks**: `src/agents/hooks.py` — PreToolUse blocks high-value & PII; audit log
- **Tools**: called via `Bash` tool: `python src/tools/<tool>.py <args>`

## Custom Commands

### Process a single claim
```
/process-claim src/data/incoming_claims/claim_001_auto.json
```

### Run eval harness
```
/eval
```

## Tool Conventions

All tool scripts:
- Accept CLI args, print JSON to stdout
- Exit 0 on success, exit 1 on error
- Never write files (except `create_claim_record.py`)

## Escalation Rules (must check before writing decision)
- `recommended_payout > 50000` → escalate-human
- `fraud_score >= 0.7` → escalate-human
- `confidence < 0.6` → escalate-human
- `policy.active == false` → deny

## Important
- Never commit `.env`
- Model: `claude-sonnet-4-20250514`
- Max iterations guard: `max_turns=20` in `ClaudeAgentOptions`
- Subagents do NOT inherit coordinator context — pass all data in subagent prompt
- Every decision must be written to `src/data/processed_claims/{claim_id}.json`
