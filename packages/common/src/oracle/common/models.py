from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

Probability = Annotated[Decimal, Field(ge=0, le=1)]


def utc_now() -> datetime:
    return datetime.now(UTC)


class RecommendationAction(StrEnum):
    BUY_YES = "BUY_YES"
    BUY_NO = "BUY_NO"
    SELL = "SELL"
    PASS = "PASS"


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Market(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    provider: str
    external_id: str
    question: str
    description: str = ""
    yes_price: Probability
    no_price: Probability
    liquidity: Decimal = Decimal(0)
    volume: Decimal = Decimal(0)
    closes_at: datetime | None = None
    observed_at: datetime = Field(default_factory=utc_now)


class Evidence(DomainModel):
    id: UUID = Field(default_factory=uuid4)
    market_id: UUID
    claim: str
    supports_yes: bool
    source_url: str
    citation: str
    reliability: Probability
    freshness: Probability
    importance: Probability
    independence_group: str
    observed_at: datetime = Field(default_factory=utc_now)


class ProbabilityEstimate(DomainModel):
    market_id: UUID
    prior: Probability
    posterior: Probability
    lower_bound: Probability
    upper_bound: Probability
    evidence_ids: tuple[UUID, ...]
    explanation: str
    created_at: datetime = Field(default_factory=utc_now)


class Recommendation(DomainModel):
    market_id: UUID
    action: RecommendationAction
    market_probability: Probability
    oracle_probability: Probability
    edge: Decimal
    expected_value: Decimal
    fractional_kelly: Decimal
    suggested_position: Decimal
    reasoning: str
