"""The Voyage client, against a fake HTTP server (no network, no key)."""

import json

import httpx
import pytest

from app.embeddings import DIMENSIONS, EmbeddingUnavailable, HashingEmbedder, VoyageEmbedder

pytestmark = pytest.mark.anyio


def fake_voyage(responses: list[int]) -> tuple[httpx.MockTransport, list[dict[str, object]]]:
    """A server that answers with these status codes in turn, recording each request."""
    requests: list[dict[str, object]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        status = responses.pop(0) if responses else 200
        if status != 200:
            return httpx.Response(
                status, headers={"retry-after": "0"}, json={"detail": "slow down"}
            )
        data = [
            {"index": i, "embedding": [float(i)] * DIMENSIONS} for i in range(len(body["input"]))
        ]
        return httpx.Response(200, json={"data": data})

    return httpx.MockTransport(handle), requests


def embedder(transport: httpx.MockTransport, batch: int = 128) -> VoyageEmbedder:
    return VoyageEmbedder("key", "voyage-3.5", batch=batch, transport=transport, backoff=0)


async def test_batches_and_keeps_order() -> None:
    transport, requests = fake_voyage([])
    vectors = await embedder(transport, batch=2).embed(["a", "b", "c"], "document")
    assert [r["input"] for r in requests] == [["a", "b"], ["c"]]
    assert [v[0] for v in vectors] == [0.0, 1.0, 0.0]
    assert requests[0]["input_type"] == "document"


async def test_waits_and_retries_when_rate_limited() -> None:
    transport, requests = fake_voyage([429, 429])
    vectors = await embedder(transport).embed(["a"], "query")
    assert len(requests) == 3 and len(vectors) == 1


async def test_gives_up_after_too_many_retries() -> None:
    transport, _ = fake_voyage([429] * 10)
    with pytest.raises(EmbeddingUnavailable):
        await embedder(transport).embed(["a"], "query")


async def test_does_not_retry_a_bad_request() -> None:
    transport, requests = fake_voyage([400])
    with pytest.raises(EmbeddingUnavailable):
        await embedder(transport).embed(["a"], "query")
    assert len(requests) == 1  # retrying a 400 would fail the same way


async def test_fake_embedder_is_deterministic_and_unit_length() -> None:
    [a], [b] = (
        await HashingEmbedder().embed(["chicken curry"], "query"),
        [HashingEmbedder._vector("chicken curry")],
    )
    assert a == b
    assert sum(v * v for v in a) == pytest.approx(1.0)
