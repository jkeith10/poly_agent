from typing import Any

import httpx
import pytest

from oracle.providers import PolymarketClient


@pytest.mark.asyncio
async def test_all_active_markets_paginates_until_short_page() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        offset = int(request.url.params["offset"])
        size = 2 if offset == 0 else 1
        payload: list[dict[str, Any]] = [
            {
                "id": f"market-{offset + index}",
                "question": "A test market?",
                "outcomePrices": ["0.4", "0.6"],
            }
            for index in range(size)
        ]
        return httpx.Response(200, json=payload)

    client = PolymarketClient("https://example.test")
    await client._client.aclose()
    client._client = httpx.AsyncClient(
        base_url="https://example.test", transport=httpx.MockTransport(handler)
    )
    try:
        markets = await client.all_active_markets(page_size=2, maximum=10)
    finally:
        await client.close()
    assert len(markets) == 3
    assert [request.url.params["offset"] for request in requests] == ["0", "2"]
