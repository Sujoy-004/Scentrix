"""Prefect ETL Pipeline Documentation

T1.10: Weekly Fragrance Data Pipeline Orchestration

This document describes the Prefect workflow that automates the complete
fragrance data pipeline from web scraping through Neo4j validation.

## Overview

The `ml/flows/weekly_refresh.py` module contains the `weekly_fragrance_etl` flow
that orchestrates:

1. **Scrape** — Fetch fresh fragrance data from Fragrantica
2. **Clean** — Normalize and validate fragrance data
3. **Ingest** — Load cleaned data into Neo4j knowledge graph
4. **Validate** — Ensure data quality and graph integrity

## Quick Start

### Install Prefect
```bash
pip install prefect>=2.14.0
```

### Run Locally (One-Time)
```bash
cd "path/to/ScentScape"
python ml/flows/weekly_refresh.py
```

Output:
```
===============================================================================
STARTING WEEKLY FRAGRANCE ETL PIPELINE
================================================================================

[Step 1/4] Scraping Fragrantica...
✓ Scraping completed
[Step 2/4] Cleaning data...
✓ Cleaning completed
[Step 3/4] Ingesting into Neo4j...
✓ Ingestion completed
[Step 4/4] Validating graph...
✓ Validation completed

================================================================================
WEEKLY ETL PIPELINE COMPLETED SUCCESSFULLY
================================================================================
```

### Deploy to Prefect Cloud (Scheduled)

1. **Create Prefect account** (free): https://cloud.prefect.io

2. **Authenticate:**
   ```bash
   prefect cloud login
   # Copy API key from: https://app.prefect.cloud/account/api-keys
   ```

3. **Deploy flow:**
   ```bash
   prefect deploy --name weekly-etl-deployment ml/flows/weekly_refresh.py:weekly_fragrance_etl \
     --schedule "0 2 * * 0"  # Sundays, 2:00 AM UTC
   ```

4. **Monitor in Prefect Cloud:** https://app.prefect.cloud/flows

## Pipeline Architecture

```
weekly_fragrance_etl (main flow)
    │
    ├─ [Task] scrape_fragrances
    │   └─ Returns: Path to raw JSONL file
    │       └─ raw/fragrantica/YYYY-MM-DD/fragrances.jsonl
    │
    ├─ [Task] clean_fragrances
    │   └─ Input: Raw JSONL
    │   └─ Output: Cleaned JSON
    │   └─ Operations: normalize, deduplicate, validate
    │
    ├─ [Task] ingest_to_neo4j
    │   └─ Input: Cleaned JSON
    │   └─ Operations: MERGE nodes, CREATE relationships
    │   └─ Output: Statistics dict
    │
    └─ [Task] validate_graph
        └─ Runs 10 validation checks
        └─ Returns: Pass/fail for each check
```

## Task Details

### Task 1: scrape_fragrances()
**Purpose:** Fetch fragrance data from Fragrantica

**Configuration:**
- Retries: 2 (with 60-second backoff)
- Timeout: 30 minutes
- Output: Path to raw JSONL file

**Responsible for:**
- Starting the Scrapy spider (T1.4-T1.6)
- Applying rate limiting (1 req/sec, 0.5-2s random delay)
- Rotating user agents
- Respecting robots.txt
- Uploading to Cloudflare R2 (or local fallback)

**Error handling:**
- Timeout → Logged, returns None
- Subprocess error → Logged, returns None
- File not found → Logged, returns None

### Task 2: clean_fragrances(raw_data_path)
**Purpose:** Normalize and validate fragrance data

**Configuration:**
- Retries: 1
- Input: Path to raw JSONL
- Output: Path to cleaned JSON

**Responsible for:**
- Loading raw JSONL (items come from scraper)
- Normalizing note names (90+ mappings)
- Deduplicating by (name, brand)
- Validating required fields
- Capping descriptions to 500 chars
- Limiting notes to 5 per category
- Limiting accords to 5 per fragrance

**Statistics tracked:**
- total_input: All items from scraper
- total_output: Valid items after cleaning
- duplicates_removed: Removed via deduplication
- invalid_records: Failed validation
- removal_rate: Percentage of items removed

### Task 3: ingest_to_neo4j(cleaned_data_path, neo4j_uri, ...)
**Purpose:** Load cleaned data into Neo4j

**Configuration:**
- Retries: 2 (with 30-second backoff)
- Input: Path to cleaned JSON
- Parameters: Neo4j URI, user, password
- Output: Statistics dict

**Responsible for:**
- Creating Brand nodes
- Creating/updating Fragrance nodes
- Creating Note nodes with HAS_*_NOTE relationships
- Creating Accord nodes with BELONGS_TO_ACCORD relationships
- Linking fragrances to brands with MADE_BY relationships

**Statistics returned:**
- fragrances_created: New fragrance nodes
- fragrances_updated: Updated existing fragrances
- notes_created: New note nodes
- accords_created: New accord nodes
- brands_created: New brand nodes
- relationships_created: Total edge count
- errors: Count of ingestion errors

### Task 4: validate_graph(neo4j_uri, ...)
**Purpose:** Verify data quality and graph integrity

**Configuration:**
- No retries (validation is quick)
- Parameters: Neo4j URI, user, password
- Output: Results dict with pass/fail for each test

**Validations run:** (10 total checks)
1. Fragrance count ≥ 100
2. Note count ≥ 150
3. Accord count ≥ 40
4. Brand count ≥ 30
5. Fragrance relationships ≥ 3 per fragrance
6. Orphaned notes = 0
7. Orphaned accords = 0
8. All notes have category (top/middle/base)
9. All fragrances have notes in all 3 categories
10. Data quality: ≥95% have names, ≥90% have descriptions

## Environment Variables

Set these for the pipeline:

```bash
# Neo4j
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Cloudflare R2 (for scraper)
CLOUDFLARE_R2_ACCOUNT_ID=your-account-id
CLOUDFLARE_R2_ACCESS_KEY_ID=your-access-key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-secret
```

Or pass as parameters to the flow:
```python
weekly_fragrance_etl(
    neo4j_uri="neo4j://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="password"
)
```

## Scheduling Options

### Option 1: Prefect Cloud Deployment (Recommended)
Deploy with schedule parameter:
```bash
prefect deploy --schedule "0 2 * * 0"
```
Runs every Sunday at 2:00 AM UTC.

### Option 2: APScheduler (Local)
```python
from apscheduler.schedulers.background import BackgroundScheduler
from ml.flows.weekly_refresh import weekly_fragrance_etl

scheduler = BackgroundScheduler()
scheduler.add_job(weekly_fragrance_etl, 'cron', day_of_week=6, hour=2, minute=0)
scheduler.start()
```

### Option 3: Cron Job (Linux/Mac)
```bash
# Every Sunday at 2:00 AM UTC
0 2 * * 0 cd /path/to/ScentScape && python ml/flows/weekly_refresh.py
```

## Monitoring & Logging

### View Logs Locally
```bash
python -c "
import logging
from ml.flows.weekly_refresh import weekly_fragrance_etl

logging.basicConfig(level=logging.INFO)
weekly_fragrance_etl()
"
```

### View Logs in Prefect Cloud
1. Navigate to Flow Runs: https://app.prefect.cloud/flows
2. Click on "weekly_fragrance_etl"
3. View logs in real-time as the flow executes

### Key Metrics
- **Execution time:** ~5-10 minutes (depends on Fragrantica size)
- **Success rate:** Target 100% (retries handle transient failures)
- **Data volume:** Variable (depends on new fragrances each week)

## Error Handling & Retries

| Task | Retries | Backoff | Timeout |
|------|---------|---------|---------|
| scrape_fragrances | 2 | 60s | 30m |
| clean_fragrances | 1 | n/a | n/a |
| ingest_to_neo4j | 2 | 30s | n/a |
| validate_graph | 0 | n/a | n/a |

If a task fails after retries:
- Subsequent tasks are skipped
- Error is logged with details
- Flow completes with status "FAILED"
- Alert is sent (if Prefect Cloud configured)

## Integration with Downstream Systems

After `validate_graph` passes, the fragrance graph is ready for:
- ML model training (GraphSAGE)
- User recommendation generation
- Similarity searches
- Personalization via BPR

If validation fails:
- Graph is not updated
- Previous version remains active
- Error is logged for investigation

## Customization

### Run Scraper Only
```python
from ml.flows.weekly_refresh import scrape_fragrances
raw_path = scrape_fragrances()
```

### Clean Offline Data
```python
from ml.flows.weekly_refresh import clean_fragrances
cleaned_path = clean_fragrances(Path("raw_data.jsonl"))
```

### Custom Neo4j Parameters
```python
from ml.flows.weekly_refresh import weekly_fragrance_etl

weekly_fragrance_etl(
    neo4j_uri="neo4j+s://auradb.example.com:7687",
    neo4j_user="neo4j",
    neo4j_password="secure-password"
)
```

## Troubleshooting

### Task: scrape_fragrances fails
- **Check:** Is Fragrantica accessible? (curl https://www.fragrantica.com)
- **Check:** Robot.txt blocking our UA? (Look at logs for 403 errors)
- **Solution:** Increase random delays, try different user agent in middleware.py

### Task: clean_fragrances produces no output
- **Check:** Raw JSONL format correct? (Each line should be valid JSON)
- **Check:** Strict validation failing? (Run with strict_mode=False)
- **Solution:** Inspect raw file, check cleaner logs for validation errors

### Task: ingest_to_neo4j fails
- **Check:** Neo4j is running? (neo4j status)
- **Check:** Credentials correct? (neo4j://user:pass@host:7687)
- **Check:** Graph quota exceeded? (Aura DB limits ~50k nodes free tier)
- **Solution:** Clear old data (MATCH (n) DETACH DELETE n) or upgrade to paid tier

### Task: validate_graph fails some checks
- **Common:** Fragrance count < 100 (normal if small scrape)
- **Action:** Check which tests fail, review stats in logs
- **Escalate:** If orphaned nodes found, investigate ingestion

## Next Steps

After Phase 1 completion (T1.13), this workflow will:
1. Execute automatically every Sunday
2. Feed fresh fragrance data to Phase 3 ML pipeline
3. Support user personalization with up-to-date graph
4. Enable continuous model retraining (weekly batch job)

## Files

- `ml/flows/weekly_refresh.py` — Prefect workflow definition
- `ml/flows/__init__.py` — Module initialization
- `ml/scraper/` — Scrapy spider (T1.4-T1.6)
- `ml/pipeline/clean.py` — Data cleaning (T1.8)
- `ml/pipeline/ingest.py` — Neo4j ingestion (T1.9)
- `ml/tests/test_graph.py` — Validation tests (T1.11)
"""
