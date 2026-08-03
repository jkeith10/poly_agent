import asyncio
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from oracle.research.models import ResearchBrief, ResearchFinding
from oracle.research.retrieval import RetrievedSource


class SearchProvider(Protocol):
    async def search(self, query: str, *, limit: int) -> list[str]: ...


class FindingExtractor(Protocol):
    async def extract(
        self, *, market_question: str, supports_yes: bool, url: str, text: str
    ) -> ResearchFinding | None: ...


class SourceRetriever(Protocol):
    async def retrieve(self, url: str) -> RetrievedSource: ...


class ResearchAgent:
    """Runs symmetric, independent research for both outcomes."""

    def __init__(
        self,
        *,
        search: SearchProvider,
        retriever: SourceRetriever,
        extractor: FindingExtractor,
        sources_per_side: int = 5,
    ) -> None:
        self.search = search
        self.retriever = retriever
        self.extractor = extractor
        self.sources_per_side = sources_per_side

    async def _research_side(
        self, question: str, *, supports_yes: bool
    ) -> list[ResearchFinding]:
        direction = "evidence supporting yes" if supports_yes else "evidence supporting no"
        urls = await self.search.search(
            f"{question} {direction}", limit=self.sources_per_side
        )
        sources = await asyncio.gather(
            *(self.retriever.retrieve(url) for url in urls), return_exceptions=True
        )
        findings: list[ResearchFinding] = []
        for source in sources:
            if isinstance(source, BaseException):
                continue
            finding = await self.extractor.extract(
                market_question=question,
                supports_yes=supports_yes,
                url=source.url,
                text=source.text,
            )
            if finding is not None and finding.supports_yes == supports_yes:
                findings.append(finding)
        return findings

    async def research(self, market_id: UUID, question: str) -> ResearchBrief:
        yes, no = await asyncio.gather(
            self._research_side(question, supports_yes=True),
            self._research_side(question, supports_yes=False),
        )
        source_count = len(yes) + len(no)
        balance = min(len(yes), len(no)) / max(1, max(len(yes), len(no)))
        confidence = min(1.0, source_count / (self.sources_per_side * 2)) * balance
        return ResearchBrief(
            market_id=market_id,
            yes_evidence=yes,
            no_evidence=no,
            confidence=confidence,
            researched_at=datetime.now(UTC),
        )
