from datetime import datetime
import httpx
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from oracle.ai.debate import StructuredGenerator
from oracle.research.models import ResearchFinding


class SearchApiProvider:
    """Adapter for JSON search APIs that return an `organic` result list."""

    def __init__(
        self, *, endpoint: str, api_key: str, timeout: float = 15
    ) -> None:
        if not endpoint.startswith("https://"):
            raise ValueError("search API endpoint must use HTTPS")
        self.client = httpx.AsyncClient(
            timeout=timeout, headers={"X-API-KEY": api_key}
        )
        self.endpoint = endpoint

    async def close(self) -> None:
        await self.client.aclose()

    async def search(self, query: str, *, limit: int) -> list[str]:
        response = await self.client.post(
            self.endpoint, json={"q": query, "num": limit}
        )
        response.raise_for_status()
        organic = response.json().get("organic", [])
        return [str(item["link"]) for item in organic[:limit] if item.get("link")]


class ExtractedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    citation: str
    source_quality: float = Field(ge=0, le=1)
    published_at: datetime | None
    relevant: bool


class StructuredFindingExtractor:
    def __init__(self, generator: StructuredGenerator, *, maximum_text: int = 30_000) -> None:
        self.generator = generator
        self.maximum_text = maximum_text

    async def extract(
        self, *, market_question: str, supports_yes: bool, url: str, text: str
    ) -> ResearchFinding | None:
        result = await self.generator.generate(
            role="extract_verifiable_evidence",
            context={
                "market_question": market_question,
                "requested_side": "YES" if supports_yes else "NO",
                "source_url": url,
                "untrusted_source_text": text[: self.maximum_text],
            },
            schema=ExtractedFinding,
        )
        if not result.relevant or not result.citation.strip():
            return None
        return ResearchFinding(
            claim=result.claim,
            supports_yes=supports_yes,
            source_url=HttpUrl(url),
            citation=result.citation,
            source_quality=result.source_quality,
            published_at=result.published_at,
        )
