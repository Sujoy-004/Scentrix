"""Add Supabase identity linkage to the users table."""

import sqlalchemy as sa
from alembic import op

revision = "004_add_supabase_identity"
down_revision = "003_fix_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {column["name"] for column in inspector.get_columns("users")}

    if "supabase_user_id" not in user_cols:
        op.add_column(
            "users",
            sa.Column("supabase_user_id", sa.String(length=128), nullable=True),
        )
        op.create_index(
            "ix_users_supabase_user_id",
            "users",
            ["supabase_user_id"],
            unique=True,
        )

    if "auth_provider" not in user_cols:
        op.add_column(
            "users",
            sa.Column(
                "auth_provider",
                sa.String(length=20),
                nullable=False,
                server_default="local",
            ),
        )

    if "hashed_password" in user_cols:
        try:
            op.alter_column("users", "hashed_password", nullable=True)
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.alter_column("users", "hashed_password", nullable=False)
    except Exception:
        pass

    if "auth_provider" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}:
        op.drop_column("users", "auth_provider")

    if "supabase_user_id" in {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}:
        op.drop_index("ix_users_supabase_user_id", table_name="users")
        op.drop_column("users", "supabase_user_id")
