import asyncio

from celery import Celery
from oracle.database.repositories import MarketRepository
from oracle.database.session import create_database, session_factory
from oracle.providers import PolymarketClient

from oracle_api.config import get_settings

settings = get_settings()
app = Celery("oracle", broker=settings.redis_url, backend=settings.redis_url)
app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], task_acks_late=True, worker_prefetch_multiplier=1, task_time_limit=120, task_soft_time_limit=110, timezone="UTC")
app.conf.beat_schedule = {
    "scan-active-markets": {"task": "oracle.scan_markets", "schedule": 60.0}
}


@app.task(name="oracle.health", autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


async def _scan_markets(limit: int) -> int:
    provider = PolymarketClient(settings.polymarket_url)
    engine = create_database(settings.database_url)
    factory = session_factory(engine)
    try:
        markets = await provider.all_active_markets(
            page_size=settings.market_page_size, maximum=limit
        )
        async with factory.begin() as session:
            repository = MarketRepository(session)
            for market in markets:
                await repository.store_snapshot(market)
        return len(markets)
    finally:
        await provider.close()
        await engine.dispose()


@app.task(name="oracle.scan_markets", autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def scan_markets(limit: int | None = None) -> dict[str, int]:
    """Retrieve and persist a bounded snapshot of active markets."""
    maximum = limit if limit is not None else settings.market_scan_limit
    return {"markets_scanned": asyncio.run(_scan_markets(maximum))}
