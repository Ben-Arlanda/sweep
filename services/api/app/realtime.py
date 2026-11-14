"""Change notices: tell a Household's connected devices that something changed.

Flow (ADR 0004):

    service commits a change ──► Postgres NOTIFY on `sweep_changes` (sent at COMMIT)
        ──► every API instance's `listen` loop ──► Hub ──► that Household's WebSockets

Notices carry ids and versions only, never data. Devices refetch through the normal
REST API, so every read still goes through the usual permission checks.

One shared channel, filtered here by household_id, rather than one channel per
Household. A per-Household channel would mean running LISTEN/UNLISTEN on a connection
that is busy waiting for notices. At household scale, every instance seeing every
notice costs nothing.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any

import psycopg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

CHANNEL = "sweep_changes"
Message = dict[str, Any]


async def notify_change(
    session: AsyncSession, household_id: uuid.UUID, entity: str, id: uuid.UUID, version: int
) -> None:
    """Queue a change notice. Postgres sends it only if this transaction commits."""
    payload = json.dumps(
        {"household_id": str(household_id), "entity": entity, "id": str(id), "version": version}
    )
    await session.execute(
        text("SELECT pg_notify(:channel, :payload)"), {"channel": CHANNEL, "payload": payload}
    )


class Hub:
    """In-memory fan-out from this API instance to its connected WebSockets.

    Each socket gets a small queue. If a device can't keep up (asleep, slow network),
    its queue is replaced with a single "resync": it has missed something, and a full
    refetch is cheaper than buffering an unbounded backlog.
    """

    def __init__(self, queue_size: int = 100) -> None:
        self._queue_size = queue_size
        self._subscribers: defaultdict[uuid.UUID, set[asyncio.Queue[Message]]] = defaultdict(set)
        self.ready = asyncio.Event()  # set while the listener is LISTENing

    def subscribe(self, household_id: uuid.UUID) -> asyncio.Queue[Message]:
        queue: asyncio.Queue[Message] = asyncio.Queue(maxsize=self._queue_size)
        self._subscribers[household_id].add(queue)
        return queue

    def unsubscribe(self, household_id: uuid.UUID, queue: asyncio.Queue[Message]) -> None:
        queues = self._subscribers.get(household_id)
        if queues is not None:
            queues.discard(queue)
            if not queues:
                del self._subscribers[household_id]

    def subscriber_count(self) -> int:
        return sum(len(q) for q in self._subscribers.values())

    def publish(self, household_id: uuid.UUID, message: Message) -> None:
        for queue in self._subscribers.get(household_id, ()):
            self._put(queue, message)

    def publish_all(self, message: Message) -> None:
        for queues in self._subscribers.values():
            for queue in queues:
                self._put(queue, message)

    @staticmethod
    def _put(queue: asyncio.Queue[Message], message: Message) -> None:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            while not queue.empty():
                queue.get_nowait()
            queue.put_nowait({"type": "resync"})


def dispatch(hub: Hub, payload: str) -> None:
    try:
        notice = json.loads(payload)
        household_id = uuid.UUID(notice.pop("household_id"))
    except (ValueError, KeyError, TypeError):
        log.warning("Ignoring malformed change notice: %r", payload)
        return
    hub.publish(household_id, {"type": "changed", **notice})


async def listen(database_url: str, hub: Hub) -> None:
    """Hold one LISTEN connection for the life of the app, reconnecting if it drops."""
    backoff = 1.0
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(database_url, autocommit=True) as conn:
                await conn.execute(f"LISTEN {CHANNEL}")
                hub.ready.set()
                # Anything committed while we were disconnected was never delivered.
                hub.publish_all({"type": "resync"})
                backoff = 1.0
                async for notice in conn.notifies():
                    dispatch(hub, notice.payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Change listener lost its connection; retrying in %ss", backoff)
        hub.ready.clear()
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 30.0)
