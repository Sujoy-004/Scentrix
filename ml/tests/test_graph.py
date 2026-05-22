"""Graph validation tests for Scentrix.

Validates Neo4j graph integrity and data quality.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any

from app.services.graph import Neo4jClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationProfile:
    """Threshold bundle for a validation environment."""

    name: str
    min_fragrances: int
    min_notes: int
    min_accords: int
    min_brands: int
    min_edges_per_frag: int
    min_name_pct: float
    min_desc_pct: float


PROFILE_PRESETS: dict[str, ValidationProfile] = {
    "local": ValidationProfile(
        name="local",
        min_fragrances=50,
        min_notes=90,
        min_accords=20,
        min_brands=20,
        min_edges_per_frag=3,
        min_name_pct=95.0,
        min_desc_pct=90.0,
    ),
    "staging": ValidationProfile(
        name="staging",
        min_fragrances=500,
        min_notes=200,
        min_accords=60,
        min_brands=50,
        min_edges_per_frag=4,
        min_name_pct=98.0,
        min_desc_pct=95.0,
    ),
    "production": ValidationProfile(
        name="production",
        min_fragrances=1000,
        min_notes=300,
        min_accords=80,
        min_brands=80,
        min_edges_per_frag=5,
        min_name_pct=99.0,
        min_desc_pct=97.0,
    ),
}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def summarize_validation_results(results: dict[str, Any]) -> dict[str, Any]:
    """Summarize validation results into pass/fail/error buckets."""
    total_checks = len(results)
    query_errors = [k for k, v in results.items() if v.get("error")]
    failed_checks = [k for k, v in results.items() if not v.get("passed")]
    warning_checks = [
        k for k, v in results.items() if not v.get("passed") and not v.get("error")
    ]
    passed_checks = [k for k, v in results.items() if v.get("passed")]

    return {
        "total_checks": total_checks,
        "passed_check_count": len(passed_checks),
        "failed_check_count": len(failed_checks),
        "warning_check_count": len(warning_checks),
        "query_error_count": len(query_errors),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "warning_checks": warning_checks,
        "query_error_checks": query_errors,
    }


class GraphValidator:
    """Validates fragrance knowledge graph integrity."""

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        profile: str | None = None,
        strict: bool | None = None,
    ):
        """Initialize validator.

        Args:
            neo4j_client: Neo4j client instance
            profile: Validation profile name (local/staging/production)
            strict: If True, treat any failed check as release-blocking
        """
        self.neo4j = neo4j_client
        self.results = {}

        selected_profile = (
            (profile or os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "local"))
            .strip()
            .lower()
        )
        if selected_profile not in PROFILE_PRESETS:
            raise ValueError(
                f"Unknown validation profile '{selected_profile}'. "
                f"Expected one of: {', '.join(PROFILE_PRESETS.keys())}"
            )

        self.profile = PROFILE_PRESETS[selected_profile]
        if strict is None:
            self.strict = _env_bool(
                "SCENTSCAPE_VALIDATION_STRICT",
                default=(self.profile.name == "production"),
            )
        else:
            self.strict = strict

    def validate_all(self) -> dict[str, Any]:
        """Run all validation checks.

        Returns:
            Results dict with validation status
        """
        logger.info(
            "Starting graph validation (profile=%s, strict=%s)...",
            self.profile.name,
            self.strict,
        )

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

        summary = summarize_validation_results(self.results)
        logger.info(
            "Validation summary: %s/%s passed, %s failed, %s query errors",
            summary["passed_check_count"],
            summary["total_checks"],
            summary["failed_check_count"],
            summary["query_error_count"],
        )

        return self.results

    def validate_fragrance_count(self) -> dict[str, Any]:
        """Validate minimum fragrance count.

        Returns:
            Result dict
        """
        query = "MATCH (f:Fragrance) RETURN COUNT(f) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.profile.min_fragrances
        return {
            "passed": passed,
            "count": count,
            "minimum": self.profile.min_fragrances,
            "message": f"Found {count} fragrances (minimum: {self.profile.min_fragrances})",
        }

    def validate_note_count(self) -> dict[str, Any]:
        """Validate minimum note count.

        Returns:
            Result dict
        """
        query = "MATCH (n:Note) RETURN COUNT(n) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.profile.min_notes
        return {
            "passed": passed,
            "count": count,
            "minimum": self.profile.min_notes,
            "message": f"Found {count} notes (minimum: {self.profile.min_notes})",
        }

    def validate_accord_count(self) -> dict[str, Any]:
        """Validate minimum accord count.

        Returns:
            Result dict
        """
        query = "MATCH (a:Accord) RETURN COUNT(a) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.profile.min_accords
        return {
            "passed": passed,
            "count": count,
            "minimum": self.profile.min_accords,
            "message": f"Found {count} accords (minimum: {self.profile.min_accords})",
        }

    def validate_brand_count(self) -> dict[str, Any]:
        """Validate minimum brand count.

        Returns:
            Result dict
        """
        query = "MATCH (b:Brand) RETURN COUNT(b) as count"
        result = self.neo4j.execute_query(query)
        count = result[0]["count"] if result else 0

        passed = count >= self.profile.min_brands
        return {
            "passed": passed,
            "count": count,
            "minimum": self.profile.min_brands,
            "message": f"Found {count} brands (minimum: {self.profile.min_brands})",
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

        passed = min_rels >= self.profile.min_edges_per_frag
        return {
            "passed": passed,
            "avg_relationships": round(avg_rels, 2),
            "min_relationships": min_rels,
            "max_relationships": stats.get("max_rels", 0),
            "minimum": self.profile.min_edges_per_frag,
            "message": f"Average {avg_rels:.1f} relationships per fragrance "
            f"(minimum: {self.profile.min_edges_per_frag})",
        }

    def validate_orphaned_notes(self) -> dict[str, Any]:
        """Check for orphaned notes (not connected to any fragrance).

        Returns:
            Result dict
        """
        query = """
        MATCH (n:Note)
        WHERE NOT EXISTS { MATCH (:Fragrance)-[]->(n) }
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
        WHERE NOT EXISTS { MATCH (:Fragrance)-[]->(a) }
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

        passed = (
            name_pct >= self.profile.min_name_pct
            and desc_pct >= self.profile.min_desc_pct
        )
        return {
            "passed": passed,
            "total_fragrances": total,
            "with_names_pct": round(name_pct, 1),
            "with_descriptions_pct": round(desc_pct, 1),
            "minimum_name_pct": self.profile.min_name_pct,
            "minimum_description_pct": self.profile.min_desc_pct,
            "message": (
                f"{name_pct:.0f}% have names (min {self.profile.min_name_pct:.0f}%), "
                f"{desc_pct:.0f}% have descriptions (min {self.profile.min_desc_pct:.0f}%)"
            ),
        }


def validate_graph(
    neo4j_client: Neo4jClient,
    profile: str | None = None,
    strict: bool | None = None,
) -> dict[str, Any]:
    """Standalone function to validate graph.

    Args:
        neo4j_client: Neo4j client instance

    Returns:
        Validation results dict
    """
    validator = GraphValidator(neo4j_client, profile=profile, strict=strict)
    return validator.validate_all()


if __name__ == "__main__":
    import argparse
    import os
    import sys
    import json
    from app.services.graph import init_neo4j

    parser = argparse.ArgumentParser(
        description="Validate Scentrix Neo4j graph quality."
    )
    parser.add_argument(
        "neo4j_uri",
        nargs="?",
        default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    )
    parser.add_argument(
        "neo4j_user",
        nargs="?",
        default=os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
    )
    parser.add_argument(
        "neo4j_password",
        nargs="?",
        default=os.getenv("NEO4J_PASSWORD", "password"),
    )
    parser.add_argument(
        "--profile",
        default=os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "local"),
        choices=list(PROFILE_PRESETS.keys()),
        help="Validation profile for threshold selection.",
    )
    parser.add_argument("--strict", dest="strict", action="store_true")
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    parser.set_defaults(strict=None)
    args = parser.parse_args()

    client = init_neo4j(args.neo4j_uri, args.neo4j_user, args.neo4j_password)
    results = validate_graph(client, profile=args.profile, strict=args.strict)
    summary = summarize_validation_results(results)

    print(json.dumps({"results": results, "summary": summary}, indent=2))
    sys.exit(0 if summary["failed_check_count"] == 0 else 1)
