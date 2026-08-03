from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EvidenceScore:
    reliability: Decimal
    freshness: Decimal
    importance: Decimal
    historical_accuracy: Decimal
    composite: Decimal


def score_evidence(*, reliability: Decimal, freshness: Decimal, importance: Decimal, historical_accuracy: Decimal) -> EvidenceScore:
    values = (reliability, freshness, importance, historical_accuracy)
    if any(value < 0 or value > 1 for value in values):
        raise ValueError("evidence factors must be probabilities")
    composite = reliability * Decimal("0.35") + freshness * Decimal("0.20") + importance * Decimal("0.30") + historical_accuracy * Decimal("0.15")
    return EvidenceScore(reliability, freshness, importance, historical_accuracy, composite)
