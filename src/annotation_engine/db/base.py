"""
Database base configuration and session management

Provides SQLAlchemy base class, engine creation, and session management
following the blueprint specifications.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Base class for all database models
Base = declarative_base()

# Metadata with naming conventions for constraints
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s", 
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """Get database URL from environment or default to SQLite"""
    
    # Check for environment variables first
    if db_url := os.getenv("DATABASE_URL"):
        return db_url
    
    # Default to SQLite in .refs directory
    repo_root = Path(__file__).parent.parent.parent.parent
    db_path = repo_root / ".refs" / "database" / "annotation_engine.db"
    
    # Ensure database directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return f"sqlite:///{db_path}"


def init_db(database_url: str = None, echo: bool = False) -> None:
    """Initialize database engine and session factory"""
    global _engine, _SessionLocal
    
    if database_url is None:
        database_url = get_database_url()
    
    logger.info(f"Initializing database: {database_url}")
    
    # Create engine with appropriate settings
    if database_url.startswith("sqlite"):
        # SQLite-specific settings
        _engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False}  # Allow SQLite in multi-threaded env
        )
    else:
        # PostgreSQL or other databases
        _engine = create_engine(database_url, echo=echo)
    
    # Create session factory
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=_engine)
    logger.info("Database tables created successfully")


def get_session() -> Session:
    """Get a new database session"""
    if _SessionLocal is None:
        init_db()
    
    return _SessionLocal()


@contextmanager
def get_db_session():
    """Context manager for database sessions with automatic cleanup"""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db() -> None:
    """Reset database by dropping and recreating all tables (development only)"""
    global _engine
    
    if _engine is None:
        init_db()
    
    logger.warning("Resetting database - all data will be lost!")
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    logger.info("Database reset complete")


def get_engine():
    """Get the current database engine"""
    if _engine is None:
        init_db()
    return _engine