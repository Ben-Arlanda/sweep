"""Alembic migration runner.

Uses a plain (sync) psycopg connection; the app uses the same driver in async mode.
The database URL comes from app settings unless a caller (e.g. the test suite) sets
`sqlalchemy.url` explicitly.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # noqa: F401  (registers the tables on Base.metadata)
from app.config import settings
from app.db import Base, sqlalchemy_url

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata
url = config.get_main_option("sqlalchemy.url") or sqlalchemy_url(settings.database_url)


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (`alembic upgrade head --sql`)."""
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
