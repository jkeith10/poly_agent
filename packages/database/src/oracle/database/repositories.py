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
    MarketPriceRecord,
    MarketRecord,
    PredictionRecord,
    RecommendationRecord,
)


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
