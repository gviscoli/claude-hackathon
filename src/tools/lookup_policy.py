"""Tool: lookup_policy — returns policy info for a given policy_id."""
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def main(policy_id: str) -> None:
    policies_path = DATA_DIR / "policies.json"
    policies = json.loads(policies_path.read_text())

    if policy_id not in policies:
        result = {"error": f"Policy {policy_id} not found", "found": False}
    else:
        result = {"found": True, "policy": policies[policy_id]}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: lookup_policy.py <policy_id>"}))
        sys.exit(1)
    main(sys.argv[1])
