"""Entry point for the Insurance Claims Agentic Solution."""
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Windows terminals default to cp1252 — force UTF-8 so emoji in agent output don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent.parent


def print_summary(results: list[dict]) -> None:
    if not results:
        print("\nNo decisions recorded.")
        return

    print("\n" + "=" * 80)
    print("CLAIMS PROCESSING SUMMARY")
    print("=" * 80)
    header = f"{'Claim ID':<20} {'Decision':<18} {'Conf':>6} {'Payout (€)':>12} {'Fraud':>7}"
    print(header)
    print("-" * 80)

    icons = {
        "fast-track": "✓",
        "investigate": "?",
        "deny": "✗",
        "escalate-human": "!",
    }

    for r in results:
        icon = icons.get(r.get("decision", ""), " ")
        payout = r.get("recommended_payout")
        payout_str = f"{payout:,.0f}" if payout is not None else "N/A"
        print(
            f"{icon} {r.get('claim_id', 'N/A'):<18} "
            f"{r.get('decision', 'N/A'):<18} "
            f"{r.get('confidence', 0):.2f}   "
            f"{payout_str:>12} "
            f"{r.get('fraud_score', 0):.2f}"
        )
    print("=" * 80)

    total_payout = sum(r.get("recommended_payout", 0) or 0 for r in results)
    escalations = sum(1 for r in results if r.get("decision") == "escalate-human")
    print(f"\nTotal potential payout: €{total_payout:,.0f}")
    print(f"Escalations to human: {escalations}/{len(results)}")


async def demo_single(claim_file: str) -> None:
    from src.agents.coordinator import process_claim
    result = await process_claim(claim_file)
    if result:
        print("\nDecision:")
        print(json.dumps(result, indent=2))


async def demo_all() -> None:
    from src.agents.coordinator import process_all_claims
    results = await process_all_claims()
    print_summary(results)


def main() -> None:
    if len(sys.argv) > 1:
        claim_file = sys.argv[1]
        asyncio.run(demo_single(claim_file))
    else:
        print("Insurance Claims Agentic Solution — Processing all incoming claims...\n")
        asyncio.run(demo_all())


if __name__ == "__main__":
    main()
