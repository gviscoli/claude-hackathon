"""Tool: create_claim_record — persists the final decision to processed_claims/."""
import json
import sys
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed_claims"


def main(decision_json: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    decision = json.loads(decision_json)
    claim_id = decision.get("claim_id", "UNKNOWN")
    output_path = OUTPUT_DIR / f"{claim_id}.json"
    decision["written_at"] = datetime.now().isoformat()
    output_path.write_text(json.dumps(decision, indent=2))
    print(json.dumps({"success": True, "path": str(output_path), "claim_id": claim_id}))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: create_claim_record.py '<decision_json>'"}))
        sys.exit(1)
    main(sys.argv[1])
