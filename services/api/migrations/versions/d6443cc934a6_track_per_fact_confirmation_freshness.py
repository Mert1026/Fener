"""track per-fact confirmation freshness

Revision ID: d6443cc934a6
Revises: c14de101428b
"""

import sqlalchemy as sa
from alembic import context, op

revision = "d6443cc934a6"
down_revision = "c14de101428b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite DDL is not transactional. Detect a partially applied local upgrade
    # so retrying this revision preserves the already-ingested evidence.
    inspector = None if context.is_offline_mode() else sa.inspect(op.get_bind())
    columns = {c["name"] for c in inspector.get_columns("source_claims")} if inspector else set()
    indexes = {i["name"] for i in inspector.get_indexes("source_claims")} if inspector else set()
    foreign_keys = (
        {tuple(f["constrained_columns"]) for f in inspector.get_foreign_keys("source_claims")}
        if inspector
        else set()
    )
    with op.batch_alter_table("source_claims") as batch:
        if "last_seen_at" not in columns:
            batch.add_column(sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        if "confirming_record_id" not in columns:
            batch.add_column(sa.Column("confirming_record_id", sa.String(64), nullable=True))
        if "ix_source_claims_observation_id" not in indexes:
            batch.create_index("ix_source_claims_observation_id", ["observation_id"])
        if ("confirming_record_id",) not in foreign_keys:
            batch.create_foreign_key(
                "fk_source_claims_confirming_record_id_source_records",
                "source_records",
                ["confirming_record_id"],
                ["id"],
            )


def downgrade() -> None:
    with op.batch_alter_table("source_claims") as batch:
        batch.drop_constraint(
            "fk_source_claims_confirming_record_id_source_records", type_="foreignkey"
        )
        batch.drop_index("ix_source_claims_observation_id")
        batch.drop_column("confirming_record_id")
        batch.drop_column("last_seen_at")
