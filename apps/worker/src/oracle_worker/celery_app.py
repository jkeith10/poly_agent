import asyncio

from celery import Celery
from sqlalchemy import select

from oracle.database.models import MarketPriceRecord, MarketRecord
from oracle.database.session import create_database, session_factory
from oracle.providers import PolymarketClient

from oracle_api.config import get_settings

settings = get_settings()
app = Celery("oracle", broker=settings.redis_url, backend=settings.redis_url)
app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=120, task_soft_time_limit=110, timezone="UTC")


@app.task(name="oracle.health", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


async def _scan_markets(limit: int) -> int:
    provider = PolymarketClient(settings.polymarket_url)
    engine = create_database(settings.database_url)
    factory = session_factory(engine)
    try:
        markets = await provider.active_markets(limit=limit)
        async with factory.begin() as session:
            for market in markets:
                record = await session.scalar(
                    select(MarketRecord).where(
                        MarketRecord.provider == market.provider,
                        MarketRecord.external_id == market.external_id,
                    )
                )
                if record is None:
                    record = MarketRecord(
                        provider=market.provider,
                        external_id=market.external_id,
                        question=market.question,
                        description=market.description,
                        closes_at=market.closes_at,
                        created_at=market.observed_at,
                    )
                    session.add(record)
                    await session.flush()
                session.add(
                    MarketPriceRecord(
                        market_id=record.id,
                        yes_price=market.yes_price,
                        no_price=market.no_price,
                        liquidity=market.liquidity,
                        volume=market.volume,
                        observed_at=market.observed_at,
                    )
                )
        return len(markets)
    finally:
        await provider.close()
        await engine.dispose()


@app.task(name="oracle.scan_markets", autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def scan_markets(limit: int = 500) -> dict[str, int]:
    """Persist a provider snapshot; retries are safe because snapshots are append-only."""
    return {"markets_scanned": asyncio.run(_scan_markets(limit))}
