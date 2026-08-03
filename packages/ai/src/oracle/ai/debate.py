from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Argument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thesis: str
    evidence_ids: list[UUID] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class DebateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yes_case: Argument
    no_case: Argument
    critique: str
    consensus: str
    disagreements: list[str]
    confidence: float = Field(ge=0, le=1)


class StructuredGenerator(Protocol):
    async def generate(self, *, role: str, context: dict[str, object], schema: type[BaseModel]) -> BaseModel: ...


class StructuredDebate:
    def __init__(self, generator: StructuredGenerator) -> None:
        self.generator = generator

    async def run(self, context: dict[str, object]) -> DebateResult:
        result = await self.generator.generate(role="independent_prediction_market_debate", context=context, schema=DebateResult)
        if not isinstance(result, DebateResult):
            raise TypeError("generator returned an invalid debate schema")
        supplied = {UUID(str(item)) for item in context.get("evidence_ids", [])}
        cited = set(result.yes_case.evidence_ids + result.no_case.evidence_ids)
        if not cited <= supplied:
            raise ValueError("debate cited evidence outside supplied context")
        return result
