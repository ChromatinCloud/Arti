"""
API Configuration
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """API Settings"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "postgresql://arti:arti@localhost/arti_db"
    
    # Redis for RQ
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # File Storage
    UPLOAD_DIR: str = "./uploads"
    RESULTS_DIR: str = "./results"
    TEMP_DIR: str = "./temp"
    MAX_UPLOAD_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000"
    ]
    
    # Job Settings
    JOB_TIMEOUT: int = 3600  # 1 hour
    MAX_JOBS_PER_USER: int = 10
    
    # Annotation Engine
    VEP_DOCKER_IMAGE: str = "ensemblorg/ensembl-vep:latest"
    ANNOTATION_ENGINE_PATH: str = "./src/annotation_engine"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()