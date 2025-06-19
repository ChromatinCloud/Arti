"""
Pydantic models for API requests/responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# User models
class UserCreate(BaseModel):
    """User creation request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str


class UserResponse(BaseModel):
    """User response"""
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"


# Job models
class JobCreate(BaseModel):
    """Job creation request"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    cancer_type: Optional[str] = None
    case_uid: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = {}


class JobResponse(BaseModel):
    """Job response"""
    id: int
    job_id: str
    name: str
    description: Optional[str]
    status: JobStatus
    cancer_type: Optional[str]
    case_uid: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: int
    total_variants: Optional[int]
    current_step: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Job list response"""
    jobs: List[JobResponse]
    total: int
    page: int
    per_page: int


# Variant models
class VariantResponse(BaseModel):
    """Variant response"""
    id: int
    chromosome: str
    position: int
    reference: str
    alternate: str
    gene_symbol: Optional[str]
    transcript_id: Optional[str]
    hgvs_c: Optional[str]
    hgvs_p: Optional[str]
    consequence: Optional[str]
    amp_tier: Optional[str]
    vicc_tier: Optional[str]
    confidence_score: Optional[float]
    gnomad_af: Optional[float]
    gnomad_af_popmax: Optional[float]
    
    class Config:
        from_attributes = True


class VariantDetailResponse(VariantResponse):
    """Detailed variant response"""
    oncokb_evidence: Optional[Dict[str, Any]]
    civic_evidence: Optional[Dict[str, Any]]
    cosmic_evidence: Optional[Dict[str, Any]]
    annotations: Optional[Dict[str, Any]]


class VariantListResponse(BaseModel):
    """Variant list response"""
    variants: List[VariantResponse]
    total: int
    page: int
    per_page: int
    filters: Optional[Dict[str, Any]]


# WebSocket models
class ProgressUpdate(BaseModel):
    """Progress update message"""
    job_id: str
    status: JobStatus
    progress: int
    total_variants: Optional[int]
    current_step: Optional[str]
    message: Optional[str]


# Report models
class ReportFormat(str, Enum):
    """Report format enum"""
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    TSV = "tsv"


class ReportRequest(BaseModel):
    """Report generation request"""
    format: ReportFormat = ReportFormat.JSON
    include_evidence: bool = True
    include_canned_text: bool = True


class ReportResponse(BaseModel):
    """Report response"""
    job_id: str
    format: ReportFormat
    file_url: str
    file_size: int
    generated_at: datetime