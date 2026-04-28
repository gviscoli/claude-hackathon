"""Eval harness — Waypoint 7: The Scorecard.

Measures: accuracy, per-category precision, escalation quality, adversarial pass rate.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

BASE = Path(__file__).parent.parent

DecisionType = Literal["fast-track", "investigate", "deny", "escalate-human"]


@dataclass
class LabeledCase:
    claim_id: str
    claim_file: str
    expected_decision: DecisionType
    expected_escalation: bool
    category: str
    is_adversarial: bool = False
    notes: str = ""


LABELED_DATASET: list[LabeledCase] = [
    LabeledCase(
        claim_id="CLM-2026-001",
        claim_file="src/data/incoming_claims/claim_001_auto.json",
        expected_decision="fast-track",
        expected_escalation=False,
        category="auto",
        notes="Clean claim, police report, single past claim, well within limits",
    ),
    LabeledCase(
        claim_id="CLM-2026-002",
        claim_file="src/data/incoming_claims/claim_002_property.json",
        expected_decision="investigate",
        expected_escalation=False,
        category="property",
        notes="Second property claim in 2 years, moderate amount, good docs",
    ),
    LabeledCase(
        claim_id="CLM-2026-003",
        claim_file="src/data/incoming_claims/claim_003_medical.json",
        expected_decision="fast-track",
        expected_escalation=False,
        category="medical",
        notes="First claim, well-documented emergency surgery, within limits",
    ),
    LabeledCase(
        claim_id="CLM-2026-004",
        claim_file="src/data/incoming_claims/claim_004_suspicious.json",
        expected_decision="escalate-human",
        expected_escalation=True,
        category="auto",
        is_adversarial=True,
        notes="Multiple fraud indicators: no docs, 3rd claim, suspicious language",
    ),
]


@dataclass
class EvalResult:
    case: LabeledCase
    actual_decision: str | None
    actual_escalation: bool
    decision_correct: bool
    escalation_correct: bool
    confidence: float
    fraud_score: float
    false_confidence: bool  # high confidence + wrong decision


@dataclass
class EvalMetrics:
    total: int = 0
    decision_correct: int = 0
    escalation_correct: int = 0
    adversarial_passed: int = 0
    adversarial_total: int = 0
    false_confidence_count: int = 0
    per_category: dict = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        return self.decision_correct / self.total if self.total else 0.0

    @property
    def escalation_quality(self) -> float:
        return self.escalation_correct / self.total if self.total else 0.0

    @property
    def adversarial_pass_rate(self) -> float:
        return self.adversarial_passed / self.adversarial_total if self.adversarial_total else 0.0

    @property
    def false_confidence_rate(self) -> float:
        return self.false_confidence_count / self.total if self.total else 0.0

    def category_precision(self, category: str) -> float:
        cat = self.per_category.get(category, {})
        total = cat.get("total", 0)
        correct = cat.get("correct", 0)
        return correct / total if total else 0.0


def load_processed_decision(claim_id: str) -> dict | None:
    path = BASE / "src" / "data" / "processed_claims" / f"{claim_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def evaluate() -> EvalMetrics:
    metrics = EvalMetrics()

    for case in LABELED_DATASET:
        metrics.total += 1
        decision_data = load_processed_decision(case.claim_id)

        if decision_data is None:
            print(f"  [MISSING] {case.claim_id} — not yet processed")
            continue

        actual = decision_data.get("decision")
        confidence = decision_data.get("confidence", 0.0)
        fraud_score = decision_data.get("fraud_score", 0.0)
        actual_escalation = actual == "escalate-human"

        decision_correct = actual == case.expected_decision
        escalation_correct = actual_escalation == case.expected_escalation
        false_conf = confidence > 0.85 and not decision_correct

        result = EvalResult(
            case=case,
            actual_decision=actual,
            actual_escalation=actual_escalation,
            decision_correct=decision_correct,
            escalation_correct=escalation_correct,
            confidence=confidence,
            fraud_score=fraud_score,
            false_confidence=false_conf,
        )

        if decision_correct:
            metrics.decision_correct += 1
        if escalation_correct:
            metrics.escalation_correct += 1
        if false_conf:
            metrics.false_confidence_count += 1
        if case.is_adversarial:
            metrics.adversarial_total += 1
            if decision_correct:
                metrics.adversarial_passed += 1

        cat = metrics.per_category.setdefault(case.category, {"total": 0, "correct": 0})
        cat["total"] += 1
        if decision_correct:
            cat["correct"] += 1

        icon = "✓" if decision_correct else "✗"
        print(f"  {icon} {case.claim_id}: expected={case.expected_decision}, actual={actual}, conf={confidence:.2f}")

    return metrics


def print_report(metrics: EvalMetrics) -> None:
    print("\n" + "=" * 60)
    print("EVAL SCORECARD")
    print("=" * 60)
    print(f"Overall Accuracy:        {metrics.accuracy:.1%}  ({metrics.decision_correct}/{metrics.total})")
    print(f"Escalation Quality:      {metrics.escalation_quality:.1%}")
    print(f"Adversarial Pass Rate:   {metrics.adversarial_pass_rate:.1%}  ({metrics.adversarial_passed}/{metrics.adversarial_total})")
    print(f"False Confidence Rate:   {metrics.false_confidence_rate:.1%}")
    print()
    print("Per-Category Precision:")
    for cat, data in metrics.per_category.items():
        prec = data["correct"] / data["total"] if data["total"] else 0
        print(f"  {cat:<15} {prec:.1%}  ({data['correct']}/{data['total']})")
    print("=" * 60)


if __name__ == "__main__":
    print("Running eval harness...\n")
    metrics = evaluate()
    print_report(metrics)
