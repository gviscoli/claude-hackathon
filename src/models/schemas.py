from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class IncomingClaim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    channel: Literal["email", "web_portal", "mobile_app", "fax"]
    claim_type: Literal["auto", "property", "medical", "other"]
    description: str
    estimated_amount: float
    incident_date: str
    attachments: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class PolicyInfo(BaseModel):
    policy_id: str
    customer_id: str
    customer_name: str
    policy_type: Literal["auto", "property", "medical", "comprehensive"]
    coverage_limit: float
    deductible: float
    active: bool
    start_date: str
    end_date: str
    covered_items: list[str]


class ClaimHistoryEntry(BaseModel):
    claim_id: str
    date: str
    type: str
    amount: float
    decision: Literal["fast-track", "paid", "investigate", "denied"]
    fraud_flag: bool = False


class FraudCheckResult(BaseModel):
    fraud_score: float = Field(ge=0.0, le=1.0)
    indicators: list[str]
    requires_investigation: bool


class ClaimDecision(BaseModel):
    claim_id: str
    decision: Literal["fast-track", "investigate", "deny", "escalate-human"]
    confidence: float = Field(ge=0.0, le=1.0)
    specialist: str
    reasoning: str
    fraud_score: float
    recommended_payout: Optional[float] = None
    escalation_reason: Optional[str] = None
    processed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
