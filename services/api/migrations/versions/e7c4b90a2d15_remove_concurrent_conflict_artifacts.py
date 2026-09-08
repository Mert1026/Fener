"""Remove concurrent-conflict artifacts from duplicate source entries.

Revision ID: e7c4b90a2d15
Revises: b84e1c9d2a75
Create Date: 2026-01-01

Sources such as LiteLLM publish some models under two keys. Before the
concurrent-observation guard, both keys resolved to one deployment and each
sync recorded their disagreement as pairs of opposite-direction changes at
the same instant. This data cleanup keeps the displayed value of every
affected chain, drops the contradictory half-writes, and preserves all raw
snapshots for provenance.
"""

from alembic import op
from fener.maintenance import purge_concurrent_conflict_artifacts

revision = "e7c4b90a2d15"
down_revision = "b84e1c9d2a75"
branch_labels = None
depends_on = None


def upgrade() -> None:
    purge_concurrent_conflict_artifacts(op.get_bind())


def downgrade() -> None:
    # Removed half-writes are not recoverable; raw snapshots remain.
    pass
