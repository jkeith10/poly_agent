from dataclasses import dataclass
from decimal import Decimal

from oracle.common.models import RecommendationAction


@dataclass(frozen=True, slots=True)
class ValuationPolicy:
    minimum_edge: Decimal = Decimal("0.05")
    kelly_fraction: Decimal = Decimal("0.25")
    maximum_position_fraction: Decimal = Decimal("0.05")
    estimated_cost_rate: Decimal = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class ValuationResult:
    action: RecommendationAction
    edge: Decimal
    expected_value: Decimal
    fractional_kelly: Decimal
    suggested_position: Decimal


class ValuationEngine:
    def __init__(self, policy: ValuationPolicy | None = None) -> None:
        self.policy = policy or ValuationPolicy()

    def evaluate(
        self, *, oracle_probability: Decimal, yes_price: Decimal, bankroll: Decimal
    ) -> ValuationResult:
        if not 0 < yes_price < 1 or not 0 <= oracle_probability <= 1 or bankroll < 0:
            raise ValueError("invalid valuation inputs")
        effective_price = min(Decimal("0.999"), yes_price + self.policy.estimated_cost_rate)
        yes_ev = oracle_probability - effective_price
        no_price = Decimal(1) - yes_price
        effective_no_price = min(Decimal("0.999"), no_price + self.policy.estimated_cost_rate)
        no_ev = (Decimal(1) - oracle_probability) - effective_no_price
        if max(yes_ev, no_ev) < self.policy.minimum_edge:
            return ValuationResult(RecommendationAction.PASS, oracle_probability - yes_price, max(yes_ev, no_ev), Decimal(0), Decimal(0))
        action = RecommendationAction.BUY_YES if yes_ev >= no_ev else RecommendationAction.BUY_NO
        probability = oracle_probability if action == RecommendationAction.BUY_YES else 1 - oracle_probability
        price = effective_price if action == RecommendationAction.BUY_YES else effective_no_price
        raw_kelly = max(Decimal(0), (probability - price) / (Decimal(1) - price))
        fractional = min(self.policy.maximum_position_fraction, raw_kelly * self.policy.kelly_fraction)
        return ValuationResult(action, oracle_probability - yes_price, max(yes_ev, no_ev), fractional, bankroll * fractional)
