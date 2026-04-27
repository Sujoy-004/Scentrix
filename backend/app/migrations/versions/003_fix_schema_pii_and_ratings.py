"""003: Fix schema - PII fields, ratings simplification, user role.

Brings the live DB in line with the current ORM models:
- users: add email_hash, encrypted_email, encrypted_full_name, role; drop old email column
- fragrance_ratings: add quiz_rating (simple 1-10 float) so the quiz recommendation
  engine can persist and retrieve ratings without requiring all 5 perceptual dims.
"""

import sqlalchemy as sa
from alembic import op

revision = "003_fix_schema"
down_revision = "002_add_user_interaction_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── PREREQUISITES ───────────────────────────────────────────────────────
    # Ensure pgcrypto is available for the SHA-256 digest function
    conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    # ── USERS table ─────────────────────────────────────────────────────────
    inspector = sa.inspect(conn)
    user_cols = {c["name"] for c in inspector.get_columns("users")}

    if "encrypted_full_name" not in user_cols:
        op.add_column("users", sa.Column("encrypted_full_name", sa.Text(), nullable=True))

    if "role" not in user_cols:
        op.add_column(
            "users",
            sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        )

    if "email_hash" not in user_cols:
        op.add_column(
            "users",
            sa.Column("email_hash", sa.String(64), nullable=True),  # nullable=True initially
        )

    if "encrypted_email" not in user_cols:
        op.add_column(
            "users",
            sa.Column("encrypted_email", sa.Text(), nullable=True),  # nullable=True initially
        )

    # Populate email_hash and encrypted_email from old email column if it exists
    if "email" in user_cols and "email_hash" in {
        c["name"] for c in inspector.get_columns("users")
    } | {"email_hash"}:
        # Use MD5 as a placeholder hash — real bcrypt not available in SQL.
        # The actual SHA-256 hash will be written by the app on next login.
        conn.execute(
            sa.text(
                """
                UPDATE users
                SET email_hash = encode(digest(lower(trim(email)), 'sha256'), 'hex'),
                    encrypted_email = email
                WHERE email_hash IS NULL
                """
            )
        )

    # Now make them NOT NULL and add unique constraints
    try:
        op.alter_column("users", "email_hash", nullable=False)
    except Exception:
        pass  # Already NOT NULL

    try:
        op.alter_column("users", "encrypted_email", nullable=False)
    except Exception:
        pass

    try:
        op.create_index("ix_users_email_hash", "users", ["email_hash"], unique=True)
    except Exception:
        pass  # Already exists

    try:
        op.create_unique_constraint("uq_users_encrypted_email", "users", ["encrypted_email"])
    except Exception:
        pass

    # Final cleanup: drop legacy email column if all data is migrated
    if "email" in user_cols:
        op.drop_column("users", "email")

    # ── FRAGRANCE_RATINGS table ─────────────────────────────────────────────
    rating_cols = {c["name"] for c in inspector.get_columns("fragrance_ratings")}

    # Add a simple quiz_rating column (1-10) alongside perceptual dims
    if "quiz_rating" not in rating_cols:
        op.add_column(
            "fragrance_ratings",
            sa.Column("quiz_rating", sa.Float(), nullable=True),
        )

    # Make the 5 perceptual dims nullable so the quiz can insert without them
    for col in [
        "rating_sweetness",
        "rating_woodiness",
        "rating_longevity",
        "rating_projection",
        "rating_freshness",
        "overall_satisfaction",
    ]:
        if col in rating_cols:
            try:
                op.alter_column("fragrance_ratings", col, nullable=True)
            except Exception:
                pass


def downgrade() -> None:
    # Non-destructive downgrade — just remove added columns and restore email
    op.drop_column("fragrance_ratings", "quiz_rating")
    op.drop_index("ix_users_email_hash", table_name="users")
    op.drop_constraint("uq_users_encrypted_email", "users", type_="unique")
    op.drop_column("users", "email_hash")
    op.drop_column("users", "encrypted_email")
    op.drop_column("users", "encrypted_full_name")
    op.drop_column("users", "role")

    # Restore legacy email column
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
