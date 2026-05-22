"""T1.12: Integration test for complete Phase 1 data pipeline.

Tests the full end-to-end pipeline:
1. Load seed fragrances from JSON
2. Clean data (normalize, validate, deduplicate)
3. Ingest into Neo4j
4. Validate graph integrity

This test verifies all Phase 1 components work together correctly.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from datetime import UTC
from pathlib import Path
from typing import Optional

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.services.graph import init_neo4j, close_neo4j
from ml.pipeline.clean import FragranceDataCleaner
from ml.pipeline.ingest import FragranceGraphIngestor
from ml.tests.test_graph import GraphValidator, summarize_validation_results


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _write_integration_report(results: dict, artifact_dir: Path) -> Optional[Path]:
    """Persist integration output as JSON artifact for release audits."""
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = artifact_dir / f"integration_report_{timestamp}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        return output_path
    except Exception as e:
        logger.warning(f"Failed to write integration artifact: {e}")
        return None


async def run_integration_test(
    seed_data_path: Path = None,
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    neo4j_user: str = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password"),
    cleanup: bool = False,
    profile: str = os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "local"),
    strict: Optional[bool] = None,
    artifact_dir: Optional[Path] = None,
) -> dict:
    """Run complete integration test of data pipeline.

    Args:
        seed_data_path: Path to seed fragrances JSON. Defaults to ml/data/seed_fragrances.json
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        cleanup: If True, delete all nodes before test

    Returns:
        Dictionary with test results:
        {
            "overall_status": "passed" | "failed",
            "phases": {
                "cleanup": {"status": ..., "message": ...},
                "load": {"status": ..., "count": ...},
                "clean": {"status": ..., "input_count": ..., "output_count": ...},
                "ingest": {"status": ..., "stats": ...},
                "validate": {"status": ..., "results": {...}}
            }
        }
    """

    started_at = datetime.now(UTC)
    report_dir = artifact_dir or (Path(__file__).parent.parent / "logs" / "integration")

    results = {
        "overall_status": "failed",
        "phases": {},
        "validation_profile": profile,
        "strict_mode": None,
        "started_at_utc": started_at.isoformat() + "Z",
        "completed_at_utc": None,
        "duration_seconds": None,
        "artifact_path": None,
    }

    # Set default seed data path
    if seed_data_path is None:
        seed_data_path = Path(__file__).parent.parent / "data" / "fra_elite_5k.json"

    logger.info("=" * 80)
    logger.info("STARTING INTEGRATION TEST - Phase 1 Data Pipeline")
    logger.info("=" * 80)

    try:
        # Step 1: Initialize Neo4j connection
        logger.info("\n[1/5] Initializing Neo4j connection...")
        client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)

        try:
            if not client.verify_connection():
                raise RuntimeError("Neo4j connection verification returned False")
            logger.info("✓ Neo4j connection verified")
        except Exception as e:
            logger.error(f"✗ Failed to verify Neo4j connection: {e}")
            results["phases"]["connection"] = {
                "status": "failed",
                "error": str(e),
            }
            return results

        # Step 2: Optional cleanup
        if cleanup:
            logger.info("\n[1.5/5] Cleaning up existing data...")
            try:
                with client.tx() as tx:
                    tx.run("MATCH (n) DETACH DELETE n")
                logger.info("✓ Deleted all existing nodes")
                results["phases"]["cleanup"] = {"status": "passed"}
            except Exception as e:
                logger.warning(f"Note: Cleanup skipped ({e})")
                results["phases"]["cleanup"] = {
                    "status": "skipped",
                    "reason": str(e),
                }

        # Step 2: Load seed data
        logger.info(f"\n[2/5] Loading seed data from {seed_data_path}...")
        try:
            with open(seed_data_path, "r", encoding="utf-8") as f:
                seed_fragrances = json.load(f)

            if not isinstance(seed_fragrances, list):
                seed_fragrances = [seed_fragrances]

            logger.info(f"✓ Loaded {len(seed_fragrances)} fragrances from seed data")
            results["phases"]["load"] = {
                "status": "passed",
                "count": len(seed_fragrances),
            }
        except Exception as e:
            logger.error(f"✗ Failed to load seed data: {e}")
            results["phases"]["load"] = {
                "status": "failed",
                "error": str(e),
            }
            return results

        # Step 3: Clean data
        logger.info("\n[3/5] Cleaning fragrances...")
        try:
            cleaner = FragranceDataCleaner()
            cleaned_fragrances = cleaner.clean_fragrance_list(seed_fragrances)
            stats = cleaner.report()

            logger.info(f"✓ Cleaned {len(cleaned_fragrances)} fragrances")
            logger.info(f"  - Input: {stats['total_input']}")
            logger.info(f"  - Output: {stats['total_output']}")
            logger.info(f"  - Duplicates removed: {stats['duplicates_removed']}")
            logger.info(f"  - Invalid records: {stats['invalid_records']}")
            logger.info(f"  - Removal rate: {stats['removal_rate']:.1f}%")

            results["phases"]["clean"] = {
                "status": "passed",
                "input_count": stats["total_input"],
                "output_count": stats["total_output"],
                "stats": stats,
            }
        except Exception as e:
            logger.error(f"✗ Data cleaning failed: {e}")
            results["phases"]["clean"] = {
                "status": "failed",
                "error": str(e),
            }
            return results

        # Step 4: Ingest into Neo4j
        logger.info("\n[4/5] Ingesting fragrances into Neo4j...")
        try:
            ingestor = FragranceGraphIngestor(client)
            ingest_stats = ingestor.ingest_fragrances(cleaned_fragrances)

            logger.info(f"✓ Ingested fragrances into Neo4j")
            logger.info(
                f"  - Fragrances created: {ingest_stats.get('fragrances_created', 0)}"
            )
            logger.info(
                f"  - Fragrances updated: {ingest_stats.get('fragrances_updated', 0)}"
            )
            logger.info(f"  - Notes created: {ingest_stats.get('notes_created', 0)}")
            logger.info(
                f"  - Accords created: {ingest_stats.get('accords_created', 0)}"
            )
            logger.info(f"  - Brands created: {ingest_stats.get('brands_created', 0)}")
            logger.info(
                f"  - Relationships created: {ingest_stats.get('relationships_created', 0)}"
            )
            logger.info(f"  - Errors: {ingest_stats.get('errors', 0)}")

            results["phases"]["ingest"] = {
                "status": "passed",
                "stats": ingest_stats,
            }
        except Exception as e:
            logger.error(f"✗ Data ingestion failed: {e}")
            results["phases"]["ingest"] = {
                "status": "failed",
                "error": str(e),
            }
            return results

        # Step 5: Validate graph
        logger.info("\n[5/5] Validating graph integrity...")
        try:
            validator = GraphValidator(client, profile=profile, strict=strict)
            validation_results = validator.validate_all()
            summary = summarize_validation_results(validation_results)
            results["strict_mode"] = validator.strict

            # Log validation results
            passed = summary["passed_check_count"]
            total = summary["total_checks"]

            logger.info(f"✓ Validation complete: {passed}/{total} tests passed")

            for test_name, test_result in validation_results.items():
                status = "✓" if test_result.get("passed") else "✗"
                logger.info(f"  {status} {test_name}: {test_result.get('message', '')}")

            if summary["query_error_count"] > 0:
                validate_status = "failed"
            elif summary["failed_check_count"] == 0:
                validate_status = "passed"
            elif validator.strict:
                validate_status = "failed"
            else:
                validate_status = "warnings"

            results["phases"]["validate"] = {
                "status": validate_status,
                "passed": passed,
                "total": total,
                "results": validation_results,
                "summary": summary,
            }
        except Exception as e:
            logger.error(f"✗ Graph validation failed: {e}")
            results["phases"]["validate"] = {
                "status": "failed",
                "error": str(e),
            }
            return results

        # Determine overall status
        phase_statuses = [p.get("status") for p in results["phases"].values()]
        if any(s == "failed" for s in phase_statuses):
            results["overall_status"] = "failed"
        elif all(s in ["passed", "skipped"] for s in phase_statuses):
            results["overall_status"] = "passed"
        elif all(s in ["passed", "warnings", "skipped"] for s in phase_statuses):
            results["overall_status"] = "passed_with_warnings"
        else:
            results["overall_status"] = "failed"

        logger.info("\n" + "=" * 80)
        logger.info(f"INTEGRATION TEST RESULT: {results['overall_status'].upper()}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Unexpected error during integration test: {e}")
        results["overall_status"] = "failed"
        results["error"] = str(e)

    finally:
        # Close Neo4j connection
        if "client" in locals():
            close_neo4j()
            logger.info("Neo4j connection closed")

        completed_at = datetime.now(UTC)
        results["completed_at_utc"] = completed_at.isoformat() + "Z"
        results["duration_seconds"] = round(
            (completed_at - started_at).total_seconds(), 3
        )

        report_path = _write_integration_report(results, report_dir)
        if report_path:
            results["artifact_path"] = str(report_path)
            logger.info(f"Integration artifact saved: {report_path}")

    return results


def print_results(results: dict):
    """Pretty-print test results."""
    print("\n" + "=" * 80)
    print("INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"Overall Status: {results['overall_status'].upper()}")
    print("-" * 80)

    for phase_name, phase_result in results["phases"].items():
        status_symbol = "✓" if phase_result.get("status") == "passed" else "✗"
        print(
            f"{status_symbol} {phase_name.upper()}: {phase_result.get('status', 'unknown')}"
        )

        if "count" in phase_result:
            print(f"  - Count: {phase_result['count']}")
        if "input_count" in phase_result:
            print(
                f"  - Input: {phase_result['input_count']}, Output: {phase_result['output_count']}"
            )
        if "stats" in phase_result and isinstance(phase_result["stats"], dict):
            for stat_name, stat_value in phase_result["stats"].items():
                if stat_name not in ["total_input", "total_output"]:
                    print(f"  - {stat_name}: {stat_value}")
        if "error" in phase_result:
            print(f"  - Error: {phase_result['error']}")

    summary = results.get("phases", {}).get("validate", {}).get("summary")
    if summary:
        print("-" * 80)
        print("VALIDATION SUMMARY")
        print(f"  - Profile: {results.get('validation_profile')}")
        print(f"  - Strict mode: {results.get('strict_mode')}")
        print(
            f"  - Passed checks: {summary['passed_check_count']}/{summary['total_checks']}"
        )
        print(f"  - Failed checks: {summary['failed_check_count']}")
        print(f"  - Query errors: {summary['query_error_count']}")

    if results.get("artifact_path"):
        print(f"Artifact: {results['artifact_path']}")

    print("=" * 80)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run ML integration pipeline validation."
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
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument(
        "--profile",
        default=os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "local"),
        choices=["local", "staging", "production"],
    )
    parser.add_argument("--strict", dest="strict", action="store_true")
    parser.add_argument("--no-strict", dest="strict", action="store_false")
    parser.set_defaults(strict=None)
    parser.add_argument(
        "--artifact-dir",
        default=os.getenv("SCENTSCAPE_VALIDATION_ARTIFACT_DIR", ""),
        help="Optional directory for JSON integration artifacts.",
    )
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir) if args.artifact_dir else None

    # Run integration test
    results = asyncio.run(
        run_integration_test(
            neo4j_uri=args.neo4j_uri,
            neo4j_user=args.neo4j_user,
            neo4j_password=args.neo4j_password,
            cleanup=args.cleanup,
            profile=args.profile,
            strict=args.strict,
            artifact_dir=artifact_dir,
        )
    )

    # Print results
    print_results(results)

    # Exit with appropriate code
    exit_ok = results["overall_status"] == "passed" or (
        results["overall_status"] == "passed_with_warnings"
        and not results.get("strict_mode", False)
    )
    sys.exit(0 if exit_ok else 1)
