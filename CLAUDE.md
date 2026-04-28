# CLAUDE.md — Insurance Claims Agentic Solution

## Project
Scenario 5 hackathon: agentic triage of insurance claims using Claude Agent SDK.
Decisions: fast-track / investigate / deny / escalate-human.

## Stack
- Runtime: Python 3.12 (Windows, terminale cp1252 → forzare `PYTHONIOENCODING=utf-8`)
- AI: Claude Agent SDK (`claude-agent-sdk >= 0.2.111`)
- Provider: Anthropic API **oppure** AWS Bedrock (selezionato via `.env`)
- Model testato: `eu.anthropic.claude-3-7-sonnet-20250219-v1:0` su Bedrock `eu-central-1`
- Tools: custom Bash scripts in `src/tools/`
- Data: JSON files in `src/data/`
- Tests: pytest (17 test, tutti deterministici — non richiedono API key)

## Architecture
- **Coordinator**: `src/agents/coordinator.py` — reads claim, enriches context, routes to specialist
- **Specialists**: `AgentDefinition` in coordinator — auto / property / medical
- **Hooks**: `src/agents/hooks.py` — PreToolUse blocks high-value & PII; audit log asincrono
- **Tools**: called via `Bash` tool: `python src/tools/<tool>.py <args>`

## Run Commands

```bash
# Unit test (no API key needed)
PYTHONIOENCODING=utf-8 pytest tests/ -x -q

# Singola claim
PYTHONIOENCODING=utf-8 python -m src.main src/data/incoming_claims/claim_001_auto.json

# Tutti i claim
PYTHONIOENCODING=utf-8 python -m src.main

# Eval scorecard
PYTHONIOENCODING=utf-8 python eval/eval_harness.py
```

## Tool Conventions

Tutti i tool script in `src/tools/`:
- Accettano argomenti CLI, stampano JSON su stdout
- Exit 0 successo, exit 1 errore
- Non scrivono file (eccetto `create_claim_record.py`)

## Hook: _extract_json_from_command
Il hook `block_high_value_auto_approve` usa `_extract_json_from_command()` che gestisce
**due formati** di quoting che l'agente può produrre:
- Format A: `create_claim_record.py '{"key": "val"}'`  (single quote)
- Format B: `create_claim_record.py "{\"key\": \"val\"}"` (double quote + escape)

## Escalation Rules (verificate prima di scrivere la decisione)
- `recommended_payout > 50000` → escalate-human
- `fraud_score >= 0.7` → escalate-human  ← anche se decision è "deny"
- `confidence < 0.6` → escalate-human
- `policy.active == false` → deny

## Risultati Eval (run 2026-04-28)
| Claim | Tipo | Decisione | Conf | Payout | Fraud |
|---|---|---|---|---|---|
| CLM-2026-001 | auto | fast-track | 0.95 | €2,500 | 0.00 |
| CLM-2026-002 | property | investigate | 0.88 | €25,500 | 0.05 |
| CLM-2026-003 | medical | fast-track | 0.95 | €5,700 | 0.00 |
| CLM-2026-004 | auto (adversarial) | escalate-human | 0.97 | — | 1.00 |

**Scorecard: 100% accuracy · 100% escalation quality · 0% false confidence**

## Important
- Never commit `.env`
- Provider: set `ANTHROPIC_API_KEY` (Anthropic) oppure `CLAUDE_CODE_USE_BEDROCK=1` + credenziali AWS
- Bedrock: Claude Sonnet 4 (`*-sonnet-4-*`) non disponibile in EU — usare Claude 3.7 Sonnet
- Max iterations guard: `max_turns=20` in `ClaudeAgentOptions`
- Subagents do NOT inherit coordinator context — pass all data in subagent prompt
- Every decision must be written to `src/data/processed_claims/{claim_id}.json`
- Audit log in `audit.log` (root) — JSONL, ogni Bash call tracciata
