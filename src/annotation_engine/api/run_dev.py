#!/usr/bin/env python3
"""
Development server startup script for Annotation Engine API
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Start the development server"""
    
    # Set development environment
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./annotation_engine_dev.db")
    
    print("🚀 Starting Annotation Engine API Development Server...")
    print("📊 Dashboard will be available at: http://localhost:8000/docs")
    print("🔍 API Explorer: http://localhost:8000/redoc")
    print("❤️  Health Check: http://localhost:8000/health")
    print()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()