# Contributing to SortSmart Backend

Thanks for taking the time to contribute. This guide covers everything you need to get changes merged cleanly.

***

## Prerequisites

- Docker and Docker Compose
- Python 3.13 (for running tests and linting outside Docker)
- Git

***

## Getting Started

```bash
git clone https://github.com/agile-group-18/sortsmart-backend
cd sortsmart-backend
cp .env.example .env
```

Edit `.env` and set at minimum:
```
DATABASE_URL=postgresql+asyncpg://sortsmart:sortsmart@db:5432/sortsmart
SECRET_KEY=dev-secret-change-me-in-production
MAIL_CONSOLE=true
```

Start the full stack:
```bash
docker compose up --build
```

The API is available at http://localhost:8000 and docs at http://localhost:8000/docs.

***

## Development Workflow

### Branch naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<short-description>` | `feat/item-search` |
| Bug fix | `fix/<short-description>` | `fix/refresh-token-expiry` |
| Docs | `docs/<short-description>` | `docs/api-reference` |
| Chore | `chore/<short-description>` | `chore/update-deps` |

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add full-text search for waste items
fix: refresh token not invalidated on logout
docs: update environment variable table
chore: bump fastapi to 0.136
```

***

## Working With Database Migrations

If your PR modifies any ORM model in `app/models/orm.py`, you **must** generate and commit a migration.

```bash
# 1. Start just the database container
docker compose up db -d

# 2. Generate a migration from your model changes
docker compose run --rm api alembic revision --autogenerate -m "add item full-text index"

# 3. Review the generated file in alembic/versions/
# Make sure it looks correct — autogenerate is not always perfect.

# 4. Apply and verify
docker compose run --rm api alembic upgrade head

# 5. Commit both the model change AND the migration file
git add app/models/orm.py alembic/versions/<new_migration>.py
git commit -m "feat: add item full-text index"
```

> **Never** edit existing migration files that have already been merged to `main`. Always create a new migration.

***

## Running Tests

```bash
# All tests inside Docker (recommended — matches CI environment)
docker compose run --rm api pytest

# With verbose output
docker compose run --rm api pytest -v

# A specific file
docker compose run --rm api pytest tests/test_auth.py

# Outside Docker (requires a local .env with a reachable DATABASE_URL)
pip install -r requirements.txt
pytest
```

Tests use a separate test database configured in `tests/conftest.py`. The test database is created and torn down automatically.

***

## Code Style

- **No linter config is enforced in CI** right now, but please follow PEP 8.
- Keep routers thin — no business logic in router functions. Put it in `services/`.
- Use type hints throughout. All public functions should have complete signatures.
- Add docstrings to service functions that contain non-obvious logic.
- If you add a new environment variable, add it to both `.env.example` and the Environment Variables table in `README.md`.

***

## Adding a New Endpoint

1. Add the Pydantic request/response schemas to `app/models/schemas.py`.
2. Add the business logic to the appropriate service in `app/services/` (or create a new one).
3. Add the route to the appropriate router in `app/routers/` (or create a new one and register it in `app/main.py`).
4. Write tests in `tests/`.
5. The OpenAPI docs at `/docs` update automatically.

***

## Adding a New External Data Source

1. Add a new fetch function to `app/fetcher.py`.
2. Map the external schema to the `Station` ORM model inside the fetcher.
3. Call the new fetch function from `fetcher.py`'s main entry point so it runs on the scheduler interval.
4. If the source introduces new fields, add them to the ORM model and generate a migration.

***

## Pull Request Checklist

Before opening a PR, verify:

- [ ] All tests pass: `docker compose run --rm api pytest`
- [ ] If ORM models changed, a migration is committed alongside
- [ ] New environment variables are documented in `.env.example` and `README.md`
- [ ] No secrets or `.env` files committed
- [ ] Branch is up to date with `main`
- [ ] PR description explains *what* changed and *why*

***

## Reporting Issues

Open a [GitHub Issue](https://github.com/agile-group-18/sortsmart-backend/issues) with:
- A clear title describing the problem
- Steps to reproduce
- Expected vs. actual behaviour
- Relevant logs or error messages
