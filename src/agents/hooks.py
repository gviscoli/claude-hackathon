"""PreToolUse safety hooks for the insurance claims agent."""
import json
import os
from datetime import datetime
from pathlib import Path

AUDIT_LOG = Path(__file__).parent.parent.parent / "audit.log"
MAX_AUTO_AMOUNT = float(os.getenv("MAX_AUTO_APPROVE_AMOUNT", "50000"))
FRAUD_THRESHOLD = float(os.getenv("FRAUD_SCORE_THRESHOLD", "0.7"))


def _extract_json_from_command(command: str) -> dict | None:
    """Extract the JSON decision dict from a create_claim_record.py command.

    Handles both single-quoted and double-quoted (escaped) formats that the
    agent may produce depending on the shell context.
    """
    # Format A: create_claim_record.py '{"key": "value"}'
    try:
        start = command.index("'") + 1
        end = command.rindex("'")
        if start < end:
            return json.loads(command[start:end])
    except (ValueError, json.JSONDecodeError):
        pass

    # Format B: create_claim_record.py "{\"key\": \"value\"}"
    # Find the outermost { ... } and unescape backslash-quoted chars
    try:
        brace_start = command.index("{")
        depth = 0
        for i, ch in enumerate(command[brace_start:], brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    raw = command[brace_start : i + 1].replace('\\"', '"')
                    return json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        pass

    return None


def _write_audit(entry: dict) -> None:
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.now().isoformat(), **entry}) + "\n")


async def block_high_value_auto_approve(input_data: dict, tool_use_id, context) -> dict:
    """Block Bash calls that try to create a claim record above the auto-approve threshold."""
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}
    if input_data.get("tool_name") != "Bash":
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    if "create_claim_record.py" not in command:
        return {}

    try:
        decision = _extract_json_from_command(command)
        if decision is None:
            return {}
        amount = decision.get("recommended_payout", 0)
        fraud_score = decision.get("fraud_score", 0.0)

        if amount > MAX_AUTO_AMOUNT or fraud_score >= FRAUD_THRESHOLD:
            reason = (
                f"Payout €{amount:,.0f} exceeds auto-approve limit €{MAX_AUTO_AMOUNT:,.0f}"
                if amount > MAX_AUTO_AMOUNT
                else f"Fraud score {fraud_score:.2f} ≥ threshold {FRAUD_THRESHOLD}"
            )
            _write_audit({
                "event": "ESCALATE_HUMAN",
                "claim_id": decision.get("claim_id"),
                "amount": amount,
                "fraud_score": fraud_score,
                "reason": reason,
            })
            return {
                "systemMessage": (
                    f"HUMAN ESCALATION REQUIRED: {reason}. "
                    "Change decision to 'escalate-human' and set escalation_reason."
                ),
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                },
            }
    except (ValueError, KeyError, json.JSONDecodeError):
        pass

    return {}


async def audit_all_bash(input_data: dict, tool_use_id, context) -> dict:
    """Async audit log for every Bash call — non-blocking."""
    import asyncio

    async def _log():
        command = input_data.get("tool_input", {}).get("command", "")
        _write_audit({
            "event": "TOOL_USE",
            "tool": input_data.get("tool_name"),
            "command": command[:200],
            "session_id": input_data.get("session_id"),
        })

    asyncio.create_task(_log())
    return {"async_": True, "asyncTimeout": 5000}


async def block_pii_exfiltration(input_data: dict, tool_use_id, context) -> dict:
    """Prevent writing raw policy/customer data outside of processed_claims/."""
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}
    if input_data.get("tool_name") not in ("Write", "Bash"):
        return {}

    command = input_data.get("tool_input", {}).get("command", "")
    file_path = input_data.get("tool_input", {}).get("file_path", "")

    for path in (command, file_path):
        if "policies.json" in path and ("curl" in command or "upload" in command):
            _write_audit({"event": "BLOCKED_PII", "path": path})
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "PII exfiltration attempt blocked",
                }
            }
    return {}
