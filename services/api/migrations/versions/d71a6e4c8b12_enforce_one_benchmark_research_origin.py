"""enforce one benchmark research origin

Revision ID: d71a6e4c8b12
Revises: c9036f1a52de
"""

from alembic import op

revision = "d71a6e4c8b12"
down_revision = "c9036f1a52de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("research_benchmarks") as batch:
        batch.create_check_constraint(
            op.f("ck_research_benchmarks_one_origin"),
            "(research_run_id IS NOT NULL AND refresh_item_id IS NULL) OR "
            "(research_run_id IS NULL AND refresh_item_id IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("research_benchmarks") as batch:
        batch.drop_constraint(op.f("ck_research_benchmarks_one_origin"), type_="check")
