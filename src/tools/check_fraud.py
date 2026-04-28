"""Tool: check_fraud — scores a claim for fraud risk (0.0-1.0)."""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def score_claim(claim: dict, history: dict, patterns: dict) -> dict:
    score = 0.0
    indicators = []

    desc_lower = claim.get("description", "").lower()
    for kw in patterns.get("high_risk_keywords", []):
        if kw in desc_lower:
            score += 0.15
            indicators.append(f"High-risk keyword detected: '{kw}'")

    customer_id = claim.get("customer_id", "")
    customer_history = history.get(customer_id, [])
    fraud_flags = sum(1 for c in customer_history if c.get("fraud_flag"))
    if fraud_flags > 0:
        score += 0.25
        indicators.append(f"Previous fraud flag(s) on account: {fraud_flags}")

    recent = [c for c in customer_history if c["date"] >= "2025-04-28"]
    if len(recent) >= 3:
        score += 0.20
        indicators.append(f"3+ claims in last 12 months: {len(recent)}")
    elif len(recent) >= 2:
        score += 0.10
        indicators.append(f"2 claims in last 12 months")

    if not claim.get("attachments"):
        score += 0.15
        indicators.append("No supporting documentation attached")

    estimated = claim.get("estimated_amount", 0)
    policies_path = DATA_DIR / "policies.json"
    policies = json.loads(policies_path.read_text())
    policy = policies.get(claim.get("policy_id", ""), {})
    coverage_limit = policy.get("coverage_limit", float("inf"))
    if coverage_limit > 0 and estimated / coverage_limit > 0.85:
        score += 0.15
        indicators.append(f"Claim amount is {estimated/coverage_limit:.0%} of coverage limit")

    score = min(score, 1.0)
    thresholds = patterns.get("escalation_thresholds", {})

    return {
        "fraud_score": round(score, 2),
        "indicators": indicators,
        "requires_investigation": score >= thresholds.get("fraud_score", 0.7),
    }


def main(claim_file: str) -> None:
    claim = json.loads(Path(claim_file).read_text())
    history = json.loads((DATA_DIR / "claims_history.json").read_text())
    patterns = json.loads((DATA_DIR / "fraud_patterns.json").read_text())
    result = score_claim(claim, history, patterns)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: check_fraud.py <claim_file_path>"}))
        sys.exit(1)
    main(sys.argv[1])
