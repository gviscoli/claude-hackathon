# The Mandate — Waypoint 1

## What the Agent Decides Autonomously

| Decision | Conditions |
|---|---|
| **fast-track** | Policy active, claim type covered, amount ≤ €10,000, fraud score < 0.3, confidence ≥ 0.8, docs attached |
| **investigate** | Fraud score 0.3–0.69, amount €10k–€50k, incomplete documentation, 2nd claim in 12 months |
| **deny** | Policy inactive/expired, claim type not covered by policy, fraud score ≥ 0.7, incident predates policy |

## What Always Escalates to Human

| Trigger | Threshold |
|---|---|
| Claim payout | > €50,000 |
| Fraud score | ≥ 0.7 |
| Agent confidence | < 0.6 |
| Claims in 12 months | ≥ 3 |
| Previous fraud flag on account | any |

## What the Agent Must NOT Touch

- Legal review decisions (denied claims with legal liability)
- Claims involving fatalities or severe personal injury
- Any claim requiring medical record access beyond the submitted invoice
- Regulatory reporting (IVASS notifications)
- Direct communication with claimants (all outbound comms go through human ops team)

## Explicit Non-Automation Boundaries

1. **No PII export**: Agent cannot send policy or customer data to external endpoints
2. **No override of deny decisions**: Once denied, only a human supervisor can reverse
3. **No settlement negotiation**: Agent only recommends payout; no negotiation with claimants
4. **Audit trail mandatory**: Every decision must be written to processed_claims/ before the session ends
