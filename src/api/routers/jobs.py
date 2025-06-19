"""
Jobs router - handles annotation job management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
import uuid
import aiofiles
from pathlib import Path

from ..database import get_db, User, Job, JobStatus
from ..models import JobCreate, JobResponse, JobListResponse
from ..routers.auth import get_current_user
from ..config import settings
from ..tasks import submit_annotation_job

router = APIRouter()


@router.post("/create", response_model=JobResponse)
async def create_job(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    cancer_type: Optional[str] = Form(None),
    case_uid: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new annotation job"""
    
    # Validate file
    if not file.filename.endswith(('.vcf', '.vcf.gz')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only VCF files are supported"
        )
    
    # Check file size
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        )
    
    # Check user job limit
    result = await db.execute(
        select(Job).where(
            and_(
                Job.user_id == current_user.id,
                Job.status.in_([JobStatus.PENDING, JobStatus.RUNNING])
            )
        )
    )
    active_jobs = len(result.scalars().all())
    
    if active_jobs >= settings.MAX_JOBS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum {settings.MAX_JOBS_PER_USER} active jobs allowed"
        )
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = Path(settings.UPLOAD_DIR) / f"{job_id}.vcf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(upload_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Create job record
    job = Job(
        job_id=job_id,
        user_id=current_user.id,
        name=name,
        description=description,
        cancer_type=cancer_type,
        case_uid=case_uid,
        input_file=str(upload_path),
        status=JobStatus.PENDING
    )
    
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Submit to job queue
    submit_annotation_job(job_id)
    
    return job


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    per_page: int = 20,
    status: Optional[JobStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List user's jobs"""
    
    # Build query
    query = select(Job).where(Job.user_id == current_user.id)
    
    if status:
        query = query.where(Job.status == status)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = query.order_by(Job.created_at.desc()).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    
    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get job details"""
    
    result = await db.execute(
        select(Job).where(
            and_(
                Job.job_id == job_id,
                Job.user_id == current_user.id
            )
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a job"""
    
    result = await db.execute(
        select(Job).where(
            and_(
                Job.job_id == job_id,
                Job.user_id == current_user.id
            )
        )
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending or running jobs"
        )
    
    # Update job status
    job.status = JobStatus.CANCELLED
    await db.commit()
    
    # TODO: Cancel RQ job
    
    return {"message": "Job cancelled successfully"}