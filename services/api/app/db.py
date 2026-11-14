"""Database plumbing: the SQLAlchemy base class and engine/session factories."""

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Predictable constraint names, so Alembic migrations can refer to them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def sqlalchemy_url(url: str) -> str:
    """Point plain `postgresql://` URLs at the psycopg 3 driver (works sync and async)."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def make_engine(url: str) -> AsyncEngine:
    return create_async_engine(sqlalchemy_url(url), pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    # expire_on_commit=False: after commit, keep loaded values readable. With async
    # SQLAlchemy, re-loading an expired attribute would need an `await` that a plain
    # attribute access can't do, and it fails with a confusing MissingGreenlet error.
    return async_sessionmaker(engine, expire_on_commit=False)
