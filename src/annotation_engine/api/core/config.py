"""
Configuration management for FastAPI application
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    APP_NAME: str = "Annotation Engine API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # Security settings
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/annotation_engine"
    DATABASE_ECHO: bool = False
    
    # Redis settings (for caching and background jobs)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security and networking
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # File upload settings
    MAX_UPLOAD_SIZE_MB: int = 100
    UPLOAD_DIR: str = "./uploads"
    
    # Knowledge base settings
    KB_BASE_PATH: str = ".refs"
    KB_CACHE_TTL_HOURS: int = 24
    
    # Clinical settings
    ENABLE_AUDIT_LOGGING: bool = True
    REQUIRE_MFA_FOR_ADMIN: bool = True
    
    # Background job settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # Email settings (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()