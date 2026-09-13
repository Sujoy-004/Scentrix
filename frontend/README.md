# Scentrix Frontend

Next.js 16 (TypeScript) application for fragrance discovery, adaptive preference quiz, and GraphSAGE-powered recommendations.

## Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | CatalogPage | Fragrance grid with search and accord family filters |
| `/auth/register` | RegisterPage | User registration with JWT auth |
| `/auth/login` | LoginPage | User login |
| `/quiz` | StandardQuiz | Adaptive preference quiz with confidence-based extension |
| `/recommendations` | RecommendationsPage | 3-state recommendations with StateIndicator |
| `/profile/history` | HistoryPage | Last quiz summary with stats and top matches |
| `/profile/wishlist` | WishlistPage | Saved fragrance collection |

## Key Components

- **StandardQuiz** — Adaptive quiz that rates fragrances 1–10, evaluates confidence, and requests extension questions when needed. Guest and authenticated sessions are both persisted in a process-local quiz session store (no Redis/Postgres).
- **StateIndicator** — Visual badge showing the user's current recommendation state (0–2: Anonymous, Quiz User/Cold, Warm) with strategy description, next-action CTA, and progress bars for state transitions.
- **FragranceCard** — Catalog item with rating star, match score, and recommendation reason (direct match, shared notes, shared accords, popularity).
- **State machine UI** — The `/recommendations` page header adapts to all 3 states with distinct badges, titles, and subtitle copy.

## State Management

Zustand store (`stores/app-store.ts`) manages:
- Quiz responses and session state
- Recommendations cache
- User session and auth tokens
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
