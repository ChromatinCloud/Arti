"""
Clinical case management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import uuid

from ..core.database import get_db
from ..core.security import get_current_user, require_read_cases, require_write_interpretations

router = APIRouter()


class CaseRequest(BaseModel):
    """Request model for creating/updating cases"""
    patient_id: str
    cancer_type: str
    analysis_type: str = "tumor_only"
    tumor_sample_id: Optional[str] = None
    normal_sample_id: Optional[str] = None
    clinical_notes: Optional[str] = None


class CaseResponse(BaseModel):
    """Response model for case data"""
    case_uid: str
    patient_id: str
    cancer_type: str
    analysis_type: str
    status: str
    created_at: float
    updated_at: float


# In-memory case storage (in production, use database)
clinical_cases = {
    "CASE_001": {
        "case_uid": "CASE_001",
        "patient_id": "PATIENT_001",
        "cancer_type": "melanoma",
        "analysis_type": "tumor_only",
        "status": "in_progress",
        "created_at": time.time() - 86400,  # 1 day ago
        "updated_at": time.time() - 3600,   # 1 hour ago
        "created_by": "demo_user",
        "variants": [
            {
                "variant_id": "7:140753336:A>T",
                "gene": "BRAF",
                "hgvs_p": "p.Val600Glu",
                "tier": "Tier IA",
                "interpretation_status": "approved"
            }
        ],
        "summary": {
            "total_variants": 45,
            "annotated_variants": 45,
            "tier_distribution": {
                "Tier IA": 2,
                "Tier IB": 1,
                "Tier IIC": 5,
                "Tier III": 25,
                "Tier IV": 12
            },
            "actionable_variants": 3
        }
    }
}


@router.get("/")
async def list_cases(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    cancer_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """List clinical cases with filtering and pagination"""
    
    # Filter cases based on permissions
    filtered_cases = []
    
    for case_uid, case in clinical_cases.items():
        # Users can see their own cases, admins can see all
        if (case["created_by"] == current_user["user_id"] or 
            current_user.get("role") in ["admin", "clinician"]):
            
            # Apply filters
            if cancer_type and case["cancer_type"] != cancer_type:
                continue
            if status and case["status"] != status:
                continue
                
            filtered_cases.append(case)
    
    # Sort by updated_at (newest first)
    filtered_cases.sort(key=lambda x: x["updated_at"], reverse=True)
    
    # Pagination
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_cases = filtered_cases[start_idx:end_idx]
    
    return {
        "success": True,
        "data": {
            "cases": paginated_cases,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(filtered_cases),
                "pages": (len(filtered_cases) + limit - 1) // limit
            }
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/")
async def create_case(
    case_request: CaseRequest,
    current_user: Dict[str, Any] = Depends(require_write_interpretations),
    db: Session = Depends(get_db)
):
    """Create new clinical case"""
    
    case_uid = f"CASE_{str(uuid.uuid4())[:8].upper()}"
    
    new_case = {
        "case_uid": case_uid,
        "patient_id": case_request.patient_id,
        "cancer_type": case_request.cancer_type,
        "analysis_type": case_request.analysis_type,
        "tumor_sample_id": case_request.tumor_sample_id,
        "normal_sample_id": case_request.normal_sample_id,
        "clinical_notes": case_request.clinical_notes,
        "status": "created",
        "created_at": time.time(),
        "updated_at": time.time(),
        "created_by": current_user["user_id"],
        "variants": [],
        "summary": {
            "total_variants": 0,
            "annotated_variants": 0,
            "tier_distribution": {},
            "actionable_variants": 0
        }
    }
    
    clinical_cases[case_uid] = new_case
    
    return {
        "success": True,
        "data": new_case,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/{case_uid}")
async def get_case_details(
    case_uid: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Get complete case details including all variants and interpretations"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    return {
        "success": True,
        "data": case,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.put("/{case_uid}")
async def update_case(
    case_uid: str,
    case_request: CaseRequest,
    current_user: Dict[str, Any] = Depends(require_write_interpretations),
    db: Session = Depends(get_db)
):
    """Update case information"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    # Update case fields
    case.update({
        "patient_id": case_request.patient_id,
        "cancer_type": case_request.cancer_type,
        "analysis_type": case_request.analysis_type,
        "tumor_sample_id": case_request.tumor_sample_id,
        "normal_sample_id": case_request.normal_sample_id,
        "clinical_notes": case_request.clinical_notes,
        "updated_at": time.time(),
        "updated_by": current_user["user_id"]
    })
    
    return {
        "success": True,
        "data": case,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/{case_uid}/variants")
async def get_case_variants(
    case_uid: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Get all variants for a case"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    return {
        "success": True,
        "data": {
            "case_uid": case_uid,
            "variants": case["variants"],
            "summary": case["summary"]
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/{case_uid}/summary")
async def get_case_summary(
    case_uid: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Get case summary with tier distribution"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    return {
        "success": True,
        "data": {
            "case_uid": case_uid,
            "patient_id": case["patient_id"],
            "cancer_type": case["cancer_type"],
            "analysis_type": case["analysis_type"],
            "status": case["status"],
            "summary": case["summary"],
            "last_updated": case["updated_at"]
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/{case_uid}/report")
async def generate_case_report(
    case_uid: str,
    format: str = Query("json", regex="^(json|pdf)$"),
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Generate clinical report for case"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    # Generate report (in production, would create actual PDF)
    report_data = {
        "report_id": f"RPT_{case_uid}_{int(time.time())}",
        "case_uid": case_uid,
        "patient_id": case["patient_id"],
        "cancer_type": case["cancer_type"],
        "analysis_type": case["analysis_type"],
        "generated_at": time.time(),
        "generated_by": current_user["user_id"],
        "variants": case["variants"],
        "summary": case["summary"],
        "clinical_recommendations": [
            "BRAF V600E mutation detected - consider targeted therapy",
            "Vemurafenib, Dabrafenib, or combination therapy recommended",
            "Monitor for resistance mutations"
        ]
    }
    
    if format == "pdf":
        # In production, generate actual PDF
        report_data["pdf_url"] = f"/reports/{report_data['report_id']}.pdf"
    
    return {
        "success": True,
        "data": report_data,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.post("/{case_uid}/finalize")
async def finalize_case(
    case_uid: str,
    current_user: Dict[str, Any] = Depends(require_write_interpretations),
    db: Session = Depends(get_db)
):
    """Finalize case for clinical use (sign-off)"""
    
    if case_uid not in clinical_cases:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_uid} not found"
        )
    
    case = clinical_cases[case_uid]
    
    # Check permissions
    if (case["created_by"] != current_user["user_id"] and 
        current_user.get("role") not in ["admin", "clinician"]):
        raise HTTPException(
            status_code=403,
            detail="Access denied to this case"
        )
    
    # Finalize case
    case["status"] = "finalized"
    case["finalized_at"] = time.time()
    case["finalized_by"] = current_user["user_id"]
    case["updated_at"] = time.time()
    
    return {
        "success": True,
        "data": {
            "case_uid": case_uid,
            "status": "finalized",
            "finalized_at": case["finalized_at"],
            "finalized_by": current_user["user_id"]
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }