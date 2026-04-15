"""Add user interaction events table for recommendation ingestion."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "002_add_user_interaction_events"
down_revision = "001_initial_setup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create user_interaction_events table."""
    op.create_table(
        "user_interaction_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fragrance_neo4j_id", sa.String(length=100), nullable=False),
        sa.Column("interaction_type", sa.String(length=50), nullable=False),
        sa.Column("interaction_value", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_user_interaction_events_user_id"),
        "user_interaction_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_interaction_events_fragrance_neo4j_id"),
        "user_interaction_events",
        ["fragrance_neo4j_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_interaction_events_created_at"),
        "user_interaction_events",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop user_interaction_events table."""
    op.drop_index(
        op.f("ix_user_interaction_events_created_at"),
        table_name="user_interaction_events",
    )
    op.drop_index(
        op.f("ix_user_interaction_events_fragrance_neo4j_id"),
        table_name="user_interaction_events",
    )
    op.drop_index(
        op.f("ix_user_interaction_events_user_id"),
        table_name="user_interaction_events",
    )
    op.drop_table("user_interaction_events")
