"""everyday default Staples: adds brown sugar, honey, tomato sauce, mayonnaise, coffee,
butter, bread
and eggs; drops rarely used ones (celery salt, sage...) from the defaults

Data only. Loads the starter list again so the new flags land, then gives existing
Households the new defaults. Their current Staples are kept. Downgrade leaves the data.

Revision ID: b7d41e9c2a63
Revises: 9526c8fd843d
Create Date: 2026-11-23 12:00:00

"""

from typing import Sequence, Union

from alembic import op

from app.seed import add_default_staples, upsert_ingredients


# revision identifiers, used by Alembic.
revision: str = "b7d41e9c2a63"
down_revision: Union[str, Sequence[str], None] = "9526c8fd843d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_DEFAULTS = (
    "brown sugar",
    "honey",
    "tomato sauce",
    "mayonnaise",
    "coffee",
    "butter",
    "bread",
    "eggs",
)


def upgrade() -> None:
    upsert_ingredients(op.get_bind())
    add_default_staples(op.get_bind(), NEW_DEFAULTS)


def downgrade() -> None:
    pass  # see the module docstring
