"""Graph validation tests for ScentScape.

Validates Neo4j graph integrity and data quality.
"""

import logging
from typing import Any

from ml.graph import Neo4jClient

logger = logging.getLogger(__name__)


class GraphValidator:
    """Validates fragrance knowledge graph integrity."""

    # Minimum required counts for MVP
    MIN_FRAGRANCES = 100
    MIN_NOTES = 150
    MIN_ACCORDS = 40
    MIN_BRANDS = 30
    MIN_EDGES_PER_FRAG = 3  # Relationships per fragrance

    def __init__(self, neo4j_client: Neo4jClient):
        """Initialize validator.

        Args:
            neo4j_client: Neo4j client instance
        """
        self.neo4j = neo4j_client
        self.results = {}

    def validate_all(self) -> dict[str, Any]:
        """Run all validation checks.

        Returns:
            Results dict with validation status
        """
        logger.info("Starting graph validation...")

        tests = [
            ("fragrance_count", self.validate_fragrance_count),
            ("note_count", self.validate_note_count),
            ("accord_count", self.validate_accord_count),
            ("brand_count", self.validate_brand_count),
            ("fragrance_relationships", self.validate_fragrance_relationships),
            ("orphaned_notes", self.validate_orphaned_notes),
            ("orphaned_accords", self.validate_orphaned_accords),
            ("note_categories", self.validate_note_categories),
            ("fragrance_note_coverage", self.validate_fragrance_note_coverage),
            ("data_quality", self.validate_data_quality),
        ]

        for test_name, test_func in tests:
            try:
                result = test_func()
                self.results[test_name] = result
                status = "PASS" if result["passed"] else "FAIL"
                logger.info(f"{test_name}: {status}")
            except Exception as e:
                logger.error(f"{test_name}: ERROR - {e}")
                self.results[test_name] = {
                    "passed": False,
                    "error": str(e),
                }

        return self.results

    def validate_fragrance_count(self) -> dict[str, Any]:
        """Validate minimum fragrance count.

        Returns:
            Result dict
        """
        query = "MATCH (f:Fragrance) RETURN COUNT(f) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.MIN_FRAGRANCES
        return {
            "passed": passed,
            "count": count,
            "minimum": self.MIN_FRAGRANCES,
            "message": f"Found {count} fragrances (minimum: {self.MIN_FRAGRANCES})",
        }

    def validate_note_count(self) -> dict[str, Any]:
        """Validate minimum note count.

        Returns:
            Result dict
        """
        query = "MATCH (n:Note) RETURN COUNT(n) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.MIN_NOTES
        return {
            "passed": passed,
            "count": count,
            "minimum": self.MIN_NOTES,
            "message": f"Found {count} notes (minimum: {self.MIN_NOTES})",
        }

    def validate_accord_count(self) -> dict[str, Any]:
        """Validate minimum accord count.

        Returns:
            Result dict
        """
        query = "MATCH (a:Accord) RETURN COUNT(a) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.MIN_ACCORDS
        return {
            "passed": passed,
            "count": count,
            "minimum": self.MIN_ACCORDS,
            "message": f"Found {count} accords (minimum: {self.MIN_ACCORDS})",
        }

    def validate_brand_count(self) -> dict[str, Any]:
        """Validate minimum brand count.

        Returns:
            Result dict
        """
        query = "MATCH (b:Brand) RETURN COUNT(b) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.MIN_BRANDS
        return {
            "passed": passed,
            "count": count,
            "minimum": self.MIN_BRANDS,
            "message": f"Found {count} brands (minimum: {self.MIN_BRANDS})",
        }

    def validate_fragrance_relationships(self) -> dict[str, Any]:
        """Validate fragrances have minimum relationships.

        Returns:
            Result dict
        """
        query = """
        MATCH (f:Fragrance)
        WITH f, size([(f)-[]-() | 1]) as rel_count
        RETURN avg(rel_count) as avg_rels,
               min(rel_count) as min_rels,
               max(rel_count) as max_rels
        """
        result = self.neo4j.execute_query(query)
        stats = result[0] if result else {}

        avg_rels = stats.get("avg_rels", 0)
        min_rels = stats.get("min_rels", 0)

        passed = min_rels >= self.MIN_EDGES_PER_FRAG
        return {
            "passed": passed,
            "avg_relationships": round(avg_rels, 2),
            "min_relationships": min_rels,
            "max_relationships": stats.get("max_rels", 0),
            "minimum": self.MIN_EDGES_PER_FRAG,
            "message": f"Average {avg_rels:.1f} relationships per fragrance "
                       f"(minimum: {self.MIN_EDGES_PER_FRAG})",
        }

    def validate_orphaned_notes(self) -> dict[str, Any]:
        """Check for orphaned notes (not connected to any fragrance).

        Returns:
            Result dict
        """
        query = """
        MATCH (n:Note)
        WHERE NOT (f:Fragrance)-[]->(n)
        RETURN COUNT(n) as orphaned_count
        """
        result = self.neo4j.execute_query(query)
        count = result[0]["orphaned_count"] if result else 0

        passed = count == 0
        return {
            "passed": passed,
            "orphaned_count": count,
            "message": f"Found {count} orphaned notes",
        }

    def validate_orphaned_accords(self) -> dict[str, Any]:
        """Check for orphaned accords.

        Returns:
            Result dict
        """
        query = """
        MATCH (a:Accord)
        WHERE NOT (f:Fragrance)-[]->(a)
        RETURN COUNT(a) as orphaned_count
        """
        result = self.neo4j.execute_query(query)
        count = result[0]["orphaned_count"] if result else 0

        passed = count == 0
        return {
            "passed": passed,
            "orphaned_count": count,
            "message": f"Found {count} orphaned accords",
        }

    def validate_note_categories(self) -> dict[str, Any]:
        """Validate note categories are valid.

        Returns:
            Result dict
        """
        query = """
        MATCH (n:Note)
        WHERE NOT n.category IN ['top', 'middle', 'base']
        RETURN COUNT(n) as invalid_count
        """
        result = self.neo4j.execute_query(query)
        count = result[0]["invalid_count"] if result else 0

        passed = count == 0
        return {
            "passed": passed,
            "invalid_categories": count,
            "message": f"Found {count} notes with invalid categories",
        }

    def validate_fragrance_note_coverage(self) -> dict[str, Any]:
        """Validate all fragrances have notes in all categories.

        Returns:
            Result dict
        """
        query = """
        MATCH (f:Fragrance)
        WITH f,
             size([(f)-[:HAS_TOP_NOTE]->() | 1]) as top_count,
             size([(f)-[:HAS_MIDDLE_NOTE]->() | 1]) as mid_count,
             size([(f)-[:HAS_BASE_NOTE]->() | 1]) as base_count
        WHERE top_count = 0 OR mid_count = 0 OR base_count = 0
        RETURN COUNT(f) as incomplete_count
        """
        result = self.neo4j.execute_query(query)
        count = result[0]["incomplete_count"] if result else 0

        passed = count == 0
        return {
            "passed": passed,
            "incomplete_fragrances": count,
            "message": f"Found {count} fragrances missing notes in one category",
        }

    def validate_data_quality(self) -> dict[str, Any]:
        """Check overall data quality metrics.

        Returns:
            Result dict
        """
        query = """
        MATCH (f:Fragrance)
        WITH f,
             (f.name IS NOT NULL AND f.name <> '') as has_name,
             (f.description IS NOT NULL AND f.description <> '') as has_desc
        RETURN COUNT(f) as total,
               COUNT(CASE WHEN has_name THEN 1 END) as with_name,
               COUNT(CASE WHEN has_desc THEN 1 END) as with_desc
        """
        result = self.neo4j.execute_query(query)
        stats = result[0] if result else {}

        total = stats.get("total", 0)
        with_name = stats.get("with_name", 0)
        with_desc = stats.get("with_desc", 0)

        name_pct = (with_name / total * 100) if total > 0 else 0
        desc_pct = (with_desc / total * 100) if total > 0 else 0

        passed = name_pct >= 95 and desc_pct >= 90
        return {
            "passed": passed,
            "total_fragrances": total,
            "with_names_pct": round(name_pct, 1),
            "with_descriptions_pct": round(desc_pct, 1),
            "message": f"{name_pct:.0f}% have names, {desc_pct:.0f}% have descriptions",
        }


def validate_graph(neo4j_client: Neo4jClient) -> dict[str, Any]:
    """Standalone function to validate graph.

    Args:
        neo4j_client: Neo4j client instance

    Returns:
        Validation results dict
    """
    validator = GraphValidator(neo4j_client)
    return validator.validate_all()


if __name__ == "__main__":
    import sys
    import json
    from ml.graph import init_neo4j

    neo4j_uri = sys.argv[1] if len(sys.argv) > 1 else "neo4j://localhost:7687"
    neo4j_user = sys.argv[2] if len(sys.argv) > 2 else "neo4j"
    neo4j_password = sys.argv[3] if len(sys.argv) > 3 else "password"

    client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
    results = validate_graph(client)
    print(json.dumps(results, indent=2))
