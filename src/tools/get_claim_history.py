"""Tool: get_claim_history — returns past claims for a given customer_id."""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def main(customer_id: str) -> None:
    history_path = DATA_DIR / "claims_history.json"
    history = json.loads(history_path.read_text())

    claims = history.get(customer_id, [])
    fraud_flags = sum(1 for c in claims if c.get("fraud_flag"))
    total_paid = sum(c["amount"] for c in claims if c["decision"] in ("paid", "fast-track"))
    recent_claims = [c for c in claims if c["date"] >= "2025-04-28"]

    result = {
        "customer_id": customer_id,
        "total_claims": len(claims),
        "fraud_flags": fraud_flags,
        "total_paid_eur": total_paid,
        "claims_last_12_months": len(recent_claims),
        "history": claims,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: get_claim_history.py <customer_id>"}))
        sys.exit(1)
    main(sys.argv[1])
