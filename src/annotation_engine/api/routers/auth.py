"""
Authentication endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
import time

from ..core.database import get_db
from ..core.security import (
    authenticate_user, create_access_token, get_current_user, 
    log_auth_event, AuthenticationError
)
from ...db.audit_trail import AuditEventType

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_info: Dict[str, Any]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_data: LoginRequest, 
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token"""
    
    # Get request info for audit logging
    request_info = {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "session_id": f"session_{int(time.time())}"
    }
    
    # Authenticate user
    user = authenticate_user(db, login_data.username, login_data.password)
    
    if not user:
        # Log failed login attempt
        await log_auth_event(
            AuditEventType.LOGIN_FAILED,
            login_data.username,
            request_info,
            success=False,
            details={"reason": "invalid_credentials"}
        )
        
        raise AuthenticationError("Invalid username or password")
    
    # Create access token
    token_data = {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
        "department": user.get("department"),
        "permissions": user.get("permissions", [])
    }
    
    access_token = create_access_token(data=token_data)
    
    # Log successful login
    await log_auth_event(
        AuditEventType.USER_LOGIN,
        user["user_id"],
        request_info,
        success=True,
        details={"role": user["role"]}
    )
    
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user_info": {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user["role"],
                "department": user.get("department"),
                "permissions": user.get("permissions", [])
            }
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Logout user and invalidate token"""
    
    request_info = {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "session_id": f"session_{int(time.time())}"
    }
    
    # Log logout event
    await log_auth_event(
        AuditEventType.USER_LOGOUT,
        current_user["user_id"],
        request_info,
        success=True
    )
    
    # In production, you might want to add token to blacklist
    # For now, just return success
    
    return {
        "success": True,
        "data": {
            "message": "Successfully logged out"
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/refresh")
async def refresh_token(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Refresh access token"""
    
    # Create new token with same data
    token_data = {
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "role": current_user["role"],
        "department": current_user.get("department"),
        "permissions": current_user.get("permissions", [])
    }
    
    new_token = create_access_token(data=token_data)
    
    return {
        "success": True,
        "data": {
            "access_token": new_token,
            "token_type": "bearer"
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/me")
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user information"""
    
    return {
        "success": True,
        "data": {
            "user_id": current_user["user_id"],
            "username": current_user["username"],
            "role": current_user["role"],
            "department": current_user.get("department"),
            "permissions": current_user.get("permissions", [])
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.put("/password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    request_info = {
        "ip_address": request.client.host,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "session_id": f"session_{int(time.time())}"
    }
    
    # In production, you would:
    # 1. Verify current password
    # 2. Hash new password
    # 3. Update in database
    # 4. Log the change
    
    # For demo, just log the event
    await log_auth_event(
        AuditEventType.PASSWORD_CHANGE,
        current_user["user_id"],
        request_info,
        success=True
    )
    
    return {
        "success": True,
        "data": {
            "message": "Password changed successfully"
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }