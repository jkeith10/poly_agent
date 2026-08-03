from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class AlertDecision:
    send: bool
    reason: str


def should_alert(*, edge: Decimal, threshold: Decimal, analyzed_at: datetime, now: datetime, freshness: timedelta = timedelta(hours=1)) -> AlertDecision:
    if now - analyzed_at > freshness:
        return AlertDecision(False, "analysis is stale")
    if edge < threshold:
        return AlertDecision(False, "edge is below threshold")
    return AlertDecision(True, "fresh analysis exceeds edge threshold")
