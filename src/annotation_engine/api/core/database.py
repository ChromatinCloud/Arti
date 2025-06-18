"""
Database connection and session management for FastAPI
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from .config import get_settings
from ...db.base import Base, get_database_url
from ...db.init_expanded_db import init_expanded_database

logger = logging.getLogger(__name__)
settings = get_settings()

# Create database engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Validate connections before use
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """Initialize database with expanded schema"""
    try:
        logger.info("Initializing database schema...")
        init_expanded_database(
            database_url=settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            include_sample_data=settings.ENVIRONMENT == "development"
        )
        logger.info("Database initialization complete")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session
    
    Usage in FastAPI endpoints:
    ```
    @app.get("/example")
    async def example(db: Session = Depends(get_db)):
        # Use db session here
    ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session for non-FastAPI use"""
    return SessionLocal()


def check_db_health() -> dict:
    """Check database connection health"""
    try:
        db = SessionLocal()
        # Simple query to test connection
        db.execute("SELECT 1")
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow()
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }