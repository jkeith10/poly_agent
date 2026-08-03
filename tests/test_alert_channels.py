import httpx
import pytest

from oracle.alerts.channels import Notification, WebhookNotifier


@pytest.mark.asyncio
async def test_webhook_notification_uses_structured_payload() -> None:
    payloads: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(__import__("json").loads(request.content))
        return httpx.Response(204)

    notifier = WebhookNotifier("https://alerts.example.test/hook")
    await notifier.client.aclose()
    notifier.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        await notifier.send(Notification("Positive EV", "BUY YES", "https://oracle/market/1"))
    finally:
        await notifier.close()
    assert payloads[0]["notification"] == {
        "subject": "Positive EV",
        "message": "BUY YES",
        "market_url": "https://oracle/market/1",
    }
