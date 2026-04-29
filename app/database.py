from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # drops stale connections automatically
    pool_size=10,  # persistent connections kept open per worker
    max_overflow=10,  # extra connections allowed under burst load
    pool_timeout=30,  # raises error if no connection available after 30s
    pool_recycle=1800,  # recycle connections after 30 min
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: opens a session, yields it, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
