from datetime import UTC, datetime, timedelta
from decimal import Decimal

from oracle.alerts import should_alert
from oracle.evidence import score_evidence
from oracle.scanner import detect_signals


def test_scanner_flags_large_move() -> None:
    signals = detect_signals([Decimal("0.4"), Decimal("0.48")], [Decimal("1000"), Decimal("2500")])
    assert signals[0].interesting
    assert signals[2].interesting


def test_evidence_score_is_weighted() -> None:
    score = score_evidence(reliability=Decimal("1"), freshness=Decimal("1"), importance=Decimal("1"), historical_accuracy=Decimal("1"))
    assert score.composite == Decimal("1.00")


def test_alert_rejects_stale_analysis() -> None:
    now = datetime.now(UTC)
    decision = should_alert(edge=Decimal("0.2"), threshold=Decimal("0.05"), analyzed_at=now - timedelta(hours=2), now=now)
    assert not decision.send
