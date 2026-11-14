"""Where LangGraph saves each conversation's state: Postgres, via its own tables.

A checkpoint is a snapshot of the graph's state after each step. Saving them means a
conversation can continue later, from any device, and (slice 6) pause for approval.
Two steps, kept apart on purpose:
- setup() creates or migrates LangGraph's tables. Run it once at startup, never inside
  a request: its migrations use CREATE INDEX CONCURRENTLY, which waits until every other
  open transaction finishes, including the request's own, so it would wait forever.
- saver() opens the connection pool on first use, so tests and CLI tools that never run
  the agent don't need it.
"""

import asyncio

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Checkpoints:
    def __init__(self, database_url: str) -> None:
        self._url = database_url
        self._pool: AsyncConnectionPool | None = None
        self._saver: AsyncPostgresSaver | None = None
        self._lock = asyncio.Lock()

    async def saver(self) -> AsyncPostgresSaver:
        async with self._lock:
            if self._saver is None:
                # The settings LangGraph's Postgres saver needs: autocommit, dict rows,
                # and no server-side prepared statements (they break behind poolers).
                pool = AsyncConnectionPool(
                    self._url,
                    min_size=1,
                    max_size=5,
                    open=False,
                    kwargs={"autocommit": True, "prepare_threshold": None, "row_factory": dict_row},
                )
                await pool.open()
                self._pool = pool
                self._saver = AsyncPostgresSaver(pool)  # type: ignore[arg-type]
            return self._saver

    async def setup(self) -> None:
        """Create or migrate the checkpoint tables. Safe to repeat."""
        await (await self.saver()).setup()

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
