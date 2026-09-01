"""queue full-catalog benchmark research refreshes

Revision ID: c9036f1a52de
Revises: b2d17a4f3c91
"""

import sqlalchemy as sa
from alembic import op

revision = "c9036f1a52de"
down_revision = "b2d17a4f3c91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "benchmark_refreshes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("total_models", sa.Integer(), nullable=False),
        sa.Column("processed_models", sa.Integer(), nullable=False),
        sa.Column("imported_results", sa.Integer(), nullable=False),
        sa.Column("failed_models", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_benchmark_refreshes")),
    )
    op.create_index(op.f("ix_benchmark_refreshes_status"), "benchmark_refreshes", ["status"])
    op.create_table(
        "benchmark_refresh_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("refresh_id", sa.String(length=36), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("imported_results", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["model_id"], ["models.id"], name=op.f("fk_benchmark_refresh_items_model_id_models")
        ),
        sa.ForeignKeyConstraint(
            ["refresh_id"],
            ["benchmark_refreshes.id"],
            name=op.f("fk_benchmark_refresh_items_refresh_id_benchmark_refreshes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_benchmark_refresh_items")),
    )
    op.create_index(
        op.f("ix_benchmark_refresh_items_model_id"), "benchmark_refresh_items", ["model_id"]
    )
    op.create_index(
        op.f("ix_benchmark_refresh_items_refresh_id"), "benchmark_refresh_items", ["refresh_id"]
    )
    op.create_index(
        op.f("ix_benchmark_refresh_items_status"), "benchmark_refresh_items", ["status"]
    )
    with op.batch_alter_table("research_benchmarks") as batch:
        batch.alter_column("research_run_id", existing_type=sa.String(length=36), nullable=True)
        batch.add_column(sa.Column("refresh_item_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            op.f("fk_research_benchmarks_refresh_item_id_benchmark_refresh_items"),
            "benchmark_refresh_items",
            ["refresh_item_id"],
            ["id"],
        )
        batch.create_index(op.f("ix_research_benchmarks_refresh_item_id"), ["refresh_item_id"])


def downgrade() -> None:
    # Refresh-created rows cannot be represented by the previous schema.
    op.execute(sa.text("DELETE FROM research_benchmarks WHERE research_run_id IS NULL"))
    with op.batch_alter_table("research_benchmarks") as batch:
        batch.drop_index(op.f("ix_research_benchmarks_refresh_item_id"))
        batch.drop_constraint(
            op.f("fk_research_benchmarks_refresh_item_id_benchmark_refresh_items"),
            type_="foreignkey",
        )
        batch.drop_column("refresh_item_id")
        batch.alter_column("research_run_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_index(op.f("ix_benchmark_refresh_items_status"), table_name="benchmark_refresh_items")
    op.drop_index(
        op.f("ix_benchmark_refresh_items_refresh_id"), table_name="benchmark_refresh_items"
    )
    op.drop_index(op.f("ix_benchmark_refresh_items_model_id"), table_name="benchmark_refresh_items")
    op.drop_table("benchmark_refresh_items")
    op.drop_index(op.f("ix_benchmark_refreshes_status"), table_name="benchmark_refreshes")
    op.drop_table("benchmark_refreshes")
