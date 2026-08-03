from decimal import Decimal

from oracle.common.models import RecommendationAction
from oracle.valuation import ValuationEngine


def test_buy_yes_for_positive_net_edge() -> None:
    result = ValuationEngine().evaluate(oracle_probability=Decimal("0.70"), yes_price=Decimal("0.50"), bankroll=Decimal("10000"))
    assert result.action is RecommendationAction.BUY_YES
    assert result.suggested_position > 0
    assert result.fractional_kelly <= Decimal("0.05")


def test_pass_when_execution_adjusted_edge_is_small() -> None:
    result = ValuationEngine().evaluate(oracle_probability=Decimal("0.52"), yes_price=Decimal("0.50"), bankroll=Decimal("10000"))
    assert result.action is RecommendationAction.PASS
    assert result.suggested_position == 0
