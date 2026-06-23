"""Scentrix Fragrantica Web Scraper

Scrapy-based web scraper for extracting fragrance data from Fragrantica.
Implements responsible crawling with rate limiting and user agent rotation.

## Features

- **Respectful Crawling:** Obeys robots.txt, uses 1 req/sec with random 0.5-2s delays
- **User Agent Rotation:** Rotates through 6 common user agents to avoid detection
- **Structured Data:** Extracts name, brand, year, concentration, gender, notes, accords, reviews
- **Cloud Storage:** Uploads raw JSONL to Cloudflare R2 (falls back to local storage)
- **Error Handling:** Comprehensive logging and retry logic
- **Pagination:** Automatically follows pagination links

## Quick Start

### 1. Install Dependencies
```bash
cd ml/scraper
pip install -r requirements.txt
```

### 2. Configure Cloudflare R2 (Optional)

If using R2 storage, set environment variables:
```bash
export CLOUDFLARE_R2_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_R2_ACCESS_KEY_ID="your-access-key"
export CLOUDFLARE_R2_SECRET_ACCESS_KEY="your-secret"
```

Or update `scraper/settings.py`:
```python
CLOUDFLARE_R2_ACCOUNT_ID = "your-account-id"
CLOUDFLARE_R2_ACCESS_KEY_ID = "your-access-key"
CLOUDFLARE_R2_SECRET_ACCESS_KEY = "your-secret"
```

### 3. Run Scraper
```bash
# Quick test (single page)
scrapy crawl fragrantica

# Or use the runner script
python run_scraper.py

# With options
ROBOTSTXT_OBEY=True scrapy crawl fragrantica -a start_url="https://www.fragrantica.com/perfumes/"
```

## Output Format

Each fragrance is output as JSONL (newline-delimited JSON):
```json
{
  "id": "12345",
  "name": "Sauvage",
  "brand": "Dior",
  "year": 2015,
  "concentration": "EDP",
  "gender_label": "N/A",
  "description": "A fresh, spicy fragrance...",
  "top_notes": ["Bergamot", "Ambroxan"],
  "middle_notes": ["Lavender", "Ambroxan"],
  "base_notes": ["Ambroxan", "Cedar"],
  "accords": ["Fresh", "Spicy", "Citrus"],
  "review_count": 2500,
  "url": "https://www.fragrantica.com/perfumes/12345/name.html"
}
```

**Storage Path:** `raw/fragrantica/YYYY-MM-DD/fragrances.jsonl`

## Rate Limiting Details

- **Base Delay:** 1.0 second between requests (DOWNLOAD_DELAY)
- **Random Delay:** 0.5-2.0 seconds per request (RandomDelayMiddleware)
- **Actual Delay:** ~1.5-3.0 seconds average per request
- **Concurrent Requests:** 1 (CONCURRENT_REQUESTS = 1)
- **User Agents:** Rotates from 6 different User-Agent strings

## Scraped Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| id | str | Fragrantica fragrance ID | "12345" |
| name | str | Fragrance name | "Sauvage" |
| brand | str | Brand name | "Dior" |
| year | int or None | Release year | 2015 |
| concentration | str | EDP, EDT, Cologne | "EDP" |
| gender_label | str | Gender classification | "N/A" (neutral default) |
| description | str | Fragrance description (max 500 chars) | "A fresh, spicy..." |
| top_notes | list | Top notes (max 5) | ["Bergamot", "Ambroxan"] |
| middle_notes | list | Middle notes (max 5) | ["Lavender"] |
| base_notes | list | Base notes (max 5) | ["Cedar"] |
| accords | list | Fragrance accords (max 5) | ["Fresh", "Spicy"] |
| review_count | int | Number of user reviews | 2500 |
| url | str | Original Fragrantica URL | "https://..." |

## Pipeline Architecture

```
FragranticaSpider
    ↓ (yields items)
RandomDelayMiddleware (0.5-2.0s random delay)
    ↓
RotatingUserAgentMiddleware (random User-Agent)
    ↓
CloudflareR2Pipeline
    ├─ Buffer items (100 per batch)
    ├─ Convert to JSONL
    └─ Upload to R2 or local storage
```

## Troubleshooting

### "No fragrance links found"
- Fragrantica page structure may have changed
- Check `parse_fragrance()` selectors match current HTML
- Inspect page with browser Developer Tools, update CSS selectors

### R2 Upload Failures
- Verify credentials are correct
- Check R2 bucket exists and is accessible
- Scraper will fall back to local storage in `raw/fragrantica/`

### Low Item Count
- Fragrantica may be blocking requests (rate limiting)
- Increase random delay: adjust `min_delay` and `max_delay` in `middleware.py`
- Check `CONCURRENT_REQUESTS` is 1

### Memory Usage
- Items are batched in memory (default 100)
- Adjust batch size in `pipelines.py` `_flush_items()` if needed

## Integration with Scentrix Pipeline

After scraping, the raw JSONL data flows through:

1. **ml/pipeline/clean.py** — Data cleaning (90+ note mappings, deduplication)
2. **ml/pipeline/ingest.py** — Neo4j ingestion (idempotent MERGE)
3. **ml/tests/test_graph.py** — Validation (10 comprehensive checks)

Example workflow:
```bash
# 1. Scrape
python run_scraper.py
# Output: raw/fragrantica/2024-03-24/fragrances.jsonl

# 2. Clean
python -m ml.pipeline.clean raw/fragrantica/2024-03-24/fragrances.jsonl cleaned_fragrances.json

# 3. Ingest
python -m ml.pipeline.ingest cleaned_fragrances.json neo4j://localhost:7687 neo4j password

# 4. Validate
python -m ml.tests.test_graph neo4j://localhost:7687 neo4j password
```

## Files

- `scrapy.cfg` — Scrapy project configuration
- `scraper/settings.py` — Scrapy settings (rate limiting, pipelines, middleware)
- `scraper/middleware.py` — Custom middleware (delays, user agent rotation)
- `scraper/pipelines.py` — Cloudflare R2 pipeline for storage
- `scraper/spiders/fragrantica.py` — Main spider implementation
- `run_scraper.py` — Standalone runner script

## Notes

- Spider respects `robots.txt` on Fragrantica
- All requests include realistic User-Agent headers
- Data is gender-neutral by default (`gender_label: "N/A"`)
- Description text is capped at 500 characters
- Fields with no data return None or empty list

## Standalone External Bundle

For environments where the Scrapy pipeline is blocked, a standalone resumable scraper is available at `fragrantica.py`.

- **Target:** 5,000+ records with incremental output to `data/fragrantica_raw.json`
- **Resume:** auto-reads `scraper_checkpoint.json` on re-run; progress saved on interrupt
- **Setup:** `python -m venv .venv_scraper && pip install -r requirements.txt`
- **Run:** `python fragrantica.py --target-records 5000 --min-delay 1 --max-delay 3`
- **Runtime estimate:** ~6–14 hours for 5,000 records at 1–3s/request
- **Validation:** `python import_licensed_feed.py --input data/fragrantica_raw.json && python dataset_gate.py` (exit 0 = pass)
"""
