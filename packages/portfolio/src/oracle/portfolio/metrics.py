import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    roi: Decimal
    win_rate: Decimal
    maximum_drawdown: Decimal
    sharpe_ratio: Decimal


def calculate_metrics(returns: list[Decimal], initial_bankroll: Decimal) -> PerformanceMetrics:
    if initial_bankroll <= 0:
        raise ValueError("initial bankroll must be positive")
    if not returns:
        return PerformanceMetrics(Decimal(0), Decimal(0), Decimal(0), Decimal(0))
    equity = initial_bankroll
    peak = equity
    drawdown = Decimal(0)
    for value in returns:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, (peak - equity) / peak)
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    sharpe = Decimal(0) if variance == 0 else Decimal(str(float(mean) / math.sqrt(float(variance))))
    return PerformanceMetrics((equity - initial_bankroll) / initial_bankroll, Decimal(sum(value > 0 for value in returns)) / len(returns), drawdown, sharpe)
