# Code Conventions

## Python (Backend)
- **Formatting**: Ruff (`ruff format`)
- **Linting**: Ruff (`ruff check`)
- **Type Checking**: MyPy
- **Naming**: 
  - `snake_case` for variables/functions.
  - `PascalCase` for Pydantic/SQLAlchemy models.
- **Patterns**: Dependency Injection for DB sessions and Auth.

## TypeScript (Frontend)
- **Formatting**: Prettier
- **Linting**: ESLint (Next.js defaults)
- **Typing**: Strict TypeScript.

## Security
- **PII Policy**: `full_name` and `email` MUST be encrypted at rest using `DataVault.encrypt()`.
- **API Response**: Decryption must happen in the Router layer, never stored plaintext in Postgres.
