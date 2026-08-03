import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx


@dataclass(frozen=True, slots=True)
class RetrievedSource:
    url: str
    text: str
    retrieved_content_type: str


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.ignored += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data: str) -> None:
        if not self.ignored:
            self.parts.append(data.strip())


class SafeSourceRetriever:
    """Retrieves public HTTP sources while blocking private-network SSRF targets."""

    def __init__(self, *, timeout: float = 15, maximum_bytes: int = 2_000_000) -> None:
        self.maximum_bytes = maximum_bytes
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    async def close(self) -> None:
        await self.client.aclose()

    async def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source URL must use public HTTP or HTTPS")
        addresses = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, parsed.port or 443
        )
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if not ip.is_global:
                raise ValueError("source URL resolves to a non-public address")

    async def retrieve(self, url: str) -> RetrievedSource:
        await self._validate_url(url)
        response = await self.client.get(url)
        response.raise_for_status()
        if len(response.content) > self.maximum_bytes:
            raise ValueError("source exceeds retrieval size limit")
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if content_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
            raise ValueError("unsupported source content type")
        if content_type == "text/plain":
            text = response.text
        else:
            parser = _TextExtractor()
            parser.feed(response.text)
            text = " ".join(part for part in parser.parts if part)
        return RetrievedSource(url=str(response.url), text=text, retrieved_content_type=content_type)
