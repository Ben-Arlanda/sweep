"""The safe page fetcher (slice 4d, the Link door). No real network: a mock transport
plays the websites, and a fake resolver plays DNS.

Two layers, tested separately:
- PublicOnlyBackend: at connect time, refuse any address that isn't on the public
  internet (private networks, loopback, the cloud metadata address…)
- SafeFetcher: https only, robots.txt, at most 3 redirects, size, type and time limits
"""

from collections.abc import Awaitable, Callable
from typing import Any

import anyio
import httpcore
import httpx
import pytest

from app import errors
from app.web_fetch import BlockedAddress, PublicOnlyBackend, SafeFetcher, check_url, is_public

pytestmark = pytest.mark.anyio

HTML = {"content-type": "text/html; charset=utf-8"}


# --- Which addresses count as public -------------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "public"),
    [
        ("93.184.215.14", True),
        ("2606:4700::1111", True),
        ("10.0.0.5", False),  # a private network
        ("192.168.1.1", False),
        ("127.0.0.1", False),  # this machine
        ("169.254.169.254", False),  # the cloud metadata server: holds credentials
        ("100.64.0.1", False),  # carrier-grade NAT
        ("0.0.0.0", False),
        ("224.0.0.1", False),  # multicast
        ("::1", False),
        ("fd00::1", False),
        ("::ffff:127.0.0.1", False),  # IPv4 loopback dressed as IPv6
    ],
)
def test_only_public_internet_addresses_are_allowed(ip: str, public: bool) -> None:
    assert is_public(ip) is public


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/ragu",  # https only
        "https://user:pw@example.com/ragu",  # credentials in a link: never
        "https://example.com:8443/ragu",  # odd ports are how internal services hide
        "ftp://example.com",
        "example.com/ragu",
        "https:///ragu",
    ],
)
def test_links_must_be_plain_https(url: str) -> None:
    with pytest.raises(ValueError):
        check_url(url)


def test_a_good_link_passes() -> None:
    assert check_url("  https://Example.com/ragu?x=1  ") == "https://Example.com/ragu?x=1"


# --- PublicOnlyBackend: the check happens when connecting ---------------------------------


class FakeInner(httpcore.AsyncNetworkBackend):
    def __init__(self) -> None:
        self.connected: list[tuple[str, int]] = []

    async def connect_tcp(self, host: str, port: int, *args: Any, **kwargs: Any) -> Any:
        self.connected.append((host, port))
        return object()

    async def sleep(self, seconds: float) -> None:  # pragma: no cover
        pass


def resolver(answers: dict[str, list[str]]) -> Callable[[str, int], Awaitable[list[str]]]:
    async def resolve(host: str, port: int) -> list[str]:
        return answers[host]

    return resolve


@pytest.mark.parametrize("ips", [["10.0.0.5"], ["93.184.215.14", "169.254.169.254"]])
async def test_a_name_with_any_private_address_is_refused(ips: list[str]) -> None:
    inner = FakeInner()
    backend = PublicOnlyBackend(resolver({"evil.example": ips}), inner)
    with pytest.raises(BlockedAddress):
        await backend.connect_tcp("evil.example", 443)
    assert inner.connected == []


async def test_it_connects_to_the_address_it_checked() -> None:
    # Connecting by IP, not by name, means DNS can't give a different answer between
    # the check and the connection (DNS rebinding). TLS still checks the real hostname.
    inner = FakeInner()
    backend = PublicOnlyBackend(resolver({"good.example": ["93.184.215.14"]}), inner)
    await backend.connect_tcp("good.example", 443)
    assert inner.connected == [("93.184.215.14", 443)]


def test_the_real_fetcher_uses_the_public_only_backend() -> None:
    # Guards a private httpx detail we rely on (see app/web_fetch.py). If an httpx
    # upgrade moves it, this fails instead of the protection silently going away.
    transport = SafeFetcher().transport
    assert isinstance(transport, httpx.AsyncHTTPTransport)
    assert isinstance(transport._pool._network_backend, PublicOnlyBackend)  # noqa: SLF001


# --- SafeFetcher -----------------------------------------------------------------------------

Site = dict[str, httpx.Response | Callable[[], Awaitable[httpx.Response]]]


def fetcher_for(site: Site, seen: list[httpx.Request] | None = None, **limits: Any) -> SafeFetcher:
    async def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        answer = site.get(str(request.url), httpx.Response(404))
        return await answer() if callable(answer) else answer

    return SafeFetcher(transport=httpx.MockTransport(handle), **limits)


def recipe_page(body: str = "<html>ragu</html>") -> httpx.Response:
    return httpx.Response(200, headers=HTML, text=body)


async def test_fetches_a_page_when_robots_allows_and_says_who_it_is() -> None:
    seen: list[httpx.Request] = []
    fetcher = fetcher_for({"https://a.example/ragu": recipe_page()}, seen)  # no robots.txt
    page = await fetcher.fetch("https://a.example/ragu")
    assert (page.url, page.html) == ("https://a.example/ragu", "<html>ragu</html>")
    assert [str(r.url) for r in seen] == ["https://a.example/robots.txt", "https://a.example/ragu"]
    assert {r.headers["user-agent"] for r in seen} == {"SweepBot/1.0"}


@pytest.mark.parametrize(
    "robots",
    [
        httpx.Response(200, text="User-agent: SweepBot\nDisallow: /"),
        httpx.Response(200, text="User-agent: *\nDisallow: /ragu"),
        httpx.Response(403),  # robots.txt itself forbidden: treat as "no"
        httpx.Response(503),  # can't tell: treat as "no" (RFC 9309)
    ],
)
async def test_robots_txt_saying_no_stops_the_fetch(robots: httpx.Response) -> None:
    seen: list[httpx.Request] = []
    site: Site = {"https://a.example/robots.txt": robots, "https://a.example/ragu": recipe_page()}
    with pytest.raises(errors.InvalidInput, match="asks apps not to read"):
        await fetcher_for(site, seen).fetch("https://a.example/ragu")
    assert "https://a.example/ragu" not in [str(r.url) for r in seen]


async def test_robots_for_another_bot_doesnt_stop_us() -> None:
    robots = httpx.Response(200, text="User-agent: BadBot\nDisallow: /")
    site: Site = {"https://a.example/robots.txt": robots, "https://a.example/ragu": recipe_page()}
    assert (await fetcher_for(site).fetch("https://a.example/ragu")).html


def redirect(to: str) -> httpx.Response:
    return httpx.Response(301, headers={"location": to})


async def test_follows_up_to_three_redirects_checking_each_hosts_robots() -> None:
    seen: list[httpx.Request] = []
    site: Site = {
        "https://a.example/r": redirect("/r2"),
        "https://a.example/r2": redirect("https://b.example/r3"),
        "https://b.example/r3": redirect("https://b.example/ragu"),
        "https://b.example/ragu": recipe_page(),
    }
    page = await fetcher_for(site, seen).fetch("https://a.example/r")
    assert page.url == "https://b.example/ragu"
    assert "https://b.example/robots.txt" in [str(r.url) for r in seen]


async def test_a_fourth_redirect_is_refused() -> None:
    site: Site = {f"https://a.example/{n}": redirect(f"/{n + 1}") for n in range(4)}
    site["https://a.example/4"] = recipe_page()
    with pytest.raises(errors.InvalidInput, match="redirects"):
        await fetcher_for(site).fetch("https://a.example/0")


async def test_a_redirect_to_plain_http_is_refused() -> None:
    site: Site = {"https://a.example/r": redirect("http://a.example/ragu")}
    with pytest.raises(errors.InvalidInput, match="https"):
        await fetcher_for(site).fetch("https://a.example/r")


async def test_a_page_too_big_is_refused_without_reading_it_all() -> None:
    site: Site = {"https://a.example/big": recipe_page("x" * 5000)}
    with pytest.raises(errors.InvalidInput, match="too big"):
        await fetcher_for(site, max_bytes=1000).fetch("https://a.example/big")


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (
            httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF"),
            "web page",
        ),
        (httpx.Response(404), "couldn't be opened"),
    ],
)
async def test_only_html_pages_that_load_are_read(answer: httpx.Response, message: str) -> None:
    with pytest.raises(errors.InvalidInput, match=message):
        await fetcher_for({"https://a.example/x": answer}).fetch("https://a.example/x")


async def test_a_slow_site_runs_out_of_time() -> None:
    async def slow() -> httpx.Response:
        await anyio.sleep(5)
        return recipe_page()

    site: Site = {"https://a.example/slow": slow}
    with pytest.raises(errors.Unavailable, match="in time"):
        await fetcher_for(site, timeout=0.1).fetch("https://a.example/slow")


async def test_a_blocked_address_is_a_plain_refusal() -> None:
    async def handle(request: httpx.Request) -> httpx.Response:
        raise BlockedAddress("10.0.0.5")

    fetcher = SafeFetcher(transport=httpx.MockTransport(handle))
    with pytest.raises(errors.InvalidInput, match="can't be opened"):
        await fetcher.fetch("https://intranet.example/ragu")
