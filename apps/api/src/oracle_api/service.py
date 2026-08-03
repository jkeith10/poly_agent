from decimal import Decimal
from uuid import UUID

from oracle.common.models import Market
from oracle.probability import BayesianEngine, EvidenceSignal
from oracle.providers import PolymarketClient
from oracle.valuation import ValuationEngine
from oracle_api.schemas import AnalysisInput, AnalysisView


class MarketService:
    def __init__(self, provider: PolymarketClient) -> None:
        self.provider = provider
        self._markets: dict[UUID, Market] = {}

    async def scan(self, limit: int) -> list[Market]:
        markets = await self.provider.active_markets(limit=limit)
        self._markets.update({market.id: market for market in markets})
        return markets

    def get(self, market_id: UUID) -> Market | None:
        return self._markets.get(market_id)


class AnalysisService:
    def __init__(self) -> None:
        self.probability = BayesianEngine()
        self.valuation = ValuationEngine()

    def analyze(self, market: Market, request: AnalysisInput) -> AnalysisView:
        signals = [EvidenceSignal(item.likelihood_ratio, item.reliability, item.independence_group) for item in request.evidence]
        posterior = self.probability.update(request.prior, signals)
        valuation = self.valuation.evaluate(oracle_probability=posterior.probability, yes_price=market.yes_price, bankroll=request.bankroll)
        reasoning = f"Posterior updated from {request.prior:.3f} to {posterior.probability:.3f} using {len(signals)} reliability-weighted evidence signals; recommendation includes estimated execution costs."
        return AnalysisView(
            market_id=market.id,
            market_probability=market.yes_price,
            oracle_probability=posterior.probability,
            lower_bound=posterior.lower_bound,
            upper_bound=posterior.upper_bound,
            action=valuation.action,
            edge=valuation.edge,
            expected_value=valuation.expected_value,
            fractional_kelly=valuation.fractional_kelly,
            suggested_position=valuation.suggested_position,
            reasoning=reasoning,
            citations=[item.citation for item in request.evidence],
        )
