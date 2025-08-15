from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings
from models.database import Base
import redis
from typing import Generator

# PostgreSQL Database
engine = create_engine(
    settings.postgres_uri,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis connection
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis():
    """Get Redis client"""
    return redis_client