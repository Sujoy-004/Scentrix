# Summary: Plan 01-02 Completed

## Objective
Remove 4 dead 503 endpoints from fragrances.py and scrub corresponding frontend code.

## Accomplished Tasks
- ✅ Removed 4 dead endpoint functions from `backend/app/routers/fragrances.py`:
  - recommend_by_text()
  - get_recommendation_weekly_metrics()
  - get_recommendation_result()
  - recommend_by_profile()
- ✅ Cleaned unused imports associated with removed endpoints
- ✅ Rewrote `getFragranceCatalog` in `frontend/src/lib/api.ts` to use direct catalog search
- ✅ Verified no remaining references to removed endpoints in frontend code
- ✅ Formatted code with ruff and verified with mypy

## Changes Made
### Backend (fragrances.py)
- Removed 4 endpoint functions and their decorators (~400 lines)
- Removed unused schema imports (RecommendationJob, RecommendationResult, RecommendationWeeklyMetrics, TextRecommendationRequest)
- Kept necessary imports for remaining functionality
- Router file shortened as expected

### Frontend (api.ts)
- Removed polling loop and job_id handling
- Changed text search to directly call `/fragrances/catalog?q=...`
- Maintained same function signature and return type
- Eliminated async recommendation polling pattern

### Verification
- All dead endpoints now return 404 (not 503)
- Frontend text search no longer calls dead endpoints
- Code formatting and type checking pass
- No breaking changes to remaining functionality

## Files Modified
- backend/app/routers/fragrances.py
- frontend/src/lib/api.ts
- frontend/src/lib/hooks.ts (verified clean, no changes needed)

## Success Criteria Met
- [x] GET /fragrances/recommend/{job_id} returns 404
- [x] GET /fragrances/recommend/metrics/weekly returns 404
- [x] POST /fragrances/recommend/text returns 404
- [x] POST /fragrances/recommend/profile returns 404
- [x] Frontend text search completes without hitting /fragrances/recommend/text

## Next Steps
Proceed with Plan 01-03: Create Neo4j graph service + import rewiring