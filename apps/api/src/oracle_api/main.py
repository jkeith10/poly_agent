import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oracle.database.repositories import AnalysisRepository, MarketRepository
from oracle.database.session import create_database, create_schema, session_factory
from oracle.observability import configure_logging
from oracle.providers import PolymarketClient
from oracle_api.config import get_settings
from oracle_api.schemas import (
    AnalysisInput,
    AnalysisView,
    HealthView,
    MarketView,
    RecommendationView,
)
from oracle_api.service import AnalysisService, MarketService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    provider = PolymarketClient(settings.polymarket_url)
    engine = create_database(settings.database_url)
    if settings.auto_create_schema:
        await create_schema(engine)
    app.state.markets = MarketService(provider)
    app.state.analysis = AnalysisService()
    app.state.sessions = session_factory(engine)
    yield
    await provider.close()
    await engine.dispose()


app = FastAPI(title="ORACLE API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "Idempotency-Key"])


def market_service(request: Request) -> MarketService:
    return request.app.state.markets


def analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis


async def database_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.sessions
    async with factory() as session:
        async with session.begin():
            yield session


async def require_admin_key(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.admin_api_keys and settings.environment == "development":
        return
    scheme, _, credential = (authorization or "").partition(" ")
    valid = scheme.lower() == "bearer" and any(
        secrets.compare_digest(credential, key) for key in settings.admin_api_keys
    )
    if not valid:
        raise HTTPException(status_code=401, detail="valid bearer credential required")


@app.get("/health", response_model=HealthView, tags=["operations"])
async def health() -> HealthView:
    return HealthView(status="ok", environment=settings.environment)


@app.get("/api/v1/markets", response_model=list[MarketView], tags=["markets"])
async def markets(
    session: Annotated[AsyncSession, Depends(database_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketView]:
    found = await MarketRepository(session).list_active(limit=limit, offset=offset)
    return [MarketView(id=item.id, question=item.question, description=item.description, yes_price=item.yes_price, no_price=item.no_price, liquidity=item.liquidity, volume=item.volume, closes_at=item.closes_at) for item in found]


@app.post("/api/v1/markets/scan", response_model=list[MarketView], tags=["markets"])
async def scan_markets(
    service: Annotated[MarketService, Depends(market_service)],
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> list[MarketView]:
    try:
        found = await service.scan(
            session,
            page_size=settings.market_page_size,
            maximum=settings.market_scan_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail="market provider unavailable") from exc
    return [MarketView(id=item.id, question=item.question, description=item.description, yes_price=item.yes_price, no_price=item.no_price, liquidity=item.liquidity, volume=item.volume, closes_at=item.closes_at) for item in found]


@app.post("/api/v1/markets/{market_id}/analysis", response_model=AnalysisView, tags=["analysis"])
async def analyze_market(
    market_id: UUID,
    body: AnalysisInput,
    analysis: Annotated[AnalysisService, Depends(analysis_service)],
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> AnalysisView:
    market = await MarketRepository(session).get(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="market has not been scanned")
    return await analysis.analyze(session, market, body)


@app.get(
    "/api/v1/recommendations",
    response_model=list[RecommendationView],
    tags=["analysis"],
)
async def recommendations(
    session: Annotated[AsyncSession, Depends(database_session)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    minimum_expected_value: Annotated[Decimal, Query(ge=-1, le=1)] = Decimal("0"),
) -> list[RecommendationView]:
    rows = await AnalysisRepository(session).list_recommendations(
        limit=limit, minimum_expected_value=minimum_expected_value
    )
    return [RecommendationView.model_validate(row) for row in rows]
