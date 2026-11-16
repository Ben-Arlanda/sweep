"""Fetching one web page a Member linked, safely (slice 4d, the Link door).

A link is the one place the API fetches a URL a user chose, which makes it the classic
SSRF hole ("server-side request forgery"): a link to http://169.254.169.254/ or to
https://intranet.local/ would make our server fetch something only it can reach and
hand it back. So:

- **Plain https links only**: no credentials in the link, no odd ports.
- **Public addresses only, checked when connecting.** `PublicOnlyBackend` resolves the
  name, refuses it if *any* address isn't on the public internet, then connects to the
  address it checked. Checking and connecting are one step, so DNS can't answer one
  thing for the check and another for the connection (DNS rebinding). Every redirect
  opens a new connection, so every hop is checked too.
- **robots.txt must allow SweepBot**, for every host we visit.
- **At most 3 redirects, 2 MB, 10 seconds, HTML only.** The size counts decoded bytes,
  so a small compressed "zip bomb" can't grow past it.
- **No proxies from the environment** (`trust_env=False`): a proxy would connect for
  us, and its address checks aren't ours.
"""

import ipaddress
import socket
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import anyio
import httpcore
import httpx

from app import errors

USER_AGENT = "SweepBot/1.0"
MAX_BYTES = 2_000_000
MAX_ROBOTS_BYTES = 500_000  # RFC 9309 asks crawlers to read at least 500 KiB
MAX_REDIRECTS = 3
TIMEOUT = 10.0  # seconds, for everything: robots.txt, the page and its redirects
HTML_TYPES = {"text/html", "application/xhtml+xml"}
REDIRECTS = {301, 302, 303, 307, 308}

Resolver = Callable[[str, int], Awaitable[list[str]]]


@dataclass(frozen=True)
class Page:
    url: str  # where the page really is, after redirects
    html: str


class BlockedAddress(Exception):
    """The name resolves to an address that isn't on the public internet."""


# --- The rules --------------------------------------------------------------------------


def is_public(ip: str) -> bool:
    address = ipaddress.ip_address(ip)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped  # ::ffff:127.0.0.1 is 127.0.0.1
    # is_global is False for private, loopback, link-local (the metadata address),
    # carrier-grade NAT, reserved and unspecified ranges. Multicast isn't a website.
    return address.is_global and not address.is_multicast


def check_url(url: str) -> str:
    """The link, trimmed, if it's a plain https link. ValueError otherwise."""
    url = url.strip()
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise ValueError("Use an https:// link")
    if not parts.hostname or parts.username is not None or parts.password is not None:
        raise ValueError("That isn't a link to a web page")
    try:
        port = parts.port
    except ValueError as error:
        raise ValueError("That isn't a link to a web page") from error
    if port not in (None, 443):
        raise ValueError("That link uses an unusual port")
    if any(ch.isspace() or ord(ch) < 32 for ch in url):
        raise ValueError("That isn't a link to a web page")
    return url


# --- Connect-time address check -----------------------------------------------------------


async def _resolve(host: str, port: int) -> list[str]:
    found = await anyio.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return sorted({str(info[4][0]) for info in found})


class PublicOnlyBackend(httpcore.AsyncNetworkBackend):
    """Opens connections only to public addresses. Wraps httpcore's own backend."""

    def __init__(
        self, resolve: Resolver | None = None, inner: httpcore.AsyncNetworkBackend | None = None
    ) -> None:
        self._resolve = resolve or _resolve
        self._inner = inner or httpcore.AnyIOBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addresses = await self._resolve(host, port)
        if not addresses or not all(is_public(a) for a in addresses):
            raise BlockedAddress(host)
        # Connect by address, not name: no second DNS answer. httpcore still sends the
        # real hostname for TLS (SNI) and checks the certificate against it.
        return await self._inner.connect_tcp(
            addresses[0], port, timeout, local_address, socket_options
        )

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


def _public_only_transport() -> httpx.AsyncHTTPTransport:
    transport = httpx.AsyncHTTPTransport(trust_env=False, retries=0)
    # httpx doesn't let us pass a network backend, but its connection pool (httpcore)
    # does. Replacing the pool touches a private attribute: tests/test_web_fetch.py
    # checks it's still in place, so an httpx upgrade that moves it fails loudly.
    transport._pool = httpcore.AsyncConnectionPool(  # noqa: SLF001
        ssl_context=httpx.create_ssl_context(trust_env=False),
        network_backend=PublicOnlyBackend(),
    )
    return transport


# --- The fetcher ----------------------------------------------------------------------------


class SafeFetcher:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        *,
        timeout: float = TIMEOUT,
        max_bytes: int = MAX_BYTES,
        max_redirects: int = MAX_REDIRECTS,
    ) -> None:
        self.transport = transport or _public_only_transport()
        self._timeout, self._max_bytes, self._max_redirects = timeout, max_bytes, max_redirects

    async def fetch(self, url: str) -> Page:
        try:
            url = check_url(url)
        except ValueError as error:
            raise errors.InvalidInput(str(error)) from error
        async with httpx.AsyncClient(
            transport=self.transport,
            headers={"user-agent": USER_AGENT},
            follow_redirects=False,  # we follow them ourselves, checking each one
            trust_env=False,
            timeout=self._timeout,
        ) as client:
            try:
                with anyio.fail_after(self._timeout):
                    return await self._follow(client, url)
            except (TimeoutError, httpx.TimeoutException) as error:
                raise errors.Unavailable(
                    "That site didn't answer in time. Try again, or paste the recipe text."
                ) from error
            except BlockedAddress as error:
                raise errors.InvalidInput("That link can't be opened.") from error
            except httpx.TransportError as error:
                raise errors.Unavailable(
                    "That site couldn't be reached. Try again, or paste the recipe text."
                ) from error

    async def _follow(self, client: httpx.AsyncClient, url: str) -> Page:
        for _ in range(self._max_redirects + 1):
            if not await self._robots_allow(client, url):
                raise errors.InvalidInput(
                    "That site asks apps not to read its pages. Paste the recipe text instead."
                )
            async with client.stream("GET", url) as response:
                if response.status_code in REDIRECTS and "location" in response.headers:
                    try:
                        url = check_url(urljoin(url, response.headers["location"]))
                    except ValueError as error:
                        raise errors.InvalidInput(
                            "That link redirects somewhere that isn't https."
                        ) from error
                    continue
                if response.status_code != 200:
                    raise errors.InvalidInput(
                        f"That page couldn't be opened ({response.status_code})."
                    )
                kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if kind not in HTML_TYPES:
                    raise errors.InvalidInput("That link isn't a web page.")
                body = await self._read(response, self._max_bytes)
                if body is None:
                    raise errors.InvalidInput(
                        "That page is too big to read. Paste the recipe text instead."
                    )
                return Page(url=url, html=body.decode(response.encoding or "utf-8", "replace"))
        raise errors.InvalidInput("That link redirects too many times.")

    async def _robots_allow(self, client: httpx.AsyncClient, url: str) -> bool:
        """RFC 9309: no robots.txt (404 and most 4xx) means all allowed; a server error
        or no answer means assume nothing is. 401/403 we treat as "no" too."""
        parts = urlsplit(url)
        robots_url = f"https://{parts.netloc}/robots.txt"
        for _ in range(self._max_redirects + 1):
            async with client.stream("GET", robots_url) as response:
                status = response.status_code
                if status in REDIRECTS and "location" in response.headers:
                    try:
                        robots_url = check_url(urljoin(robots_url, response.headers["location"]))
                    except ValueError:
                        return False
                    continue
                if status in (401, 403) or status >= 500:
                    return False
                if status != 200:
                    return True
                body = await self._read(response, MAX_ROBOTS_BYTES)
                if body is None:
                    return False  # huge robots.txt: we can't read all its rules, so no
                rules = RobotFileParser()
                rules.parse(body.decode("utf-8", "replace").splitlines())
                return rules.can_fetch(USER_AGENT, url)
        return False

    @staticmethod
    async def _read(response: httpx.Response, limit: int) -> bytes | None:
        """The body, or None once it passes `limit` (stops reading there)."""
        chunks, size = [], 0
        async for chunk in response.aiter_bytes():  # decoded: gzip is already undone
            size += len(chunk)
            if size > limit:
                return None
            chunks.append(chunk)
        return b"".join(chunks)
