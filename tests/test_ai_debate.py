import asyncio
from typing import TypeVar, cast
from uuid import UUID, uuid4

from pydantic import BaseModel

from oracle.ai.debate import Argument, Critique, DebateResult, StructuredDebate, Synthesis

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class FakeGenerator:
    def __init__(self, evidence_id: UUID) -> None:
        self.evidence_id = evidence_id
        self.roles: list[str] = []

    async def generate(
        self, *, role: str, context: dict[str, object], schema: type[SchemaT]
    ) -> SchemaT:
        self.roles.append(role)
        if schema is Argument:
            value = Argument(
                thesis=f"{role} thesis",
                evidence_ids=[self.evidence_id],
                confidence=0.7,
            )
        elif schema is Critique:
            value = Critique(
                weaknesses=["limited sample"],
                unsupported_assumptions=[],
                evidence_ids=[self.evidence_id],
            )
        else:
            value = Synthesis(
                consensus="uncertain",
                disagreements=["base rate"],
                confidence=0.6,
                evidence_ids=[self.evidence_id],
            )
        return cast(SchemaT, value)


def test_debate_runs_independent_roles_and_validates_citations() -> None:
    evidence_id = uuid4()
    generator = FakeGenerator(evidence_id)
    result = asyncio.run(
        StructuredDebate(generator).run({"evidence_ids": [str(evidence_id)]})
    )
    assert isinstance(result, DebateResult)
    assert set(generator.roles) == {"argue_yes", "argue_no", "critique_both", "synthesize"}
