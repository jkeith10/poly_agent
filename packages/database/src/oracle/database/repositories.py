import json
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from oracle.common.models import Market
from oracle.database.models import (
    EvidenceRecord,
    HistoricalResultRecord,
    MarketPriceRecord,
    MarketRecord,
    PredictionRecord,
    PortfolioRecord,
    PositionRecord,
    RecommendationRecord,
    ResearchRecord,
    SourceRecord,
)
from oracle.learning import evaluate_forecast
from oracle.research.models import ResearchBrief


class MarketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def store_snapshot(self, market: Market) -> UUID:
        record = await self.session.scalar(
            select(MarketRecord).where(
                MarketRecord.provider == market.provider,
                MarketRecord.external_id == market.external_id,
            )
        )
        if record is None:
            record = MarketRecord(
                id=market.id,
                provider=market.provider,
                external_id=market.external_id,
                question=market.question,
                description=market.description,
                closes_at=market.closes_at,
                created_at=market.observed_at,
            )
            self.session.add(record)
            await self.session.flush()
        else:
            record.question = market.question
            record.description = market.description
            record.closes_at = market.closes_at
            record.active = True
        existing = await self.session.scalar(
            select(MarketPriceRecord.id).where(
                MarketPriceRecord.market_id == record.id,
                MarketPriceRecord.observed_at == market.observed_at,
            )
        )
        if existing is None:
            self.session.add(
                MarketPriceRecord(
                    market_id=record.id,
                    yes_price=market.yes_price,
                    no_price=market.no_price,
                    liquidity=market.liquidity,
                    volume=market.volume,
                    observed_at=market.observed_at,
                )
            )
        return record.id

    async def list_active(self, *, limit: int = 100, offset: int = 0) -> list[Market]:
        latest_time = (
            select(
                MarketPriceRecord.market_id,
                func.max(MarketPriceRecord.observed_at).label("observed_at"),
            )
            .group_by(MarketPriceRecord.market_id)
            .subquery()
        )
        latest_subquery = (
            select(MarketPriceRecord)
            .join(
                latest_time,
                (latest_time.c.market_id == MarketPriceRecord.market_id)
                & (latest_time.c.observed_at == MarketPriceRecord.observed_at),
            )
            .subquery()
        )
        latest = aliased(MarketPriceRecord, latest_subquery)
        rows = (
            await self.session.execute(
                select(MarketRecord, latest)
                .join(latest, latest.market_id == MarketRecord.id)
                .where(MarketRecord.active.is_(True))
                .order_by(desc(latest.liquidity))
                .limit(limit)
                .offset(offset)
            )
        ).all()
        return [
            Market(
                id=record.id,
                provider=record.provider,
                external_id=record.external_id,
                question=record.question,
                description=record.description,
                yes_price=price.yes_price,
                no_price=price.no_price,
                liquidity=price.liquidity,
                volume=price.volume,
                closes_at=record.closes_at,
                observed_at=price.observed_at,
            )
            for record, price in rows
        ]

    async def get(self, market_id: UUID) -> Market | None:
        price = await self.session.scalar(
            select(MarketPriceRecord)
            .where(MarketPriceRecord.market_id == market_id)
            .order_by(desc(MarketPriceRecord.observed_at))
            .limit(1)
        )
        record = await self.session.get(MarketRecord, market_id)
        if record is None or price is None:
            return None
        return Market(
            id=record.id,
            provider=record.provider,
            external_id=record.external_id,
            question=record.question,
            description=record.description,
            yes_price=price.yes_price,
            no_price=price.no_price,
            liquidity=price.liquidity,
            volume=price.volume,
            closes_at=record.closes_at,
            observed_at=price.observed_at,
        )


class AnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        *,
        market_id: UUID,
        prior: Decimal,
        posterior: Decimal,
        lower_bound: Decimal,
        upper_bound: Decimal,
        action: str,
        market_probability: Decimal,
        edge: Decimal,
        expected_value: Decimal,
        fractional_kelly: Decimal,
        suggested_position: Decimal,
        reasoning: str,
        citations: Sequence[str],
    ) -> UUID:
        now = datetime.now(UTC)
        prediction = PredictionRecord(
            market_id=market_id,
            prior=prior,
            posterior=posterior,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            explanation=reasoning,
            model_version="bayesian-v1",
            created_at=now,
        )
        self.session.add(prediction)
        await self.session.flush()
        self.session.add(
            RecommendationRecord(
                prediction_id=prediction.id,
                action=action,
                market_probability=market_probability,
                edge=edge,
                expected_value=expected_value,
                fractional_kelly=fractional_kelly,
                suggested_position=suggested_position,
                reasoning=reasoning,
                citations_json=json.dumps(list(citations)),
                created_at=now,
            )
        )
        return prediction.id

    async def list_recommendations(
        self, *, limit: int = 100, minimum_expected_value: Decimal = Decimal("0")
    ) -> list[dict[str, object]]:
        rows = (
            await self.session.execute(
                select(PredictionRecord, RecommendationRecord, MarketRecord.question)
                .join(
                    RecommendationRecord,
                    RecommendationRecord.prediction_id == PredictionRecord.id,
                )
                .join(MarketRecord, MarketRecord.id == PredictionRecord.market_id)
                .where(RecommendationRecord.expected_value >= minimum_expected_value)
                .order_by(desc(RecommendationRecord.created_at))
                .limit(limit)
            )
        ).all()
        return [
            {
                "prediction_id": prediction.id,
                "market_id": prediction.market_id,
                "question": question,
                "action": recommendation.action,
                "market_probability": recommendation.market_probability,
                "oracle_probability": prediction.posterior,
                "lower_bound": prediction.lower_bound,
                "upper_bound": prediction.upper_bound,
                "edge": recommendation.edge,
                "expected_value": recommendation.expected_value,
                "fractional_kelly": recommendation.fractional_kelly,
                "suggested_position": recommendation.suggested_position,
                "reasoning": recommendation.reasoning,
                "citations": json.loads(recommendation.citations_json),
                "created_at": recommendation.created_at,
            }
            for prediction, recommendation, question in rows
        ]


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, name: str, bankroll: Decimal) -> PortfolioRecord:
        record = PortfolioRecord(
            name=name, bankroll=bankroll, created_at=datetime.now(UTC)
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list(self) -> list[PortfolioRecord]:
        return list(
            (
                await self.session.scalars(
                    select(PortfolioRecord).order_by(PortfolioRecord.created_at)
                )
            ).all()
        )

    async def add_position(
        self,
        *,
        portfolio_id: UUID,
        market_id: UUID,
        side: str,
        quantity: Decimal,
        average_price: Decimal,
    ) -> PositionRecord:
        if await self.session.get(PortfolioRecord, portfolio_id) is None:
            raise LookupError("portfolio not found")
        if await self.session.get(MarketRecord, market_id) is None:
            raise LookupError("market not found")
        record = PositionRecord(
            portfolio_id=portfolio_id,
            market_id=market_id,
            side=side,
            quantity=quantity,
            average_price=average_price,
            status="OPEN",
            opened_at=datetime.now(UTC),
            resolved_at=None,
            realized_pnl=None,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def positions(self, portfolio_id: UUID) -> list[PositionRecord]:
        return list(
            (
                await self.session.scalars(
                    select(PositionRecord)
                    .where(PositionRecord.portfolio_id == portfolio_id)
                    .order_by(PositionRecord.opened_at)
                )
            ).all()
        )

    async def resolve_position(
        self, position_id: UUID, *, outcome_yes: bool
    ) -> PositionRecord:
        record = await self.session.get(PositionRecord, position_id)
        if record is None:
            raise LookupError("position not found")
        if record.status != "OPEN":
            raise ValueError("position is already resolved")
        won = (record.side == "YES") == outcome_yes
        payout = record.quantity if won else Decimal(0)
        cost = record.quantity * record.average_price
        record.realized_pnl = payout - cost
        record.status = "RESOLVED"
        record.resolved_at = datetime.now(UTC)
        return record


class LearningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate_resolution(
        self, market_id: UUID, *, outcome_yes: bool
    ) -> tuple[int, Decimal, Decimal]:
        predictions = list(
            (
                await self.session.scalars(
                    select(PredictionRecord).where(PredictionRecord.market_id == market_id)
                )
            ).all()
        )
        if not predictions:
            raise LookupError("no predictions found for market")
        scores = [evaluate_forecast(float(item.posterior), outcome_yes) for item in predictions]
        mean_brier = Decimal(str(sum(item.brier for item in scores) / len(scores)))
        mean_log_loss = Decimal(str(sum(item.log_loss for item in scores) / len(scores)))
        existing = await self.session.scalar(
            select(HistoricalResultRecord).where(
                HistoricalResultRecord.market_id == market_id
            )
        )
        if existing is None:
            existing = HistoricalResultRecord(
                market_id=market_id,
                outcome=outcome_yes,
                brier_score=mean_brier,
                log_loss=mean_log_loss,
                resolved_at=datetime.now(UTC),
            )
            self.session.add(existing)
        else:
            existing.outcome = outcome_yes
            existing.brier_score = mean_brier
            existing.log_loss = mean_log_loss
            existing.resolved_at = datetime.now(UTC)
        return len(scores), mean_brier, mean_log_loss


class ResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, brief: ResearchBrief) -> UUID:
        run = ResearchRecord(
            market_id=brief.market_id,
            status="COMPLETED",
            started_at=brief.researched_at,
            completed_at=brief.researched_at,
        )
        self.session.add(run)
        await self.session.flush()
        for finding in brief.yes_evidence + brief.no_evidence:
            url = str(finding.source_url)
            source = await self.session.scalar(
                select(SourceRecord).where(SourceRecord.url == url)
            )
            if source is None:
                source = SourceRecord(
                    url=url,
                    publisher=finding.source_url.host or "unknown",
                    historical_accuracy=None,
                )
                self.session.add(source)
                await self.session.flush()
            quality = Decimal(str(finding.source_quality))
            self.session.add(
                EvidenceRecord(
                    research_id=run.id,
                    source_id=source.id,
                    claim=finding.claim,
                    citation=finding.citation,
                    supports_yes=finding.supports_yes,
                    reliability=quality,
                    freshness=Decimal("0.5") if finding.published_at is None else Decimal("1"),
                    importance=quality,
                    independence_group=url,
                    observed_at=brief.researched_at,
                )
            )
        return run.id
