"""
Database models and connection management
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, JSON, ForeignKey, Enum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import enum

from .config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for models
Base = declarative_base()


class JobStatus(str, enum.Enum):
    """Job status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    jobs = relationship("Job", back_populates="user")


class Job(Base):
    """Annotation job model"""
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job details
    name = Column(String, nullable=False)
    description = Column(Text)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    
    # Input/Output
    input_file = Column(String, nullable=False)
    output_dir = Column(String)
    
    # Parameters
    cancer_type = Column(String)
    case_uid = Column(String)
    parameters = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Progress
    progress = Column(Integer, default=0)
    total_variants = Column(Integer)
    current_step = Column(String)
    
    # Results
    error_message = Column(Text)
    result_summary = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    variants = relationship("Variant", back_populates="job")


class Variant(Base):
    """Variant model"""
    __tablename__ = "variants"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Variant identifiers
    chromosome = Column(String, index=True)
    position = Column(Integer, index=True)
    reference = Column(String)
    alternate = Column(String)
    
    # Annotations
    gene_symbol = Column(String, index=True)
    transcript_id = Column(String)
    hgvs_c = Column(String)
    hgvs_p = Column(String)
    consequence = Column(String)
    
    # Evidence and scores
    amp_tier = Column(String)
    vicc_tier = Column(String)
    confidence_score = Column(Float)
    
    # Population frequencies
    gnomad_af = Column(Float)
    gnomad_af_popmax = Column(Float)
    
    # Clinical evidence
    oncokb_evidence = Column(JSON)
    civic_evidence = Column(JSON)
    cosmic_evidence = Column(JSON)
    
    # Full annotation data
    annotations = Column(JSON)
    
    # Relationships
    job = relationship("Job", back_populates="variants")


# Database initialization
async def init_db():
    """Initialize database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()


# Dependency for getting DB session
async def get_db():
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()