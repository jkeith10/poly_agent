from decimal import Decimal

from oracle.learning import evaluate_forecast
from oracle.portfolio import calculate_metrics


def test_forecast_scores_reward_accurate_probability() -> None:
    good = evaluate_forecast(0.9, True)
    bad = evaluate_forecast(0.1, True)
    assert good.brier < bad.brier
    assert good.log_loss < bad.log_loss


def test_portfolio_metrics_include_drawdown() -> None:
    result = calculate_metrics([Decimal("100"), Decimal("-200"), Decimal("300")], Decimal("1000"))
    assert result.roi == Decimal("0.2")
    assert result.maximum_drawdown > 0
    assert result.win_rate == Decimal(2) / Decimal(3)
