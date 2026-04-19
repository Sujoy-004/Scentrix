"""Add JSON preferences storage to users."""

import sqlalchemy as sa
from alembic import op

revision = "005_add_user_preferences_json"
down_revision = "004_add_supabase_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {column["name"] for column in inspector.get_columns("users")}

    if "preferences_json" not in user_cols:
        op.add_column(
            "users",
            sa.Column("preferences_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {column["name"] for column in inspector.get_columns("users")}

    if "preferences_json" in user_cols:
        op.drop_column("users", "preferences_json")
