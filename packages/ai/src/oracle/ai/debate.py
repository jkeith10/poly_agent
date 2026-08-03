import asyncio
from typing import Protocol, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class Argument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thesis: str
    evidence_ids: list[UUID] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class Critique(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weaknesses: list[str]
    unsupported_assumptions: list[str]
    evidence_ids: list[UUID]


class Synthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consensus: str
    disagreements: list[str]
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[UUID] = Field(min_length=1)


class DebateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    yes_case: Argument
    no_case: Argument
    critique: Critique
    synthesis: Synthesis


class StructuredGenerator(Protocol):
    async def generate(
        self, *, role: str, context: dict[str, object], schema: type[SchemaT]
    ) -> SchemaT: ...


class StructuredDebate:
    """Runs independent advocates before critique and synthesis."""

    def __init__(self, generator: StructuredGenerator) -> None:
        self.generator = generator

    async def run(self, context: dict[str, object]) -> DebateResult:
        yes_case, no_case = await asyncio.gather(
            self.generator.generate(role="argue_yes", context=context, schema=Argument),
            self.generator.generate(role="argue_no", context=context, schema=Argument),
        )
        debate_context = {**context, "yes_case": yes_case.model_dump(mode="json"), "no_case": no_case.model_dump(mode="json")}
        critique = await self.generator.generate(
            role="critique_both", context=debate_context, schema=Critique
        )
        synthesis = await self.generator.generate(
            role="synthesize",
            context={**debate_context, "critique": critique.model_dump(mode="json")},
            schema=Synthesis,
        )
        supplied = {UUID(str(item)) for item in context.get("evidence_ids", [])}
        cited = set(
            yes_case.evidence_ids
            + no_case.evidence_ids
            + critique.evidence_ids
            + synthesis.evidence_ids
        )
        if not cited <= supplied:
            raise ValueError("debate cited evidence outside supplied context")
        return DebateResult(
            yes_case=yes_case,
            no_case=no_case,
            critique=critique,
            synthesis=synthesis,
        )
