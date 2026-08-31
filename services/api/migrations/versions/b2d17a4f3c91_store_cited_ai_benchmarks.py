"""store cited AI benchmark claims separately from source-ingested facts

Revision ID: b2d17a4f3c91
Revises: a708b414fa98
"""

import sqlalchemy as sa
from alembic import op

revision = "b2d17a4f3c91"
down_revision = "a708b414fa98"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_benchmarks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("research_run_id", sa.String(length=36), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("metric", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("evaluator", sa.String(length=300), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("reported_date", sa.String(length=40), nullable=True),
        sa.Column("higher_is_better", sa.Boolean(), nullable=True),
        sa.Column("score_min", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("score_max", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"], ["models.id"], name=op.f("fk_research_benchmarks_model_id_models")
        ),
        sa.ForeignKeyConstraint(
            ["research_run_id"],
            ["research_runs.id"],
            name=op.f("fk_research_benchmarks_research_run_id_research_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_research_benchmarks")),
    )
    op.create_index(op.f("ix_research_benchmarks_model_id"), "research_benchmarks", ["model_id"])
    op.create_index(op.f("ix_research_benchmarks_name"), "research_benchmarks", ["name"])
    op.create_index(
        op.f("ix_research_benchmarks_research_run_id"), "research_benchmarks", ["research_run_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_research_benchmarks_research_run_id"), table_name="research_benchmarks")
    op.drop_index(op.f("ix_research_benchmarks_name"), table_name="research_benchmarks")
    op.drop_index(op.f("ix_research_benchmarks_model_id"), table_name="research_benchmarks")
    op.drop_table("research_benchmarks")
