"""
Audit middleware for logging all API requests
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all API requests for audit trail"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record request start time
        start_time = time.time()
        
        # Log request
        logger.info(
            f"API Request: {request.method} {request.url.path} "
            f"[ID: {request_id}] [IP: {request.client.host}]"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"API Response: {response.status_code} "
            f"[ID: {request_id}] [Time: {process_time:.3f}s]"
        )
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response