"""Recipe Images: an approved photo and its credit on Seed Recipes (slice 4f, ADR 0027)

Revision ID: 1e533861b60f
Revises: d8c91ecb211e
Create Date: 2026-11-20 09:22:18.827613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1e533861b60f'
down_revision: Union[str, Sequence[str], None] = 'd8c91ecb211e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("image", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("recipes", "image")
