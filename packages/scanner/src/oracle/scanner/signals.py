from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MarketSignal:
    kind: str
    magnitude: Decimal
    interesting: bool


def detect_signals(prices: list[Decimal], liquidity: list[Decimal]) -> tuple[MarketSignal, ...]:
    if not prices:
        return ()
    movement = abs(prices[-1] - prices[0])
    volatility = max(prices) - min(prices)
    liquidity_change = liquidity[-1] - liquidity[0] if liquidity else Decimal(0)
    return (
        MarketSignal("price_movement", movement, movement >= Decimal("0.05")),
        MarketSignal("volatility", volatility, volatility >= Decimal("0.10")),
        MarketSignal("liquidity_change", liquidity_change, abs(liquidity_change) >= Decimal("1000")),
    )
