# Insurance Claims Agentic Solution

**Scenario 5** — Claude Agent SDK · Python · Hackathon 2026-04-28

An autonomous agent that classifies, triages, and routes 200+ daily insurance claims — making real decisions (fast-track / investigate / deny / escalate), not just chatting.

## Architecture

```
[Incoming Claim JSON]  →  [Coordinator Agent]
                               │
               ┌───────────────┼───────────────┐
          [auto-claims]  [property-claims]  [medical-claims]
               │
          [PreToolUse Hooks]  ←  blocks high-value / fraud
               │
          [processed_claims/{id}.json]
```

## Setup (2 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY

# 3. Run the demo (all 4 sample claims)
python -m src.main

# 4. Run a single claim
python -m src.main src/data/incoming_claims/claim_001_auto.json
```

## Key Files

| File | Purpose |
|---|---|
| `src/agents/coordinator.py` | Coordinator agent + specialist definitions + hooks config |
| `src/agents/hooks.py` | PreToolUse safety hooks (high-value block, PII protection, audit log) |
| `src/tools/*.py` | Custom tools called via Bash (policy lookup, fraud check, damage assessment) |
| `src/data/incoming_claims/` | Sample claims to process |
| `src/data/processed_claims/` | Output decisions (written after processing) |
| `docs/mandate.md` | What the agent can/cannot do autonomously |
| `docs/architecture.md` | ADR with agent-loop diagram |
| `eval/eval_harness.py` | Scorecard: accuracy, escalation quality, adversarial pass rate |

## Running Tests

```bash
# Unit tests (tools only — no API calls)
pytest tests/test_tools.py -v

# Adversarial eval set
pytest tests/adversarial/ -v

# Eval harness (requires processed claims from a prior run)
python eval/eval_harness.py
```

## Decision Logic

| Decision | Conditions |
|---|---|
| fast-track | Amount ≤ €10k, fraud < 0.3, docs attached, policy active |
| investigate | Fraud 0.3–0.69, amount €10k–€50k, or incomplete docs |
| deny | Inactive policy, not covered, fraud ≥ 0.7 |
| escalate-human | Payout > €50k, confidence < 0.6, or previous fraud flag |

## Human-in-the-Loop

`PreToolUse` hooks intercept `create_claim_record.py` calls and:
1. **Block** if `recommended_payout > €50,000` or `fraud_score ≥ 0.7`
2. **Inject** a `systemMessage` telling the agent to set `decision = escalate-human`
3. **Audit log** every tool call to `audit.log`

## Next Steps (Post-Hackathon)

- Replace JSON files with PostgreSQL + pgvector for policy/RAG search
- Add real document parsing (PDF → text via PyMuPDF)
- Webhook notifications to ops team for escalations
- Feedback loop: human overrides update labeled eval dataset
