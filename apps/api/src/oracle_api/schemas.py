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
