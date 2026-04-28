from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # drops stale connections automatically
    pool_size=10,  # max persistent connections in the pool
    max_overflow=20,  # extra connections allowed under burst load
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
