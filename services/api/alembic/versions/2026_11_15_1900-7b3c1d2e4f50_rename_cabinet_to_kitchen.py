"""rename Cabinet to Kitchen (ADR 0011)

A rename, not drop-and-create: autogenerate would see a "new" kitchen_items table and
an "old" cabinet_items table and lose every row. Constraint and index names are renamed
too, so they keep matching the naming convention and later autogenerates stay quiet.

Revision ID: 7b3c1d2e4f50
Revises: ce2f1634afaf
Create Date: 2026-11-15 19:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "7b3c1d2e4f50"
down_revision: str | Sequence[str] | None = "ce2f1634afaf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINTS = [
    ("pk_cabinet_items", "pk_kitchen_items"),
    ("uq_cabinet_items_household_id_ingredient_id", "uq_kitchen_items_household_id_ingredient_id"),
    ("fk_cabinet_items_household_id_households", "fk_kitchen_items_household_id_households"),
    ("fk_cabinet_items_ingredient_id_ingredients", "fk_kitchen_items_ingredient_id_ingredients"),
    ("ck_cabinet_items_quantity_not_negative", "ck_kitchen_items_quantity_not_negative"),
    ("ck_cabinet_items_cabinet_change_source", "ck_kitchen_items_kitchen_change_source"),
]
INDEXES = [("ix_cabinet_items_household_id", "ix_kitchen_items_household_id")]
COLUMNS = [
    ("households", "cabinet_version", "kitchen_version"),
    ("shopping_list_items", "cabinet_applied", "kitchen_applied"),
    ("shopping_list_items", "cabinet_added_quantity", "kitchen_added_quantity"),
]


def _rename(table: str, old_table: str, pairs: list[tuple[str, str]], forward: bool) -> None:
    op.rename_table(old_table, table)
    for old, new in CONSTRAINTS if forward else [(n, o) for o, n in CONSTRAINTS]:
        op.execute(f"ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new}")
    for old, new in INDEXES if forward else [(n, o) for o, n in INDEXES]:
        op.execute(f"ALTER INDEX {old} RENAME TO {new}")
    for tbl, old, new in pairs:
        op.alter_column(tbl, old, new_column_name=new)


def upgrade() -> None:
    _rename("kitchen_items", "cabinet_items", COLUMNS, forward=True)


def downgrade() -> None:
    _rename("cabinet_items", "kitchen_items", [(t, n, o) for t, o, n in COLUMNS], forward=False)
