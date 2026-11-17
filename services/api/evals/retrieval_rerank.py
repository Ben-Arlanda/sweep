"""R4: Voyage's reranker, for the retrieval eval only (slice 9, measured not shipped).

A reranker reads the query and each document *together* and scores how well they fit
(a "cross-encoder"). Embeddings can't do that: a recipe's vector is made before anyone
searches. That's why reranking is slower and costs a call per search, and why it's
only used on a shortlist (R3's top 30), never the whole library.

Results are cached on disk by model + query + documents, so re-running the report is free
and the free tier's 3 requests a minute only bite once.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Sequence
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

CACHE = Path(__file__).resolve().parent / ".cache"
MODEL = "rerank-2.5"


class VoyageReranker:
    URL = "https://api.voyageai.com/v1/rerank"
    RETRYABLE = {429, 500, 502, 503, 504}

    def __init__(self, api_key: str, model: str = MODEL, retries: int = 6) -> None:
        self.model = model
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._retries = retries
        self.path = CACHE / f"rerank-{model}.json"
        self._cache: dict[str, list[int]] = (
            json.loads(self.path.read_text()) if self.path.exists() else {}
        )
        self.calls = 0
        self.tokens = 0

    def _key(self, query: str, documents: Sequence[str]) -> str:
        return hashlib.sha256(json.dumps([self.model, query, list(documents)]).encode()).hexdigest()

    async def rerank(self, query: str, documents: Sequence[str]) -> list[int]:
        """Positions in `documents`, best first."""
        key = self._key(query, documents)
        if key not in self._cache:
            self._cache[key] = await self._call(query, documents)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._cache))
        return self._cache[key]

    async def _call(self, query: str, documents: Sequence[str]) -> list[int]:
        body = {"query": query, "documents": list(documents), "model": self.model}
        async with httpx.AsyncClient(timeout=60) as http:
            for attempt in range(self._retries + 1):
                response = await http.post(self.URL, headers=self._headers, json=body)
                if response.status_code == 200:
                    payload = response.json()
                    self.calls += 1
                    self.tokens += payload.get("usage", {}).get("total_tokens", 0)
                    ranked = sorted(payload["data"], key=lambda d: -d["relevance_score"])
                    return [d["index"] for d in ranked]
                if response.status_code not in self.RETRYABLE or attempt == self._retries:
                    break
                wait = 21.0 * (attempt + 1)  # 3 requests a minute on the free tier
                log.warning("Voyage rerank %s; retrying in %.0fs", response.status_code, wait)
                await asyncio.sleep(wait)
        raise RuntimeError(f"Voyage rerank failed ({response.status_code}): {response.text[:200]}")
