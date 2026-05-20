import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .database import Base
from . import scheduler
from .routers import auth, stations, profile, web, items, tips

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s  %(name)s  %(message)s",
)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Import models so SQLAlchemy registers them before create_all
    from .models import orm  # noqa: F401

    # Managed by Alembic migrations, so we don't want to create tables automatically
    # Base.metadata.create_all(bind=engine)
    scheduler.start()
    yield
    scheduler.stop()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Backend for the SortSmart recycling station app.",
    lifespan=lifespan,
    redirect_slashes=False,  # /*/ -> /* avoiding issues with trailing slashes and rate limiting
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(web.router)
app.include_router(auth.router, prefix=PREFIX)
app.include_router(stations.router, prefix=PREFIX)
app.include_router(profile.router, prefix=PREFIX)
app.include_router(items.router, prefix=PREFIX)
app.include_router(tips.router, prefix=PREFIX)


@app.middleware("http")
async def no_cache_private(request, call_next):
    resp = await call_next(request)
    if any(request.url.path.startswith(p) for p in ["/api/v1/auth", "/api/v1/profile"]):
        resp.headers["Cache-Control"] = "no-store, private"
    return resp


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": settings.app_name}
