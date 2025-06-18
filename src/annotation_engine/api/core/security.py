"""
Authentication and authorization for FastAPI application
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from .config import get_settings
from .database import get_db
from ...db.models import User  # We'll need to create this model
from ...db.audit_trail import get_audit_manager, create_audit_context, AuditEventType, AuditSeverity

logger = logging.getLogger(__name__)
settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
        
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid token")


def authenticate_user(db: Session, username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with username/password"""
    try:
        # This would query the actual User model
        # For now, we'll use a simple mock
        if username == "demo_user" and password == "demo_password":
            return {
                "user_id": "demo_user",
                "username": "demo_user", 
                "role": "clinician",
                "department": "Molecular Pathology",
                "permissions": ["read_cases", "write_interpretations", "approve_reports"]
            }
        
        # In production, this would be:
        # user = db.query(User).filter(User.username == username).first()
        # if user and verify_password(password, user.hashed_password):
        #     return {
        #         "user_id": user.user_id,
        #         "username": user.username,
        #         "role": user.role,
        #         "department": user.department,
        #         "permissions": user.permissions
        #     }
        
        return None
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current authenticated user from token"""
    
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("user_id")
    if not user_id:
        raise AuthenticationError("Invalid token payload")
    
    # In production, verify user still exists in database
    # user = db.query(User).filter(User.user_id == user_id).first()
    # if not user:
    #     raise AuthenticationError("User not found")
    
    # For demo, return payload data
    return {
        "user_id": payload.get("user_id"),
        "username": payload.get("username"),
        "role": payload.get("role", "user"),
        "department": payload.get("department"),
        "permissions": payload.get("permissions", [])
    }


def require_permission(permission: str):
    """Decorator factory for requiring specific permissions"""
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_permissions = current_user.get("permissions", [])
        
        if permission not in user_permissions and "admin" not in user_permissions:
            raise AuthorizationError(f"Permission required: {permission}")
        
        return current_user
    
    return permission_checker


def require_role(role: str):
    """Decorator factory for requiring specific roles"""
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")
        
        # Admin can access everything
        if user_role == "admin":
            return current_user
        
        if user_role != role:
            raise AuthorizationError(f"Role required: {role}")
        
        return current_user
    
    return role_checker


async def log_auth_event(
    event_type: AuditEventType,
    user_id: str,
    request_info: Dict[str, str],
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
):
    """Log authentication/authorization events for audit trail"""
    try:
        audit_manager = get_audit_manager()
        
        audit_context = create_audit_context(
            user_id=user_id,
            session_id=request_info.get("session_id", "unknown"),
            request_context={
                "ip_address": request_info.get("ip_address", "unknown"),
                "user_agent": request_info.get("user_agent", "unknown")
            }
        )
        
        severity = AuditSeverity.LOW if success else AuditSeverity.HIGH
        description = f"Authentication event: {event_type.value}"
        
        if not success:
            description += " - FAILED"
        
        audit_manager.log_event(
            event_type=event_type,
            description=description,
            audit_context=audit_context,
            severity=severity,
            success=success,
            **(details or {})
        )
        
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")


# Role-based dependency shortcuts
require_clinician = require_role("clinician")
require_admin = require_role("admin")
require_read_cases = require_permission("read_cases")
require_write_interpretations = require_permission("write_interpretations")
require_approve_reports = require_permission("approve_reports")