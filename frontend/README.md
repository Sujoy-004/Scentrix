# Scentrix Frontend

Next.js 16 (TypeScript) application for fragrance discovery, adaptive preference quiz, and GraphSAGE-powered recommendations.

## Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | CatalogPage | Fragrance grid with search and accord family filters |
| `/auth/register` | RegisterPage | User registration with JWT + Supabase auth |
| `/auth/login` | LoginPage | User login |
| `/quiz` | StandardQuiz | Adaptive preference quiz with confidence-based extension |
| `/recommendations` | RecommendationsPage | 5-state recommendations with StateIndicator |
| `/profile/history` | HistoryPage | Last quiz summary with stats and top matches |
| `/profile/wishlist` | WishlistPage | Saved fragrance collection |

## Key Components

- **StandardQuiz** — Adaptive quiz that rates fragrances 1–10, evaluates confidence, and requests extension questions when needed. Supports guest (Redis) and authenticated (PostgreSQL) persistence.
- **StateIndicator** — Visual badge showing the user's current recommendation state (0–4) with strategy description, next-action CTA, and progress bars for state transitions.
- **FragranceCard** — Catalog item with rating star, match score, and recommendation reason (direct match, shared notes, shared accords, popularity).
- **State machine UI** — The `/recommendations` page header adapts to all 5 states with distinct badges, titles, and subtitle copy.

## State Management

Zustand store (`stores/app-store.ts`) manages:
- Quiz responses and session state
- Recommendations cache
- User session and auth tokens
- Fragrance catalog

## Key Data Flows

1. **Anonymous user** → sees catalog + popularity-based recommendations (State 0)
2. **Quiz completion** → ratings are stored → recommendations switch to GraphSAGE (State 1)
3. **Continued rating** → state advances through Cold (2) → Warm (3) → Mature (4), each with different recommendation strategies

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

See [ARCHITECTURE.md](../docs/ARCHITECTURE.md) for the canonical 5-state dispatch design and [backend/app/services/dispatcher.py](../backend/app/services/dispatcher.py) for the state machine implementation.
