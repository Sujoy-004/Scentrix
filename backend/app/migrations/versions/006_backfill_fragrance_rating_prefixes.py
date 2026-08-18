"""006: Backfill legacy unprefixed fragrance_neo4j_id rows.

The catalog SSOT (ml/data/scentrix_master.json), the GraphSAGE node index
(ml/models/serving/v1/node_ids_jaccard.json) and the embedding index
(ml/data/embedding_index.json) all key fragrances as ``frag_<brand>_<name>_<year>``.
Older write paths stripped the ``frag_`` prefix before persisting, so legacy
rows in ``fragrance_ratings`` hold unprefixed ids (e.g. ``hermes_...``) that
never match the catalog — breaking personalized recommendations and quiz
summaries.  This migration prefixes those rows so stored ids match the
canonical format used everywhere else.
"""

import sqlalchemy as sa
from alembic import op

revision = "006_backfill_fragrance_rating_prefixes"
down_revision = "1802a3ca3620"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "fragrance_ratings" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("fragrance_ratings")}
    if "fragrance_neo4j_id" not in cols:
        return

    conn.execute(
        sa.text(
            r"""
            UPDATE fragrance_ratings
            SET fragrance_neo4j_id = 'frag_' || fragrance_neo4j_id
            WHERE fragrance_neo4j_id IS NOT NULL
              AND fragrance_neo4j_id NOT LIKE 'frag\_%' ESCAPE '\'
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "fragrance_ratings" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("fragrance_ratings")}
    if "fragrance_neo4j_id" not in cols:
        return

    # Best-effort inverse: strip the frag_ prefix back off.  Guard against
    # frag_syn_* synthetic ids, where substring(from 6) would corrupt
    # frag_syn_500 → syn_500 (stripping frag_ from an already-canonical id).
    conn.execute(
        sa.text(
            r"""
            UPDATE fragrance_ratings
            SET fragrance_neo4j_id = substring(fragrance_neo4j_id from 6)
            WHERE fragrance_neo4j_id LIKE 'frag\_%' ESCAPE '\'
              AND fragrance_neo4j_id NOT LIKE 'frag_syn\_%' ESCAPE '\'
            """
        )
    )
