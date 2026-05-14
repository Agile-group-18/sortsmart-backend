<div align="center">

# SortSmart Backend

**REST API for the SortSmart recycling app — aggregates Swedish recycling station data, manages user accounts, and serves a unified API to mobile clients.**

</div>

***

SortSmart helps people in Sweden find where to recycle their waste. Users describe what they want to dispose of, and the app routes them to the nearest appropriate recycling station.

This backend is **not** the source of truth for recycling station data — it is an **aggregation and normalization layer**. It fetches, caches, and normalises data from external Swedish recycling APIs, then exposes a single clean REST API to the mobile client.

***

## Links

| | |
|---|---|
| 🌐 **Live API** | https://sortsmart.kleopatra.pro |
| 📖 **Interactive Docs (Swagger UI)** | https://sortsmart.kleopatra.pro/docs |
| 📄 **OpenAPI Schema** | https://sortsmart.kleopatra.pro/openapi.json |
| 📚 **Getting Started (Wiki)** | https://github.com/Agile-group-18/sortsmart-backend/wiki/Getting-Started |
| 🏗 **Architecture** | https://github.com/agile-group-18/sortsmart-backend/wiki/Architecture |
| 📖 **API Reference** | https://github.com/agile-group-18/sortsmart-backend/wiki/API-Reference |

***

## What This Service Does

| Responsibility | Details |
|---|---|
| **Fetch & cache** | Pulls recycling station data from external APIs on a configurable schedule (`REFRESH_INTERVAL_HOURS`, default 7 days) |
| **Normalize** | Maps heterogeneous external schemas into a consistent internal model |
| **Location queries** | Serves nearby stations filtered by coordinates, waste category, and radius |
| **User accounts** | Registration, email verification, JWT auth (access + refresh tokens), profile management |
| **Community reports** | Users flag station issues (full, not working, etc.) which feed into the station status pipeline |
| **Item lookup** | Search and browse waste items to find which category they belong to |

***

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI 0.136 |
| Runtime | Python 3.13 |
| Database | PostgreSQL 18 |
| ORM | SQLAlchemy (async) |
| Migrations | Alembic |
| Auth | JWT — HS256, access + refresh token pair |
| Password hashing | Argon2 (via `argon2-cffi`) |
| Email | `fastapi-mail` + `aiosmtplib` (console mode for dev) |
| Scheduler | APScheduler 3 |
| Deployment | Docker + Docker Compose |
| Tunnel (prod) | Cloudflare Tunnel |

***

## API Overview

| Group | Base path | Auth required | Description |
|---|---|---|---|
| **Auth** | `/api/v1/auth/` | No | Register, login, logout, refresh, verify email, forgot/reset password |
| **Stations** | `/api/v1/stations/` | Partial* | List nearby, get detail, browse categories, report a station |
| **Items** | `/api/v1/items/` | No | List all items, search by name, get item by slug |
| **Profile** | `/api/v1/profile` | Yes | Get, update, delete your profile |
| **Health** | `/health` | No | Liveness check |

\* `GET /api/v1/stations` and `GET /api/v1/stations/{id}` are public. `POST /api/v1/stations/{id}/report` requires a Bearer token.

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

Full request/response schemas: [Swagger UI](https://sortsmart.kleopatra.pro/docs)

***

## Quickstart

**Prerequisites:** Docker, Docker Compose

```bash
git clone https://github.com/agile-group-18/sortsmart-backend
cd sortsmart-backend
cp .env.example .env
# Edit .env — set DATABASE_URL and SECRET_KEY at minimum
docker compose up --build
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

See the [Getting Started guide](https://github.com/Agile-group-18/sortsmart-backend/wiki/Getting-Started) for the full local development workflow including database seeding, running tests, and working with migrations.

***

## Key Query Parameters — Nearby Stations

```
GET /api/v1/stations?lat=57.7089&lon=11.9746&radius_km=5&limit=25
```

| Parameter | Type | Default | Max | Description |
|---|---|---|---|---|
| `lat` | float | — | ±90 | Latitude (required for nearby mode) |
| `lon` | float | — | ±180 | Longitude (required for nearby mode) |
| `radius_km` | float | 10.0 | 500 | Search radius in km |
| `category_ids` | int[] | `[]` | — | Filter by waste category IDs |
| `filter_mode` | enum | `any` | — | `any`: station has at least one category; `all`: station has all listed categories |
| `station_type` | string | — | — | Filter by station type string |
| `view` | enum | `map` | — | `map`: compact response with coordinates only; `list`: full detail per station |
| `limit` | int | 25 | 100 | Max results returned |

Omitting `lat`/`lon` returns a global list (`StationsResponse`). Providing both returns a proximity-sorted `NearbyResponse` with a `distance_km` field on each station.

***

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_URL` | — | **Yes** | PostgreSQL DSN, e.g. `postgresql+asyncpg://user:pass@db:5432/sortsmart` |
| `SECRET_KEY` | — | **Yes** | JWT signing secret — **change this in production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | No | Access token TTL (default: 7 days) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `90` | No | Refresh token TTL |
| `REFRESH_INTERVAL_HOURS` | `168` | No | How often external station data is re-fetched (default: 7 days) |
| `DEFAULT_RADIUS_KM` | `10` | No | Default search radius when `radius_km` is omitted |
| `DEFAULT_NEARBY_LIMIT` | `25` | No | Default result count for nearby queries |
| `MAX_NEARBY_LIMIT` | `100` | No | Hard cap on nearby results |
| `MAIL_CONSOLE` | `true` | No | Print emails to stdout instead of sending (dev mode) |
| `FRONTEND_URL` | — | No | Base URL for email links (verify, reset password) |
| `MAIL_USERNAME` | — | No (prod) | SMTP username |
| `MAIL_PASSWORD` | — | No (prod) | SMTP password |
| `MAIL_FROM` | — | No (prod) | Sender address |
| `MAIL_SERVER` | — | No (prod) | SMTP host |
| `MAIL_PORT` | `587` | No | SMTP port |

See `.env.example` for the full annotated list.

***

## Project Structure

```
sortsmart-backend/
├── app/
│   ├── core/
│   │   ├── deps.py          # FastAPI dependency injection (DB session, current user)
│   │   └── security.py      # JWT encode/decode, password hashing (Argon2)
│   ├── models/
│   │   ├── orm.py           # SQLAlchemy ORM models (User, Station, Category, Report, …)
│   │   └── schemas.py       # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py          # /api/v1/auth/* endpoints
│   │   ├── stations.py      # /api/v1/stations/* endpoints
│   │   ├── profile.py       # /api/v1/profile endpoints
│   │   └── web.py           # HTML views for email verification and password reset
│   ├── services/
│   │   ├── auth.py          # Auth business logic (register, login, token rotation)
│   │   ├── stations.py      # Station query logic, report aggregation
│   │   ├── email.py         # Email dispatch (console or SMTP)
│   │   └── profile.py       # Profile update/delete logic
│   ├── config.py            # Pydantic Settings — reads from .env
│   ├── database.py          # Async SQLAlchemy engine + session factory
│   ├── fetcher.py           # External API fetcher and data normaliser
│   ├── scheduler.py         # APScheduler setup — triggers fetcher on interval
│   └── main.py              # FastAPI app factory, router registration, lifespan
├── alembic/
│   └── versions/            # Migration files
├── tests/
│   ├── test_auth.py
│   └── test_stations.py
├── docker-compose.yml        # Local dev (API + DB)
├── docker-compose.prod.yml   # Production overrides
├── Dockerfile
├── docker-entrypoint.sh      # Runs migrations then starts uvicorn
├── .env.example
└── requirements.txt
```

***

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. If you changed any ORM models:
   - Spin up the database: `docker compose up db -d`
   - Generate a migration: `docker compose run --rm api alembic revision --autogenerate -m "describe change"`
   - Commit **both** the model change and the generated migration file
4. Open a pull request against `main`

See the [Getting Started wiki](https://github.com/Agile-group-18/sortsmart-backend/wiki/Getting-Started) for the full local dev workflow.

***

## License

[MIT](./LICENSE) — Agile Group 18
