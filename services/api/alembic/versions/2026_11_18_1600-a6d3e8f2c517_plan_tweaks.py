"""Plan tweaks: the Plan my week sheet's "This week" chips (slice 6e)

Revision ID: a6d3e8f2c517
Revises: f2c9a7d1b384
Create Date: 2026-11-18 16:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6d3e8f2c517"
down_revision: Union[str, Sequence[str], None] = "f2c9a7d1b384"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("plan_tweaks", postgresql.ARRAY(sa.String(length=20)), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "plan_tweaks")
