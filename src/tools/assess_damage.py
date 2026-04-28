"""Tool: assess_damage — validates damage estimate against policy coverage."""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def main(policy_id: str, claim_type: str, estimated_amount: float) -> None:
    policies = json.loads((DATA_DIR / "policies.json").read_text())
    policy = policies.get(policy_id)

    if not policy:
        print(json.dumps({"error": f"Policy {policy_id} not found"}))
        return

    if not policy.get("active"):
        print(json.dumps({
            "covered": False,
            "reason": "Policy is inactive / expired",
            "recommended_payout": 0.0,
        }))
        return

    covered_items = policy.get("covered_items", [])
    type_coverage_map = {
        "auto": ["collision", "theft", "fire"],
        "property": ["fire", "flood", "theft", "earthquake", "storm"],
        "medical": ["hospitalization", "surgery", "emergency", "specialist-visits"],
    }
    required = type_coverage_map.get(claim_type, [])
    has_coverage = any(item in covered_items for item in required)

    if not has_coverage:
        print(json.dumps({
            "covered": False,
            "reason": f"Claim type '{claim_type}' not covered under this policy",
            "recommended_payout": 0.0,
        }))
        return

    deductible = policy.get("deductible", 0)
    coverage_limit = policy.get("coverage_limit", 0)
    payout = max(0.0, min(estimated_amount - deductible, coverage_limit - deductible))

    print(json.dumps({
        "covered": True,
        "coverage_limit": coverage_limit,
        "deductible": deductible,
        "estimated_amount": estimated_amount,
        "recommended_payout": round(payout, 2),
        "within_limits": estimated_amount <= coverage_limit,
    }))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(json.dumps({"error": "Usage: assess_damage.py <policy_id> <claim_type> <amount>"}))
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
