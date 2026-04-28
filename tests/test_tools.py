"""Unit tests for claim processing tools."""
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
SRC = BASE / "src"


def run_tool(args: list[str]) -> dict:
    result = subprocess.run(
        [sys.executable] + args,
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )
    assert result.returncode == 0, f"Tool failed: {result.stderr}"
    return json.loads(result.stdout)


class TestLookupPolicy:
    def test_existing_policy(self):
        result = run_tool(["src/tools/lookup_policy.py", "POL001"])
        assert result["found"] is True
        assert result["policy"]["customer_name"] == "Marco Rossi"

    def test_missing_policy(self):
        result = run_tool(["src/tools/lookup_policy.py", "POL999"])
        assert result["found"] is False
        assert "error" in result

    def test_inactive_policy(self):
        result = run_tool(["src/tools/lookup_policy.py", "POL005"])
        assert result["found"] is True
        assert result["policy"]["active"] is False


class TestClaimHistory:
    def test_customer_with_history(self):
        result = run_tool(["src/tools/get_claim_history.py", "CUST001"])
        assert result["total_claims"] == 1
        assert result["fraud_flags"] == 0

    def test_customer_no_history(self):
        result = run_tool(["src/tools/get_claim_history.py", "CUST003"])
        assert result["total_claims"] == 0

    def test_customer_with_fraud_flag(self):
        result = run_tool(["src/tools/get_claim_history.py", "CUST004"])
        assert result["fraud_flags"] >= 1


class TestAssessDamage:
    def test_covered_claim(self):
        result = run_tool(["src/tools/assess_damage.py", "POL001", "auto", "3500"])
        assert result["covered"] is True
        assert result["recommended_payout"] == 2500.0  # 3500 - 1000 deductible

    def test_inactive_policy(self):
        result = run_tool(["src/tools/assess_damage.py", "POL005", "property", "10000"])
        assert result["covered"] is False
        assert result["recommended_payout"] == 0.0

    def test_payout_capped_at_limit(self):
        result = run_tool(["src/tools/assess_damage.py", "POL001", "auto", "90000"])
        assert result["recommended_payout"] <= 80000
        assert result["within_limits"] is False


class TestFraudCheck:
    def test_clean_claim(self):
        claim_file = str(SRC / "data/incoming_claims/claim_001_auto.json")
        result = run_tool(["src/tools/check_fraud.py", claim_file])
        assert result["fraud_score"] < 0.5
        assert result["requires_investigation"] is False

    def test_suspicious_claim(self):
        claim_file = str(SRC / "data/incoming_claims/claim_004_suspicious.json")
        result = run_tool(["src/tools/check_fraud.py", claim_file])
        assert result["fraud_score"] >= 0.5
        assert len(result["indicators"]) > 0
