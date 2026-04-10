# Known Concerns & Tech Debt

## Security
- Hardcoded sensitive defaults might persist in templates (`.env.cloud.template`) mapped to backend setups. Needs active monitoring.
- Passwords implemented via local python-jose bcrypt logic rather than offloading to robust providers if enterprise compliance requires.

## Fragile Areas
- **Synthetic Inference Scripts**: `ml/generate_synthetic_data.py` is standalone and potentially loosely coupled to evolving FastAPI models. If DB schema shifts, ML flows may fail silently before Prefect alerts.
- **Frontend/Backend Synchronization**: High reactivity relying on hardcoded types that might drift from Pydantic schema exports unless typed endpoints exist (no `openapi-ts` ingestion explicitly defined in `package.json`).

## Performance
- Neural Discovery loader (`DiscoveryNeuralLoader.tsx`) heavily leverages D3 and Framer Motion concurrently in React. Complex interaction events could induce main thread stalls without `requestAnimationFrame` boundaries.
