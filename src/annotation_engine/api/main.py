"""
FastAPI Main Application - Phase 3B Sprint 1

Entry point for the Annotation Engine REST API with streamlined clinical endpoints.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import uuid
from contextlib import asynccontextmanager

# API Router imports
from .routers import auth, variants, cases, interpretations, evidence, search, analytics, users, jobs, tech_filtering
from .core.config import get_settings
from .core.database import init_database
from .core.security import get_current_user
from .middleware.audit import AuditMiddleware
from .middleware.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Annotation Engine API...")
    
    # Initialize database
    init_database()
    
    # Log startup
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Annotation Engine API...")


# Create FastAPI application
app = FastAPI(
    title="Annotation Engine API",
    description="Clinical variant interpretation API with comprehensive knowledge base integration",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler with consistent response format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "details": {}
            },
            "meta": {
                "timestamp": time.time(),
                "version": "1.0.0",
                "request_id": getattr(request.state, "request_id", str(uuid.uuid4()))
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unexpected errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "details": {}
            },
            "meta": {
                "timestamp": time.time(),
                "version": "1.0.0",
                "request_id": getattr(request.state, "request_id", str(uuid.uuid4()))
            }
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


# API route registration
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(variants.router, prefix="/api/v1/variants", tags=["Variant Processing"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Job Management"])
app.include_router(cases.router, prefix="/api/v1/cases", tags=["Clinical Workflow"])
app.include_router(interpretations.router, prefix="/api/v1/interpretations", tags=["Interpretations"])
app.include_router(evidence.router, prefix="/api/v1/evidence", tags=["Clinical Evidence"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search & Discovery"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(users.router, prefix="/api/v1/users", tags=["User Management"])
app.include_router(tech_filtering.router, tags=["Technical Filtering"])


# Root endpoint with API information
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "success": True,
        "data": {
            "name": "Annotation Engine API",
            "version": "1.0.0",
            "description": "Clinical variant interpretation API",
            "documentation": "/docs" if settings.ENVIRONMENT != "production" else None,
            "health": "/health"
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info"
    )