# Scentrix Frontend

Next.js 16 (TypeScript) application for anonymous fragrance discovery: an adaptive preference quiz and GraphSAGE-powered recommendations with no account required.

## Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | CatalogPage | Fragrance grid with search and accord family filters |
| `/quiz` | StandardQuiz | Adaptive preference quiz with confidence-based extension |
| `/recommendations` | RecommendationsPage | 3-state recommendations with StateIndicator |
| `/families` | FamiliesPage | Fragrance family browse/directory |
| `/families/[family]` | FamilyPage | Fragrances within one olfactory family |
| `/fragrances/[id]` | FragranceDetailPage | Single fragrance detail + rating control |

There is no login, register, or profile surface — the product flow is anonymous end to end.

## Key Components

- **StandardQuiz** — Adaptive quiz that rates fragrances on a signed 1–10 scale (1–4 Dislike, 5 Neutral, 6–10 Like), evaluates confidence, and requests extension questions when needed. Guest sessions are persisted in a process-local quiz session store (no Redis/Postgres).
- **StateIndicator** — Visual badge showing the user's current recommendation state (0–2: Anonymous, Quiz User/Cold, Warm) with strategy description, next-action CTA, and progress bars for state transitions.
- **RatingControls** — Shared Dislike/Neutral/Love selector mapping to the signed scale: Dislike=3, Neutral=5, Love=9. Each selection feeds the local quiz store, which the `/recommendations/guest` request forwards to the backend.
- **FragranceCard** — Clickable recommendation card (navigates to `/fragrances/[id]`) with match score, recommendation reason, and the inline Dislike/Neutral/Love rating.
- **State machine UI** — The `/recommendations` page header adapts to all 3 states with distinct badges, titles, and subtitle copy.

## State Management

Zustand store (`stores/app-store.ts`) manages:
- Quiz responses, quiz confidence, and adaptive-quiz session state
- Recommendations cache
- Device-local preferences and wishlist
- Fragrance catalog

## Key Data Flows

1. **Anonymous user** → sees catalog + popularity-based recommendations (State 0)
2. **Quiz completion** → submissions pin the user to Cold (State 1, GraphSAGE user-vector KNN) regardless of how many ratings they have afterwards
3. **Without a quiz** → 1–2 ratings = Cold (State 1); 3+ ratings = Warm (State 2, feature-overlap scoring)

## Development

```bash
npm install          # Install dependencies
npm run dev          # Development server on :3000
npm run build        # Production build
npm run lint         # ESLint
npm run type-check   # TypeScript (tsc --noEmit)
npm run test:e2e     # Playwright E2E tests
```

## Production

Build with `npm run build` then `npm start`. For Docker-based deployment, see the root `Dockerfile` and `DEPLOYMENT.md`.

## Architecture

See [backend/app/services/dispatcher.py](../backend/app/services/dispatcher.py) for the 3-state dispatch implementation (ANONYMOUS → popularity, COLD → GraphSAGE user-vector KNN, WARM → feature-overlap scoring; quiz submission overrides WARM).
