"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time

from ..core.database import get_db
from ..core.security import get_current_user, require_admin

router = APIRouter()


class UserRequest(BaseModel):
    """Request model for user creation/update"""
    username: str
    email: str
    role: str
    department: Optional[str] = None
    permissions: List[str] = []


class UserResponse(BaseModel):
    """Response model for user data"""
    user_id: str
    username: str
    email: str
    role: str
    department: Optional[str]
    permissions: List[str]
    is_active: bool
    created_at: float
    last_login: Optional[float]


# Demo user data
demo_users = {
    "demo_user": {
        "user_id": "demo_user",
        "username": "demo_user",
        "email": "demo@example.com",
        "role": "clinician",
        "department": "Molecular Pathology",
        "permissions": ["read_cases", "write_interpretations", "approve_reports"],
        "is_active": True,
        "created_at": time.time() - 86400 * 30,  # 30 days ago
        "last_login": time.time() - 3600  # 1 hour ago
    },
    "admin_user": {
        "user_id": "admin_user",
        "username": "admin_user", 
        "email": "admin@example.com",
        "role": "admin",
        "department": "IT",
        "permissions": ["admin"],
        "is_active": True,
        "created_at": time.time() - 86400 * 90,  # 90 days ago
        "last_login": time.time() - 7200  # 2 hours ago
    }
}


@router.get("/")
async def list_users(
    current_user: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    
    users_list = list(demo_users.values())
    
    return {
        "success": True,
        "data": {
            "users": users_list,
            "total": len(users_list)
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/")
async def create_user(
    user_request: UserRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new user (admin only)"""
    
    # Check if username already exists
    if user_request.username in demo_users:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )
    
    new_user = {
        "user_id": user_request.username,
        "username": user_request.username,
        "email": user_request.email,
        "role": user_request.role,
        "department": user_request.department,
        "permissions": user_request.permissions,
        "is_active": True,
        "created_at": time.time(),
        "last_login": None
    }
    
    demo_users[user_request.username] = new_user
    
    return {
        "success": True,
        "data": new_user,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_request: UserRequest,
    current_user: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user information (admin only)"""
    
    if user_id not in demo_users:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} not found"
        )
    
    user = demo_users[user_id]
    
    # Update user fields
    user.update({
        "email": user_request.email,
        "role": user_request.role,
        "department": user_request.department,
        "permissions": user_request.permissions,
        "updated_at": time.time()
    })
    
    return {
        "success": True,
        "data": user,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }