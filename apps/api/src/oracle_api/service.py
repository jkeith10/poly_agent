from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from oracle.common.models import Market
from oracle.database.repositories import AnalysisRepository, MarketRepository
from oracle.probability import BayesianEngine, EvidenceSignal
from oracle.providers import PolymarketClient
from oracle.valuation import ValuationEngine
from oracle_api.schemas import AnalysisInput, AnalysisView


class MarketService:
    def __init__(self, provider: PolymarketClient) -> None:
        self.provider = provider

    async def scan(
        self, session: AsyncSession, *, page_size: int, maximum: int
    ) -> list[Market]:
        markets = await self.provider.all_active_markets(
            page_size=page_size, maximum=maximum
        )
        repository = MarketRepository(session)
        for market in markets:
            await repository.store_snapshot(market)
        return markets


class AnalysisService:
    def __init__(self) -> None:
        self.probability = BayesianEngine()
        self.valuation = ValuationEngine()

    async def analyze(
        self, session: AsyncSession, market: Market, request: AnalysisInput
    ) -> AnalysisView:
        signals = [
            EvidenceSignal(
                item.likelihood_ratio, item.reliability, item.independence_group
            )
            for item in request.evidence
        ]
        posterior = self.probability.update(request.prior, signals)
        valuation = self.valuation.evaluate(
            oracle_probability=posterior.probability,
            yes_price=market.yes_price,
            bankroll=request.bankroll,
        )
        reasoning = (
            f"Posterior updated from {request.prior:.3f} to "
            f"{posterior.probability:.3f} using {len(signals)} reliability-weighted "
            "evidence signals; recommendation includes estimated execution costs."
        )
        citations = [item.citation for item in request.evidence]
        result = AnalysisView(
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
            citations=citations,
        )
        await AnalysisRepository(session).save(
            market_id=market.id,
            prior=request.prior,
            posterior=result.oracle_probability,
            lower_bound=result.lower_bound,
            upper_bound=result.upper_bound,
            action=result.action.value,
            market_probability=result.market_probability,
            edge=result.edge,
            expected_value=result.expected_value,
            fractional_kelly=result.fractional_kelly,
            suggested_position=result.suggested_position,
            reasoning=result.reasoning,
            citations=result.citations,
        )
        return result
