"""Insurance Claims Coordinator Agent — orchestrates triage and specialist routing."""
import asyncio
import json
import os
from pathlib import Path

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    HookMatcher,
    ResultMessage,
    AssistantMessage,
    query,
)

from .hooks import audit_all_bash, block_high_value_auto_approve, block_pii_exfiltration

BASE_DIR = Path(__file__).parent.parent.parent
SRC_DIR = BASE_DIR / "src"

COORDINATOR_PROMPT = """You are an insurance claims coordinator. Your job is to triage incoming claims and route them to specialist subagents for a final decision.

For each claim you receive, follow these steps IN ORDER:

1. READ the claim file provided to you
2. RUN: python src/tools/lookup_policy.py <policy_id>  → get policy details
3. RUN: python src/tools/get_claim_history.py <customer_id>  → get customer history
4. RUN: python src/tools/check_fraud.py <claim_file_path>  → get fraud score
5. RUN: python src/tools/assess_damage.py <policy_id> <claim_type> <amount>  → get payout estimate
6. Based on claim_type, use the AGENT tool to invoke the correct specialist:
   - auto   → use agent "auto-claims-specialist"
   - property → use agent "property-claims-specialist"
   - medical  → use agent "medical-claims-specialist"
   Pass ALL enriched data (policy, history, fraud score, damage assessment) in the agent prompt.
7. The specialist will return a JSON decision. RUN: python src/tools/create_claim_record.py '<decision_json>'
8. Print a final summary table showing: claim_id, decision, confidence, payout, fraud_score.

ESCALATION RULES (apply BEFORE calling create_claim_record):
- If recommended_payout > 50000 EUR → set decision to "escalate-human"
- If fraud_score >= 0.7 → set decision to "escalate-human"
- If confidence < 0.6 → set decision to "escalate-human"
- If policy is inactive → set decision to "deny"

MAX ITERATIONS: 20. Stop and report if you cannot complete within this limit.
"""

SPECIALIST_BASE = """You are an insurance claims specialist. You receive enriched claim data and must return a JSON decision.

You have access to these tools:
- python src/tools/assess_damage.py <policy_id> <claim_type> <amount>
- python src/tools/check_fraud.py <claim_file_path>

Analyze the data provided and return ONLY a valid JSON object with this exact structure:
{
  "claim_id": "<id>",
  "decision": "fast-track" | "investigate" | "deny" | "escalate-human",
  "confidence": <0.0-1.0>,
  "specialist": "<your-name>",
  "reasoning": "<clear explanation>",
  "fraud_score": <0.0-1.0>,
  "recommended_payout": <float or null>,
  "escalation_reason": "<reason or null>"
}

Decision criteria:
- fast-track: clear incident, good documentation, no fraud indicators, amount < 10000 EUR
- investigate: ambiguous circumstances, moderate fraud score (0.3-0.69), amount 10k-50k EUR
- deny: policy inactive, not covered, fraud score >= 0.7, or clearly fraudulent
- escalate-human: amount > 50000, confidence < 0.6, or borderline fraud
"""


def _bedrock_env() -> dict[str, str]:
    """Build env overrides for AWS Bedrock when CLAUDE_CODE_USE_BEDROCK is set."""
    if not os.getenv("CLAUDE_CODE_USE_BEDROCK"):
        return {}
    env: dict[str, str] = {"CLAUDE_CODE_USE_BEDROCK": "1"}
    for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "AWS_SESSION_TOKEN"):
        val = os.getenv(var)
        if val:
            env[var] = val
    return env


def build_options() -> ClaudeAgentOptions:
    bedrock_model = os.getenv("BEDROCK_MODEL_ID")
    return ClaudeAgentOptions(
        allowed_tools=["Bash", "Read", "Write", "Glob", "Agent"],
        max_turns=20,
        cwd=str(BASE_DIR),
        model=bedrock_model or None,
        env=_bedrock_env(),
        agents={
            "auto-claims-specialist": AgentDefinition(
                description="Specialist for automobile and vehicle insurance claims. Evaluates collision, theft, fire, and liability claims.",
                prompt=SPECIALIST_BASE + "\nYou specialize in AUTO claims: collision, theft, fire, third-party liability.",
                tools=["Bash", "Read"],
            ),
            "property-claims-specialist": AgentDefinition(
                description="Specialist for property and home insurance claims. Evaluates fire, flood, theft, storm, and earthquake damage.",
                prompt=SPECIALIST_BASE + "\nYou specialize in PROPERTY claims: fire, flood, storm, earthquake, theft from premises.",
                tools=["Bash", "Read"],
            ),
            "medical-claims-specialist": AgentDefinition(
                description="Specialist for health and medical insurance claims. Evaluates hospitalization, surgery, emergency, and specialist visits.",
                prompt=SPECIALIST_BASE + "\nYou specialize in MEDICAL claims: hospitalization, surgery, emergency care, specialist visits.",
                tools=["Bash", "Read"],
            ),
        },
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Bash", hooks=[block_high_value_auto_approve]),
                HookMatcher(matcher="Bash|Write", hooks=[block_pii_exfiltration]),
                HookMatcher(matcher="Bash", hooks=[audit_all_bash]),
            ]
        },
    )


async def process_claim(claim_file: str) -> dict | None:
    claim_path = Path(claim_file)
    if not claim_path.exists():
        raise FileNotFoundError(f"Claim file not found: {claim_file}")

    claim_data = json.loads(claim_path.read_text())
    claim_id = claim_data.get("claim_id", "UNKNOWN")
    print(f"\n{'='*60}")
    print(f"Processing claim: {claim_id}")
    print(f"Type: {claim_data.get('claim_type')} | Channel: {claim_data.get('channel')}")
    print(f"Amount: €{claim_data.get('estimated_amount', 0):,.0f}")
    print(f"{'='*60}\n")

    prompt = f"Process the insurance claim at: {claim_file}"
    options = build_options()

    result_text = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text, end="", flush=True)
        elif isinstance(message, ResultMessage):
            result_text = message.result
            print(f"\n\n[RESULT] {result_text}")

    processed_path = BASE_DIR / "src" / "data" / "processed_claims" / f"{claim_id}.json"
    if processed_path.exists():
        return json.loads(processed_path.read_text())
    return None


async def process_all_claims() -> list[dict]:
    claims_dir = SRC_DIR / "data" / "incoming_claims"
    claim_files = sorted(claims_dir.glob("*.json"))

    if not claim_files:
        print("No claims found in incoming_claims/")
        return []

    results = []
    for claim_file in claim_files:
        decision = await process_claim(str(claim_file))
        if decision:
            results.append(decision)

    return results
