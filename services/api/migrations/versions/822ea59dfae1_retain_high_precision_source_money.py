"""retain high precision source money

Revision ID: 822ea59dfae1
Revises: 8f708c750d19
"""

import sqlalchemy as sa
from alembic import op

revision = "822ea59dfae1"
down_revision = "8f708c750d19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("pricing_observations") as batch:
        batch.alter_column(
            "amount",
            existing_type=sa.NUMERIC(30, 12),
            type_=sa.Numeric(60, 30),
            existing_nullable=False,
        )


def downgrade() -> None:
    raise RuntimeError("Refusing a lossy money precision downgrade; restore a backup instead")
