from datetime import UTC, datetime
from uuid import uuid4

import pytest

from oracle.research import ResearchAgent
from oracle.research.models import ResearchFinding
from oracle.research.retrieval import RetrievedSource


class Search:
    async def search(self, query: str, *, limit: int) -> list[str]:
        direction = "yes" if "supporting yes" in query else "no"
        return [f"https://example.com/{direction}"]


class Retriever:
    async def retrieve(self, url: str) -> RetrievedSource:
        return RetrievedSource(url=url, text="source text", retrieved_content_type="text/plain")


class Extractor:
    async def extract(
        self, *, market_question: str, supports_yes: bool, url: str, text: str
    ) -> ResearchFinding:
        return ResearchFinding(
            claim=f"Evidence for {supports_yes}",
            supports_yes=supports_yes,
            source_url=url,
            citation=text,
            source_quality=0.8,
            published_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_research_agent_balances_both_sides() -> None:
    agent = ResearchAgent(
        search=Search(),
        retriever=Retriever(),
        extractor=Extractor(),
        sources_per_side=1,
    )
    brief = await agent.research(uuid4(), "Will an event happen?")
    assert len(brief.yes_evidence) == 1
    assert len(brief.no_evidence) == 1
    assert brief.confidence == 1
