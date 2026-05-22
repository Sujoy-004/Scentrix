"""T1.10: Prefect workflow for weekly ETL pipeline.

Orchestrates the complete fragrance data pipeline:
1. Scrape Fragrantica (T1.4-T1.6)
2. Clean data (T1.8)
3. Ingest into Neo4j (T1.9)
4. Validate graph (T1.11)
5. Log results and metrics

Scheduled to run weekly on Sundays at 2:00 AM UTC.
"""

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from prefect import flow, task, get_run_logger

from app.services.graph import init_neo4j, close_neo4j
from ml.pipeline.clean import FragranceDataCleaner
from ml.pipeline.ingest import FragranceGraphIngestor
from ml.tests.test_graph import GraphValidator, summarize_validation_results


logger = logging.getLogger(__name__)


@task(retries=2, retry_delay_seconds=60)
def scrape_fragrances(days_back: int = 7) -> Optional[Path]:
    """Task: Scrape Fragrantica for new fragrances.

    Args:
        days_back: Only scrape fragrances updated in last N days

    Returns:
        Path to downloaded JSONL file
    """
    run_logger = get_run_logger()
    run_logger.info("Starting fragrance scraping task...")

    try:
        import json
        import subprocess
        from datetime import datetime

        # Run scraper via subprocess
        result = subprocess.run(
            ["python", "-m", "ml.scraper.run_scraper"],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )

        if result.returncode != 0:
            run_logger.error(f"Scraper failed: {result.stderr}")
            return None

        # Find latest raw data file
        today = datetime.utcnow().strftime("%Y-%m-%d")
        raw_path = Path(f"raw/fragrantica/{today}/fragrances.jsonl")

        if raw_path.exists():
            # Count items
            item_count = sum(1 for _ in raw_path.open())
            run_logger.info(f"Scraped {item_count} fragrances")
            return raw_path
        else:
            run_logger.error(f"Raw data file not found: {raw_path}")
            return None

    except subprocess.TimeoutExpired:
        run_logger.error("Scraper timeout (30 minutes)")
        return None
    except Exception as e:
        run_logger.error(f"Scraping failed: {e}")
        return None


@task(retries=1)
def clean_fragrances(raw_data_path: Optional[Path]) -> Optional[Path]:
    """Task: Clean and normalize fragrance data.

    Args:
        raw_data_path: Path to raw JSONL from scraper

    Returns:
        Path to cleaned JSON file
    """
    run_logger = get_run_logger()

    if not raw_data_path or not raw_data_path.exists():
        run_logger.warning("No raw data to clean")
        return None

    try:
        import json

        # Load raw JSONL
        fragrances = []
        with open(raw_data_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    fragrances.append(json.loads(line))

        run_logger.info(f"Loaded {len(fragrances)} raw fragrances")

        # Clean
        cleaner = FragranceDataCleaner()
        cleaned = cleaner.clean_fragrance_list(fragrances)
        stats = cleaner.report()

        run_logger.info(f"Cleaned {len(cleaned)} fragrances")
        run_logger.info(f"  - Duplicates removed: {stats['duplicates_removed']}")
        run_logger.info(f"  - Invalid: {stats['invalid_records']}")
        run_logger.info(f"  - Removal rate: {stats['removal_rate']:.1f}%")

        # Save cleaned data
        cleaned_path = raw_data_path.parent / "cleaned_fragrances.json"
        with open(cleaned_path, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, indent=2)

        run_logger.info(f"Saved cleaned data to {cleaned_path}")
        return cleaned_path

    except Exception as e:
        run_logger.error(f"Data cleaning failed: {e}")
        return None


@task(retries=2, retry_delay_seconds=30)
def ingest_to_neo4j(
    cleaned_data_path: Optional[Path],
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    neo4j_user: str = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password"),
) -> dict:
    """Task: Ingest cleaned fragrances into Neo4j.

    Args:
        cleaned_data_path: Path to cleaned JSON
        neo4j_uri: Neo4j connection string
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Statistics dict
    """
    run_logger = get_run_logger()

    if not cleaned_data_path or not cleaned_data_path.exists():
        run_logger.warning("No cleaned data to ingest")
        return {}

    try:
        import json

        # Load cleaned data
        with open(cleaned_data_path, "r", encoding="utf-8") as f:
            fragrances = json.load(f)

        # Initialize Neo4j and ingest
        client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        ingestor = FragranceGraphIngestor(client)

        run_logger.info(f"Ingesting {len(fragrances)} fragrances into Neo4j...")
        stats = ingestor.ingest_fragrances(fragrances)

        run_logger.info(f"✓ Ingestion complete")
        run_logger.info(f"  - Fragrances: {stats.get('fragrances_created', 0)}")
        run_logger.info(f"  - Notes: {stats.get('notes_created', 0)}")
        run_logger.info(f"  - Accords: {stats.get('accords_created', 0)}")
        run_logger.info(f"  - Relationships: {stats.get('relationships_created', 0)}")
        run_logger.info(f"  - Errors: {stats.get('errors', 0)}")

        close_neo4j()
        return stats

    except Exception as e:
        run_logger.error(f"Ingestion failed: {e}")
        return {}


@task
def validate_graph(
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    neo4j_user: str = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password"),
    validation_profile: str = os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "staging"),
    strict_validation: bool = os.getenv("SCENTSCAPE_VALIDATION_STRICT", "false").lower()
    in {"1", "true", "yes", "on"},
) -> dict:
    """Task: Validate graph integrity after ingestion.

    Args:
        neo4j_uri: Neo4j connection string
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Validation results dict
    """
    run_logger = get_run_logger()

    try:
        client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        validator = GraphValidator(
            client,
            profile=validation_profile,
            strict=strict_validation,
        )

        run_logger.info("Validating graph integrity...")
        results = validator.validate_all()
        summary = summarize_validation_results(results)

        passed = summary["passed_check_count"]
        total = summary["total_checks"]

        run_logger.info(f"✓ Validation: {passed}/{total} tests passed")
        run_logger.info(
            "  - Failed checks: %s, Query errors: %s",
            summary["failed_check_count"],
            summary["query_error_count"],
        )

        for test_name, test_result in results.items():
            status = "✓" if test_result.get("passed") else "✗"
            run_logger.info(f"  {status} {test_name}")

        close_neo4j()
        return {
            "profile": validation_profile,
            "strict": validator.strict,
            "results": results,
            "summary": summary,
        }

    except Exception as e:
        run_logger.error(f"Validation failed: {e}")
        return {}


@flow(
    name="Weekly Fragrance ETL",
    description="Weekly pipeline: scrape → clean → ingest → validate fragrances",
)
def weekly_fragrance_etl(
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    neo4j_user: str = os.getenv("NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")),
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password"),
    validation_profile: str = os.getenv("SCENTSCAPE_VALIDATION_PROFILE", "staging"),
    strict_validation: bool = os.getenv("SCENTSCAPE_VALIDATION_STRICT", "false").lower()
    in {"1", "true", "yes", "on"},
):
    """Main ETL workflow.

    Scheduled to run weekly on Sundays at 2:00 AM UTC.
    """
    run_logger = get_run_logger()

    run_logger.info("=" * 80)
    run_logger.info("STARTING WEEKLY FRAGRANCE ETL PIPELINE")
    run_logger.info(f"Timestamp: {datetime.utcnow().isoformat()}")
    run_logger.info("=" * 80)

    # Step 1: Scrape
    run_logger.info("\n[Step 1/4] Scraping Fragrantica...")
    raw_path = scrape_fragrances()
    if raw_path:
        run_logger.info(f"✓ Scraping completed")
    else:
        run_logger.warning("⚠ Scraping skipped or failed")

    # Step 2: Clean
    run_logger.info("\n[Step 2/4] Cleaning data...")
    cleaned_path = clean_fragrances(raw_path)
    if cleaned_path:
        run_logger.info(f"✓ Cleaning completed")
    else:
        run_logger.warning("⚠ Cleaning skipped or failed")
        return

    # Step 3: Ingest
    run_logger.info("\n[Step 3/4] Ingesting into Neo4j...")
    ingest_stats = ingest_to_neo4j(cleaned_path, neo4j_uri, neo4j_user, neo4j_password)
    if ingest_stats:
        run_logger.info(f"✓ Ingestion completed")
    else:
        run_logger.warning("⚠ Ingestion skipped or failed")
        return

    # Step 4: Validate
    run_logger.info("\n[Step 4/4] Validating graph...")
    validation_results = validate_graph(
        neo4j_uri,
        neo4j_user,
        neo4j_password,
        validation_profile,
        strict_validation,
    )
    if validation_results:
        summary = validation_results.get("summary", {})
        query_errors = summary.get("query_error_count", 0)
        failed_checks = summary.get("failed_check_count", 0)

        if query_errors > 0:
            raise RuntimeError(
                f"Validation query errors detected ({query_errors}). Blocking pipeline completion."
            )

        if strict_validation and failed_checks > 0:
            raise RuntimeError(
                f"Strict validation failed with {failed_checks} failed checks."
            )

        if failed_checks > 0:
            run_logger.warning(
                "⚠ Validation completed with warnings: %s failed checks (strict=%s)",
                failed_checks,
                strict_validation,
            )
        else:
            run_logger.info("✓ Validation completed")
    else:
        run_logger.warning("⚠ Validation failed")

    run_logger.info("\n" + "=" * 80)
    run_logger.info("WEEKLY ETL PIPELINE COMPLETED SUCCESSFULLY")
    run_logger.info("=" * 80)


# Schedule: Sundays at 2:00 AM UTC
# To enable: Uncomment the schedule parameter and configure Prefect deployment
# schedule = CronSchedule(cron="0 2 * * 0", timezone="UTC")


if __name__ == "__main__":
    # Run locally
    weekly_fragrance_etl()
