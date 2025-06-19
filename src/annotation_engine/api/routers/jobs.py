"""
Job management endpoints for annotation processing
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import time

from ..core.database import get_db
from ..core.security import get_current_user, require_read_cases
from .variants import annotation_jobs  # Import job storage

router = APIRouter()


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Get annotation job status and results"""
    
    if job_id not in annotation_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    job = annotation_jobs[job_id]
    
    # Check if user owns this job or is admin
    if job["user_id"] != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied to this job"
        )
    
    return {
        "success": True,
        "data": {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job["progress"],
            "message": job["message"],
            "created_at": job["created_at"],
            "results": job.get("results"),
            "error": job.get("error")
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Retry a failed annotation job"""
    
    if job_id not in annotation_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    job = annotation_jobs[job_id]
    
    # Check permissions
    if job["user_id"] != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied to this job"
        )
    
    # Only retry failed jobs
    if job["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is {job['status']}, cannot retry"
        )
    
    # Reset job status
    annotation_jobs[job_id]["status"] = "queued"
    annotation_jobs[job_id]["progress"] = 0.0
    annotation_jobs[job_id]["message"] = "Job queued for retry"
    annotation_jobs[job_id].pop("error", None)
    annotation_jobs[job_id].pop("results", None)
    
    return {
        "success": True,
        "data": {
            "job_id": job_id,
            "status": "queued",
            "message": "Job queued for retry"
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Cancel or delete an annotation job"""
    
    if job_id not in annotation_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
    
    job = annotation_jobs[job_id]
    
    # Check permissions
    if job["user_id"] != current_user["user_id"] and current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access denied to this job"
        )
    
    # Cancel or delete job
    if job["status"] in ["queued", "processing"]:
        annotation_jobs[job_id]["status"] = "cancelled"
        annotation_jobs[job_id]["message"] = "Job cancelled by user"
        message = "Job cancelled successfully"
    else:
        # Delete completed/failed jobs
        del annotation_jobs[job_id]
        message = "Job deleted successfully"
    
    return {
        "success": True,
        "data": {
            "message": message
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/")
async def list_jobs(
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """List annotation jobs for current user"""
    
    user_jobs = []
    
    for job_id, job in annotation_jobs.items():
        # Show user's jobs or all jobs for admin
        if job["user_id"] == current_user["user_id"] or current_user.get("role") == "admin":
            user_jobs.append({
                "job_id": job["job_id"],
                "status": job["status"],
                "progress": job["progress"],
                "message": job["message"],
                "created_at": job["created_at"],
                "case_uid": job.get("case_uid"),
                "user_id": job["user_id"] if current_user.get("role") == "admin" else None
            })
    
    # Sort by creation time (newest first)
    user_jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "success": True,
        "data": {
            "jobs": user_jobs,
            "total": len(user_jobs)
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }