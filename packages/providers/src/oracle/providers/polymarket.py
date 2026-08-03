import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import httpx

from oracle.common.models import Market


class PolymarketClient:
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com", timeout: float = 20) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def active_markets(self, limit: int = 100, offset: int = 0) -> list[Market]:
        response = await self._client.get("/markets", params={"active": "true", "closed": "false", "limit": limit, "offset": offset})
        response.raise_for_status()
        return [self._normalize(raw) for raw in response.json()]

    async def all_active_markets(
        self, *, page_size: int = 100, maximum: int = 5_000
    ) -> list[Market]:
        """Retrieve active markets page-by-page with an explicit safety ceiling."""
        if page_size < 1 or maximum < 1:
            raise ValueError("pagination limits must be positive")
        collected: list[Market] = []
        while len(collected) < maximum:
            page = await self.active_markets(
                limit=min(page_size, maximum - len(collected)), offset=len(collected)
            )
            collected.extend(page)
            if len(page) < page_size:
                break
        return collected

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> Market:
        outcomes = raw.get("outcomePrices", ["0.5", "0.5"])
        if isinstance(outcomes, str):
            outcomes = json.loads(outcomes)
        end = raw.get("endDate")
        return Market(
            id=uuid5(NAMESPACE_URL, f"polymarket:{raw['id']}"),
            provider="polymarket",
            external_id=str(raw["id"]),
            question=str(raw["question"]),
            description=str(raw.get("description") or ""),
            yes_price=Decimal(str(outcomes[0])),
            no_price=Decimal(str(outcomes[1])),
            liquidity=Decimal(str(raw.get("liquidityNum") or raw.get("liquidity") or 0)),
            volume=Decimal(str(raw.get("volumeNum") or raw.get("volume") or 0)),
            closes_at=datetime.fromisoformat(end.replace("Z", "+00:00")) if end else None,
        )
