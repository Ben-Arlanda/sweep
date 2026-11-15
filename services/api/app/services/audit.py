"""The audit log: an append-only record of decisions and what they changed (ADR 0005)."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Actor, AuditEntry


async def record(
    session: AsyncSession,
    household_id: uuid.UUID,
    action: str,
    entity: str,
    entity_id: uuid.UUID,
    *,
    member_id: uuid.UUID | None,
    actor: Actor = Actor.MEMBER,
    detail: dict[str, Any] | None = None,
) -> None:
    """Add an entry in the caller's transaction, so it's saved only if the change is."""
    session.add(
        AuditEntry(
            household_id=household_id,
            member_id=member_id,
            actor=actor,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail or {},
        )
    )
