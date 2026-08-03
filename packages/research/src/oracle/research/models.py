from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ResearchFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    supports_yes: bool
    source_url: HttpUrl
    citation: str
    source_quality: float = Field(ge=0, le=1)
    published_at: datetime | None


class ResearchBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")
    market_id: UUID
    yes_evidence: list[ResearchFinding]
    no_evidence: list[ResearchFinding]
    confidence: float = Field(ge=0, le=1)
    researched_at: datetime
