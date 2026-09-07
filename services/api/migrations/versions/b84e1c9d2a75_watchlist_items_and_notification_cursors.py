"""watchlist items and notification cursors

Revision ID: b84e1c9d2a75
Revises: d71a6e4c8b12
"""

import sqlalchemy as sa
from alembic import op

revision = "b84e1c9d2a75"
down_revision = "d71a6e4c8b12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watchlist_items")),
        sa.ForeignKeyConstraint(
            ["model_id"], ["models.id"], name=op.f("fk_watchlist_items_model_id_models")
        ),
    )
    op.create_index(
        op.f("ix_watchlist_items_model_id"), "watchlist_items", ["model_id"], unique=True
    )
    op.create_table(
        "notification_cursors",
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("last_notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("channel", name=op.f("pk_notification_cursors")),
    )


def downgrade() -> None:
    op.drop_table("notification_cursors")
    op.drop_index(op.f("ix_watchlist_items_model_id"), table_name="watchlist_items")
    op.drop_table("watchlist_items")
