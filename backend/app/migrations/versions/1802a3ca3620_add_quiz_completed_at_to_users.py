"""Add quiz_completed_at to users."""

import sqlalchemy as sa
from alembic import op

revision = "1802a3ca3620"
down_revision = "005_add_user_preferences_json"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {column["name"] for column in inspector.get_columns("users")}

    if "quiz_completed_at" not in user_cols:
        op.add_column(
            "users",
            sa.Column(
                "quiz_completed_at",
                sa.DateTime(),
                nullable=True,
                comment="When the user completed (finalized) the neural discovery quiz",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    user_cols = {column["name"] for column in inspector.get_columns("users")}

    if "quiz_completed_at" in user_cols:
        op.drop_column("users", "quiz_completed_at")
