"""Turning text into vectors for recipe search. The only module that talks to Voyage AI.

An embedding is a list of numbers (here 1,024) that places a piece of text in "meaning
space": texts about similar things end up close together, even with no words in common
("quick weeknight noodles" lands near "15-minute stir-fry"). Search then means "find the
recipe vectors closest to the query's vector".

Every vector is stored with the model that made it. Vectors from different models aren't
comparable, so switching models means re-embedding, never mixing.
"""

import asyncio
import hashlib
import logging
import math
import re
from typing import Literal, Protocol

import httpx

log = logging.getLogger(__name__)

DIMENSIONS = 1024  # the recipe_embeddings column is fixed at this size

Purpose = Literal["document", "query"]


class Embedder(Protocol):
    model: str

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        """One vector per text, in order. `purpose`: are these recipes or a search?"""
        ...


class EmbeddingUnavailable(Exception):
    pass


class VoyageEmbedder:
    """Voyage AI's embeddings API, called directly over HTTP (it's one small endpoint).

    Rate limits are normal, not exceptional: a 429 means "slow down", so we wait and try
    again, a few times, getting slower each time ("exponential backoff"). Other errors
    (a bad key, a malformed request) would fail the same way again, so they don't retry.
    """

    URL = "https://api.voyageai.com/v1/embeddings"
    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        batch: int = 128,  # Voyage's maximum texts per request
        retries: int = 5,
        backoff: float = 5.0,  # seconds before the first retry; doubles each time
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,  # tests pass a fake server
    ) -> None:
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._batch, self._retries, self._backoff = batch, retries, backoff
        self._timeout, self._transport = timeout, transport

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        vectors: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as http:
            for start in range(0, len(texts), self._batch):
                vectors += await self._embed_batch(
                    http, texts[start : start + self._batch], purpose
                )
        return vectors

    async def _embed_batch(
        self, http: httpx.AsyncClient, batch: list[str], purpose: Purpose
    ) -> list[list[float]]:
        body = {
            "input": batch,
            "model": self.model,
            # Voyage tunes the vector for its role: a short question vs a longer
            # document. Using the right one measurably helps search.
            "input_type": purpose,
            "output_dimension": DIMENSIONS,
        }
        for attempt in range(self._retries + 1):
            try:
                response = await http.post(self.URL, headers=self._headers, json=body)
            except httpx.TransportError as error:  # network trouble: worth another try
                status, detail = None, str(error)
            else:
                if response.status_code == 200:
                    data = sorted(response.json()["data"], key=lambda d: d["index"])
                    return [d["embedding"] for d in data]
                status, detail = response.status_code, response.text[:200]
            if status is not None and status not in self.RETRYABLE:
                break
            if attempt < self._retries:
                wait = self._backoff * 2**attempt
                if status is not None and response.headers.get("retry-after", "").isdigit():
                    wait = max(wait, float(response.headers["retry-after"]))
                log.warning("Voyage %s; retrying in %.0fs", status or detail, wait)
                await asyncio.sleep(wait)
        raise EmbeddingUnavailable(f"Voyage request failed ({status}): {detail}")


class HashingEmbedder:
    """A fake for tests and CI: no network, no key, same answer every run.

    Each word is hashed to one of the 1,024 positions ("feature hashing"), so texts that
    share words get similar vectors. It understands nothing (no synonyms), but it is
    good enough to test that search, filters and ranking are wired up correctly.
    """

    model = "fake-hashing-v1"

    async def embed(self, texts: list[str], purpose: Purpose) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for word in re.findall(r"[a-z]+", text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % DIMENSIONS] += 1.0
        length = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / length for v in vector]
