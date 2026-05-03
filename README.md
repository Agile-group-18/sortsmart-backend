# SortSmart Backend

> REST API backend for the SortSmart recycling app — a centralized middleware layer that aggregates external recycling data sources, handles user accounts, and serves a clean unified API to the mobile client.

**SortSmart helps people in Sweden find where to recycle their waste.** Users describe what they want to dispose of, and the app routes them to the nearest appropriate recycling station. The backend ties together external recycling station data APIs, location services, and user account management into a single service.

- **Live API:** https://sortsmart.kleopatra.pro
- **Interactive Docs (Swagger UI):** https://sortsmart.kleopatra.pro/docs
- **OpenAPI Schema:** https://sortsmart.kleopatra.pro/openapi.json

---

## What This Service Does

The backend is not the source of truth for recycling station data — it is an aggregation and normalization layer. It:

- **Fetches and caches** recycling station data from external APIs (refreshed on a configurable interval via `REFRESH_INTERVAL_HOURS`)
- **Normalizes** external data into a consistent schema for the mobile client
- **Serves location-aware queries** — nearby stations filtered by waste category and radius
- **Manages user accounts** — registration, email verification, JWT auth, profile management
- **Accepts community reports** — users can flag station issues, which feed into the verification pipeline

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL 18 |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Auth | JWT (HS256, access + refresh tokens) |
| Email | SMTP (configurable, console mode for dev) |
| Runtime | Docker + Docker Compose |
| Tunnel (prod) | Cloudflare Tunnel |

---

## API Overview

| Group | Endpoints | Auth required |
|---|---|---|
| **Auth** | Register, Login, Logout, Refresh, Verify email, Forgot/Reset password | No |
| **Stations** | List nearby, Get detail, Browse categories, Report a station | Yes |
| **Profile** | Get, Update, Delete | Yes |
| **Health** | `GET /health` | No |

All protected endpoints require a `Bearer` token in the `Authorization` header. Full request/response schemas are available in the [Swagger UI](https://sortsmart.kleopatra.pro/docs).

### Key query parameters — Nearby stations

```
GET /api/v1/stations?lat=57.7089&lon=11.9746&radius_km=5&limit=25
```

| Parameter | Default | Max | Description |
|---|---|---|---|
| `lat`, `lon` | — | — | User coordinates (required) |
| `radius_km` | 10 | 500 | Search radius |
| `limit` | 25 | 100 | Max results returned |

---

## Project Structure

```
└── 📁sortsmart-backend
    └── 📁app
        └── 📁core
            ├── __init__.py
            ├── deps.py
            ├── security.py
        └── 📁models
            ├── __init__.py
            ├── orm.py
            ├── schemas.py
        └── 📁routers
            ├── __init__.py
            ├── auth.py
            ├── profile.py
            ├── stations.py
            ├── web.py
        └── 📁services
            ├── __init__.py
            ├── auth.py
            ├── email.py
            ├── profile.py
            ├── stations.py
        ├── __init__.py
        ├── config.py
        ├── database.py
        ├── fetcher.py
        ├── main.py
        ├── scheduler.py
    └── 📁tests
        ├── __init__.py
        ├── test_auth.py
        ├── test_stations.py
    ├── .dockerignore
    ├── .env.example
    ├── .gitattributes
    ├── .gitignore
    ├── alembic.ini
    ├── docker-compose.prod.yml
    ├── docker-compose.yml
    ├── docker-entrypoint.sh
    ├── Dockerfile
    ├── LICENSE
    └── requirements.txt
```

---

## Quickstart

See [GETTING_STARTED.md]([./GETTING_STARTED.md](https://github.com/Agile-group-18/sortsmart-backend/wiki/Getting-Started)) for the full setup guide.

```bash
git clone https://github.com/agile-group-18/sortsmart-backend
cd sortsmart-backend
cp .env.example .env
docker compose -f docker-compose.yml up --build
```

API available at `http://localhost:8000` · Docs at `http://localhost:8000/docs`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `SECRET_KEY` | — | JWT signing secret — **change in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Access token lifetime (7 days) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `90` | Refresh token lifetime |
| `REFRESH_INTERVAL_HOURS` | `168` | How often external station data is re-fetched (7 days) |
| `DEFAULT_RADIUS_KM` | `10` | Default search radius for nearby stations |
| `DEFAULT_NEARBY_LIMIT` | `25` | Default result count for nearby queries |
| `MAX_NEARBY_LIMIT` | `100` | Hard cap on nearby results |
| `MAIL_CONSOLE` | `true` | Print emails to logs instead of sending (dev only) |
| `FRONTEND_URL` | — | Used in email links (verify email, reset password) |

See `.env.example` for the full list including SMTP configuration.

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. If you changed any models,
   1. spin up throwaway db container `docker compose up db -d`
   2. generate a migration: `docker compose run --rm api alembic revision --autogenerate -m "describe change"`
5. Commit both the model change and the generated migration file
6. Open a pull request against `main`

See [GETTING_STARTED.md]([./GETTING_STARTED.md](https://github.com/Agile-group-18/sortsmart-backend/wiki/Getting-Started)) for the full local development workflow.
