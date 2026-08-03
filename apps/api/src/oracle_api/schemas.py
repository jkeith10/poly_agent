from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from oracle.common.models import RecommendationAction


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketView(ApiModel):
    id: UUID
    question: str
    description: str
    yes_price: Decimal
    no_price: Decimal
    liquidity: Decimal
    volume: Decimal
    closes_at: datetime | None


class EvidenceInput(ApiModel):
    likelihood_ratio: Decimal = Field(gt=0)
    reliability: Decimal = Field(ge=0, le=1)
    independence_group: str = Field(min_length=1, max_length=255)
    citation: str = Field(min_length=1)


class AnalysisInput(ApiModel):
    prior: Decimal = Field(gt=0, lt=1)
    evidence: list[EvidenceInput]
    bankroll: Decimal = Field(gt=0)


class AnalysisView(ApiModel):
    market_id: UUID
    market_probability: Decimal
    oracle_probability: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    action: RecommendationAction
    edge: Decimal
    expected_value: Decimal
    fractional_kelly: Decimal
    suggested_position: Decimal
    reasoning: str
    citations: list[str]


class HealthView(ApiModel):
    status: str
    environment: str


class RecommendationView(ApiModel):
    prediction_id: UUID
    market_id: UUID
    question: str
    action: RecommendationAction
    market_probability: Decimal
    oracle_probability: Decimal
    lower_bound: Decimal
    upper_bound: Decimal
    edge: Decimal
    expected_value: Decimal
    fractional_kelly: Decimal
    suggested_position: Decimal
    reasoning: str
    citations: list[str]
    created_at: datetime


class PortfolioCreate(ApiModel):
    name: str = Field(min_length=1, max_length=255)
    bankroll: Decimal = Field(gt=0)


class PortfolioView(ApiModel):
    id: UUID
    name: str
    bankroll: Decimal
    created_at: datetime


class PositionCreate(ApiModel):
    market_id: UUID
    side: str = Field(pattern="^(YES|NO)$")
    quantity: Decimal = Field(gt=0)
    average_price: Decimal = Field(gt=0, lt=1)


class PositionView(ApiModel):
    id: UUID
    portfolio_id: UUID
    market_id: UUID
    side: str
    quantity: Decimal
    average_price: Decimal
    status: str
    opened_at: datetime
    resolved_at: datetime | None
    realized_pnl: Decimal | None


class ResolvePosition(ApiModel):
    outcome_yes: bool


class PortfolioPerformanceView(ApiModel):
    roi: Decimal
    win_rate: Decimal
    maximum_drawdown: Decimal
    sharpe_ratio: Decimal


class MarketResolutionInput(ApiModel):
    outcome_yes: bool


class ForecastEvaluationView(ApiModel):
    market_id: UUID
    predictions_evaluated: int
    mean_brier_score: Decimal
    mean_log_loss: Decimal
