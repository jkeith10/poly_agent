import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import httpx


@dataclass(frozen=True, slots=True)
class Notification:
    subject: str
    message: str
    market_url: str


class Notifier(Protocol):
    async def send(self, notification: Notification) -> None: ...


class WebhookNotifier:
    """Delivers Discord, Slack, Telegram-proxy, or browser-gateway webhooks."""

    def __init__(self, url: str, *, timeout: float = 10) -> None:
        if not url.startswith("https://"):
            raise ValueError("notification webhook must use HTTPS")
        self.url = url
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def send(self, notification: Notification) -> None:
        response = await self.client.post(
            self.url,
            json={
                "text": f"{notification.subject}\n{notification.message}\n{notification.market_url}",
                "notification": {
                    "subject": notification.subject,
                    "message": notification.message,
                    "market_url": notification.market_url,
                },
            },
        )
        response.raise_for_status()


class EmailNotifier:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        recipient: str,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender
        self.recipient = recipient

    async def send(self, notification: Notification) -> None:
        message = EmailMessage()
        message["Subject"] = notification.subject
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content(f"{notification.message}\n\n{notification.market_url}")

        def deliver() -> None:
            with smtplib.SMTP_SSL(self.host, self.port, timeout=10) as client:
                client.login(self.username, self.password)
                client.send_message(message)

        await asyncio.to_thread(deliver)
