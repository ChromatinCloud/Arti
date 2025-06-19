#!/usr/bin/env python3
"""
Arti API Server - FastAPI backend for annotation engine

Provides REST API endpoints for:
- File upload and job management
- Variant annotation processing
- Results retrieval and visualization
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from .database import init_db, close_db
from .routers import auth, jobs, variants, reports
from .config import settings
from .websocket import websocket_endpoint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle
    """
    # Startup
    logger.info("Starting Arti API server...")
    
    # Initialize database
    await init_db()
    
    # Create necessary directories
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.RESULTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)
    
    logger.info("API server ready")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API server...")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Arti Annotation Engine API",
    description="REST API for cancer variant annotation and interpretation",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(variants.router, prefix="/api/variants", tags=["variants"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

# Add WebSocket endpoint
app.add_api_websocket_route("/ws/jobs/{job_id}", websocket_endpoint)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Arti Annotation Engine API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "arti-api",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )