# Coding Conventions

## Python (Backend & ML)
- Type hinting enforced rigorously via `mypy` natively.
- Linting standard: `ruff` (selects E, W, F, I, C, B, UP). Line length 100.
- Formatting: `black`.
- API framework: `FastAPI` + `Pydantic` v2 strict schemas.

## TypeScript (Frontend)
- Type safety enforced strictly (`tsc --noEmit`).
- Codebase style relies on `eslint` with specific configurations for Next.js 16.
- Styling: Utility-first CSS classes (Tailwind CSS v4). Component composition logic preferred. 
- Global UI animations handled homogenously via `framer-motion`.

## Commit & Planning
- GSD paradigm utilized locally via `.planning/` directory context threads.
- Adherence to atomic implementations.
