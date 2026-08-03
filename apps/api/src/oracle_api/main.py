from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from oracle.observability import configure_logging
from oracle.providers import PolymarketClient
from oracle_api.config import get_settings
from oracle_api.schemas import AnalysisInput, AnalysisView, HealthView, MarketView
from oracle_api.service import AnalysisService, MarketService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging()
    provider = PolymarketClient(settings.polymarket_url)
    app.state.markets = MarketService(provider)
    app.state.analysis = AnalysisService()
    yield
    await provider.close()


app = FastAPI(title="ORACLE API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "Idempotency-Key"])


def market_service(request: Request) -> MarketService:
    return request.app.state.markets


def analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis


@app.get("/health", response_model=HealthView, tags=["operations"])
async def health() -> HealthView:
    return HealthView(status="ok", environment=settings.environment)


@app.get("/api/v1/markets", response_model=list[MarketView], tags=["markets"])
async def markets(service: Annotated[MarketService, Depends(market_service)], limit: Annotated[int, Query(ge=1, le=500)] = 100) -> list[MarketView]:
    try:
        found = await service.scan(limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="market provider unavailable") from exc
    return [MarketView(id=item.id, question=item.question, description=item.description, yes_price=item.yes_price, no_price=item.no_price, liquidity=item.liquidity, volume=item.volume, closes_at=item.closes_at) for item in found]


@app.post("/api/v1/markets/{market_id}/analysis", response_model=AnalysisView, tags=["analysis"])
async def analyze_market(market_id: UUID, body: AnalysisInput, markets: Annotated[MarketService, Depends(market_service)], analysis: Annotated[AnalysisService, Depends(analysis_service)]) -> AnalysisView:
    market = markets.get(market_id)
    if market is None:
        raise HTTPException(status_code=404, detail="market has not been scanned")
    return analysis.analyze(market, body)
