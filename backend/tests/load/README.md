# Load Testing — Scentrix Phase 12B

## Quick Start

```bash
# Install locust
pip install locust>=2.31

# Ensure backend is running (Docker)
cd ../../ && docker compose up -d

# Dry run (1 user, 10 seconds)
locust --headless -u 1 -r 1 --run-time 10s --host http://localhost:8000

# Full ramp (20 users, ramp 2/sec, 5 minutes)
locust --headless -u 20 -r 2 --run-time 300s --host http://localhost:8000 --html load_report.html --csv load_results
```

## Scenarios

| # | Name | Endpoint | Type | Weight |
|---|------|----------|------|--------|
| 1 | Health Check | `GET /health` | `HealthCheckUser` | 1 |
| 2 | Guest Rec — State 0 | `POST /recommendations/guest` (empty) | `GuestRecUser` | 3 (×3 task) |
| 3 | Guest Rec — State 1 | `POST /recommendations/guest` (with quiz) | `GuestRecUser` | 3 (×2 task) |
| 4 | Quiz Session Start | `POST /fragrances/quiz/session/start` | `QuizStartUser` | 2 |

## Success Criteria

| Metric | Threshold |
|--------|-----------|
| Health P95 | < 200 ms |
| Guest Rec State 0 P95 | < 500 ms |
| Guest Rec State 1 P95 | < 2,000 ms |
| Quiz Start P95 | < 1,000 ms |
| Error rate (all) | < 1% |
| Correlation IDs present | 100% of responses |

## Files

- `locustfile.py` — User classes and task definitions
- `load_report.html` — Generated HTML report (after run)
- `load_results_*.csv` — Generated CSV stats (after run)
