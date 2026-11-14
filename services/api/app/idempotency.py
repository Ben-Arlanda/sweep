"""Idempotency keys: make "send it again" safe.

A phone on bad supermarket signal often can't tell whether a request failed or only the
reply was lost, so it retries. Each mutation carries an `Idempotency-Key` (a UUID the
device makes once per intended change). The first request with a key does the work and
stores the response; a retry with that key gets the stored response and changes nothing.

Race safety comes from Postgres: the key row is inserted in the *same transaction* as
the change. If a retry arrives while the first attempt is still running, its insert waits
on the same primary key until the first one commits (then it replays) or rolls back
(then it does the work itself). A failed request leaves no row, so it can be retried.
"""

import hashlib
import uuid
from typing import Annotated, Any

from fastapi import Header, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import IdempotencyKeyReused
from app.models import IdempotencyKey

IdempotencyKeyHeader = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]


def fingerprint(request: Request, body: bytes) -> bytes:
    return hashlib.sha256(
        b"\n".join([request.method.encode(), request.url.path.encode(), body])
    ).digest()


class Replay:
    """The stored outcome of an earlier attempt with the same key."""

    def __init__(self, status_code: int, response: dict[str, Any] | None) -> None:
        self.status_code = status_code
        self.response = response


async def claim(
    session: AsyncSession, member_id: uuid.UUID, key: str, print_: bytes
) -> Replay | None:
    """Reserve `key` for this request. Returns the earlier outcome if it was already used.

    The row starts with a placeholder status; `record` fills in the real result before
    commit, so other transactions only ever see a finished row.
    """
    inserted = await session.execute(
        insert(IdempotencyKey)
        .values(member_id=member_id, key=key, fingerprint=print_, status_code=0)
        .on_conflict_do_nothing()
        .returning(IdempotencyKey.key)
    )
    if inserted.scalar_one_or_none() is not None:
        return None  # first time: go ahead

    existing = (
        await session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.member_id == member_id, IdempotencyKey.key == key
            )
        )
    ).scalar_one()
    if existing.fingerprint != print_:
        raise IdempotencyKeyReused("This Idempotency-Key was already used for a different request")
    return Replay(existing.status_code, existing.response)


async def record(
    session: AsyncSession,
    member_id: uuid.UUID,
    key: str,
    status_code: int,
    response: dict[str, Any] | None,
) -> None:
    row = await session.get_one(IdempotencyKey, (member_id, key))
    row.status_code = status_code
    row.response = response
