import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from oracle.ai import StructuredHttpGenerator
from oracle.database.models import PortfolioRecord
from oracle.database.repositories import (
    AnalysisRepository,
    LearningRepository,
    MarketRepository,
    PortfolioRepository,
    ResearchRepository,
)
from oracle.database.session import create_database, create_schema, session_factory
from oracle.observability import configure_logging
from oracle.portfolio import calculate_metrics
from oracle.providers import PolymarketClient
from oracle.research import (
    ResearchAgent,
    ResearchBrief,
    SafeSourceRetriever,
    SearchApiProvider,
    StructuredFindingExtractor,
)
from oracle_api.config import get_settings
from oracle_api.schemas import (
    AnalysisInput,
    AnalysisView,
    ForecastEvaluationView,
    HealthView,
    MarketResolutionInput,
    MarketView,
    PortfolioCreate,
    PortfolioPerformanceView,
    PortfolioView,
    PositionCreate,
    PositionView,
    RecommendationView,
    ResolvePosition,
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
    app.state.research = None
    app.state.research_resources = []
    if (
        settings.ai_api_key is not None
        and settings.ai_model is not None
        and settings.search_api_key is not None
    ):
        generator = StructuredHttpGenerator(
            api_key=settings.ai_api_key.get_secret_value(),
            model=settings.ai_model,
            base_url=settings.ai_base_url,
        )
        search = SearchApiProvider(
            endpoint=settings.search_api_url,
            api_key=settings.search_api_key.get_secret_value(),
        )
        retriever = SafeSourceRetriever()
        app.state.research = ResearchAgent(
            search=search,
            retriever=retriever,
            extractor=StructuredFindingExtractor(generator),
        )
        app.state.research_resources = [generator, search, retriever]
    yield
    await provider.close()
    for resource in app.state.research_resources:
        await resource.close()
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


@app.post("/api/v1/portfolios", response_model=PortfolioView, tags=["portfolio"])
async def create_portfolio(
    body: PortfolioCreate,
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> PortfolioView:
    record = await PortfolioRepository(session).create(
        name=body.name, bankroll=body.bankroll
    )
    return PortfolioView.model_validate(record, from_attributes=True)


@app.get("/api/v1/portfolios", response_model=list[PortfolioView], tags=["portfolio"])
async def portfolios(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> list[PortfolioView]:
    records = await PortfolioRepository(session).list()
    return [PortfolioView.model_validate(item, from_attributes=True) for item in records]


@app.post(
    "/api/v1/portfolios/{portfolio_id}/positions",
    response_model=PositionView,
    tags=["portfolio"],
)
async def create_position(
    portfolio_id: UUID,
    body: PositionCreate,
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> PositionView:
    try:
        record = await PortfolioRepository(session).add_position(
            portfolio_id=portfolio_id,
            market_id=body.market_id,
            side=body.side,
            quantity=body.quantity,
            average_price=body.average_price,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PositionView.model_validate(record, from_attributes=True)


@app.get(
    "/api/v1/portfolios/{portfolio_id}/positions",
    response_model=list[PositionView],
    tags=["portfolio"],
)
async def positions(
    portfolio_id: UUID,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> list[PositionView]:
    records = await PortfolioRepository(session).positions(portfolio_id)
    return [PositionView.model_validate(item, from_attributes=True) for item in records]


@app.post(
    "/api/v1/positions/{position_id}/resolve",
    response_model=PositionView,
    tags=["portfolio"],
)
async def resolve_position(
    position_id: UUID,
    body: ResolvePosition,
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> PositionView:
    try:
        record = await PortfolioRepository(session).resolve_position(
            position_id, outcome_yes=body.outcome_yes
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return PositionView.model_validate(record, from_attributes=True)


@app.get(
    "/api/v1/portfolios/{portfolio_id}/performance",
    response_model=PortfolioPerformanceView,
    tags=["portfolio"],
)
async def portfolio_performance(
    portfolio_id: UUID,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> PortfolioPerformanceView:
    repository = PortfolioRepository(session)
    portfolio = await session.get(PortfolioRecord, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail="portfolio not found")
    records = await repository.positions(portfolio_id)
    returns = [item.realized_pnl for item in records if item.realized_pnl is not None]
    result = calculate_metrics(returns, portfolio.bankroll)
    return PortfolioPerformanceView(
        roi=result.roi,
        win_rate=result.win_rate,
        maximum_drawdown=result.maximum_drawdown,
        sharpe_ratio=result.sharpe_ratio,
    )


@app.post(
    "/api/v1/markets/{market_id}/resolve",
    response_model=ForecastEvaluationView,
    tags=["learning"],
)
async def resolve_market(
    market_id: UUID,
    body: MarketResolutionInput,
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> ForecastEvaluationView:
    try:
        count, brier, log_loss = await LearningRepository(session).evaluate_resolution(
            market_id, outcome_yes=body.outcome_yes
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ForecastEvaluationView(
        market_id=market_id,
        predictions_evaluated=count,
        mean_brier_score=brier,
        mean_log_loss=log_loss,
    )


@app.post(
    "/api/v1/markets/{market_id}/research",
    response_model=ResearchBrief,
    tags=["research"],
)
async def research_market(
    market_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
    _: Annotated[None, Depends(require_admin_key)],
) -> ResearchBrief:
    agent: ResearchAgent | None = request.app.state.research
    if agent is None:
        raise HTTPException(
            status_code=503,
            detail="research requires configured AI and search provider credentials",
        )
    market = await MarketRepository(session).get(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="market has not been scanned")
    brief = await agent.research(market.id, market.question)
    await ResearchRepository(session).save(brief)
    return brief
