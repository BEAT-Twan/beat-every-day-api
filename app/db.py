from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_session() -> Iterator[Session]:
    """
    FastAPI dependency: yields a DB session and closes it afterwards.
    NOTE: Do NOT decorate this with @contextmanager. FastAPI expects a generator.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Utility context manager for internal use (non-Dependency).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
