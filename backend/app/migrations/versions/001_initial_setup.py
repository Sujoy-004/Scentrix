"""Initial database migration - create user and ratings tables."""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001_initial_setup"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("gdpr_deletion_requested_at", sa.DateTime(), nullable=True),
        sa.Column("opt_in_training", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)

    # Create fragrance_ratings table
    op.create_table(
        "fragrance_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fragrance_neo4j_id", sa.String(length=100), nullable=False),
        sa.Column("rating_sweetness", sa.Float(), nullable=False),
        sa.Column("rating_woodiness", sa.Float(), nullable=False),
        sa.Column("rating_longevity", sa.Float(), nullable=False),
        sa.Column("rating_projection", sa.Float(), nullable=False),
        sa.Column("rating_freshness", sa.Float(), nullable=False),
        sa.Column("overall_satisfaction", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fragrance_ratings_user_id"),
        "fragrance_ratings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fragrance_ratings_fragrance_neo4j_id"),
        "fragrance_ratings",
        ["fragrance_neo4j_id"],
        unique=False,
    )

    # Create saved_fragrances table
    op.create_table(
        "saved_fragrances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fragrance_neo4j_id", sa.String(length=100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_saved_fragrances_user_id"),
        "saved_fragrances",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_saved_fragrances_fragrance_neo4j_id"),
        "saved_fragrances",
        ["fragrance_neo4j_id"],
        unique=False,
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_refresh_tokens_user_id"),
        "refresh_tokens",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(
        op.f("ix_saved_fragrances_fragrance_neo4j_id"),
        table_name="saved_fragrances",
    )
    op.drop_index(op.f("ix_saved_fragrances_user_id"), table_name="saved_fragrances")
    op.drop_table("saved_fragrances")
    op.drop_index(
        op.f("ix_fragrance_ratings_fragrance_neo4j_id"),
        table_name="fragrance_ratings",
    )
    op.drop_index(
        op.f("ix_fragrance_ratings_user_id"), table_name="fragrance_ratings"
    )
    op.drop_table("fragrance_ratings")
    op.drop_index(op.f("ix_users_is_active"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
