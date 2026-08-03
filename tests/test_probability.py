from decimal import Decimal

import pytest

from oracle.probability import BayesianEngine, EvidenceSignal


def test_supporting_evidence_increases_probability() -> None:
    result = BayesianEngine().update(Decimal("0.4"), [EvidenceSignal(Decimal("2"), Decimal("0.9"), "primary")])
    assert result.probability > Decimal("0.4")
    assert result.lower_bound < result.probability < result.upper_bound


def test_correlated_evidence_is_discounted() -> None:
    engine = BayesianEngine()
    correlated = engine.update(Decimal("0.5"), [EvidenceSignal(Decimal("2"), Decimal("1"), "same"), EvidenceSignal(Decimal("2"), Decimal("1"), "same")])
    independent = engine.update(Decimal("0.5"), [EvidenceSignal(Decimal("2"), Decimal("1"), "one"), EvidenceSignal(Decimal("2"), Decimal("1"), "two")])
    assert correlated.probability < independent.probability


def test_invalid_prior_is_rejected() -> None:
    with pytest.raises(ValueError):
        BayesianEngine().update(Decimal("1"), [])
