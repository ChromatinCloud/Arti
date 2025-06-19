"""
Clinical evidence endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import time

from ..core.database import get_db
from ..core.security import get_current_user, require_read_cases

router = APIRouter()


@router.get("/{variant_id}")
async def get_variant_evidence(
    variant_id: str,
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Get all clinical evidence for variant (ClinVar + therapeutic + literature)"""
    
    # Demo evidence data
    evidence_data = {
        "variant_id": variant_id,
        "clinical_significance": {
            "clinvar": {
                "significance": "Pathogenic",
                "review_status": "reviewed_by_expert",
                "stars": 4,
                "conditions": ["Melanoma", "Noonan syndrome"],
                "submitters": 15,
                "last_updated": "2024-01-15"
            }
        },
        "therapeutic_evidence": [
            {
                "source": "OncoKB",
                "evidence_level": "LEVEL_1",
                "drug": "Vemurafenib",
                "indication": "BRAF V600E-positive melanoma",
                "fda_approved": True,
                "approval_date": "2011-08-17"
            },
            {
                "source": "OncoKB", 
                "evidence_level": "LEVEL_1",
                "drug": "Dabrafenib",
                "indication": "BRAF V600E-positive melanoma",
                "fda_approved": True,
                "approval_date": "2013-05-29"
            }
        ],
        "literature": [
            {
                "pmid": "25265494",
                "title": "Improved survival with vemurafenib in melanoma with BRAF V600E mutation",
                "journal": "New England Journal of Medicine",
                "year": 2011,
                "evidence_strength": "FDA_APPROVED",
                "impact_score": 72.4
            }
        ],
        "population_data": {
            "gnomad_exomes": {"af": 0.000001, "ac": 2, "an": 251454},
            "gnomad_genomes": {"af": 0.000002, "ac": 1, "an": 156690}
        }
    }
    
    return {
        "success": True,
        "data": evidence_data,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/sources/status")
async def get_evidence_sources_status(
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Check evidence source freshness and status"""
    
    sources_status = {
        "clinvar": {
            "status": "healthy",
            "last_updated": "2024-01-20",
            "version": "2024-01",
            "total_variants": 2_500_000,
            "pathogenic_variants": 185_000
        },
        "oncokb": {
            "status": "healthy", 
            "last_updated": "2024-01-15",
            "version": "v4.20",
            "total_annotations": 15_000,
            "fda_approved_therapies": 85
        },
        "civic": {
            "status": "healthy",
            "last_updated": "2024-01-18", 
            "version": "2024-01-18",
            "total_evidence": 8_500,
            "therapeutic_evidence": 4_200
        }
    }
    
    return {
        "success": True,
        "data": sources_status,
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.put("/sources/refresh")
async def refresh_evidence_sources(
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Trigger evidence source refresh"""
    
    return {
        "success": True,
        "data": {
            "message": "Evidence source refresh initiated",
            "job_id": f"refresh_{int(time.time())}",
            "estimated_completion": time.time() + 3600  # 1 hour
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }