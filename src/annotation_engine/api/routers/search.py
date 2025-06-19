"""
Search and discovery endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import time

from ..core.database import get_db
from ..core.security import get_current_user, require_read_cases

router = APIRouter()


@router.get("/variants")
async def search_variants(
    q: str = Query(..., description="Search query (gene, position, HGVS)"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Search variants by gene, position, or HGVS notation"""
    
    # Demo search results
    search_results = []
    
    if "BRAF" in q.upper():
        search_results.append({
            "variant_id": "7:140753336:A>T",
            "gene": "BRAF",
            "hgvs_p": "p.Val600Glu",
            "consequence": "missense_variant",
            "tier": "Tier IA",
            "clinical_significance": "Pathogenic",
            "match_type": "gene"
        })
    
    if "V600E" in q.upper():
        search_results.append({
            "variant_id": "7:140753336:A>T", 
            "gene": "BRAF",
            "hgvs_p": "p.Val600Glu",
            "consequence": "missense_variant",
            "tier": "Tier IA",
            "clinical_significance": "Pathogenic",
            "match_type": "protein_change"
        })
    
    return {
        "success": True,
        "data": {
            "query": q,
            "results": search_results[:limit],
            "total": len(search_results)
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/cases")
async def search_cases(
    q: str = Query(..., description="Search query"),
    cancer_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Search cases by patient, date, cancer type"""
    
    # Demo search results
    search_results = [
        {
            "case_uid": "CASE_001",
            "patient_id": "PATIENT_001",
            "cancer_type": "melanoma",
            "status": "in_progress",
            "created_at": time.time() - 86400,
            "match_type": "case_id"
        }
    ]
    
    return {
        "success": True,
        "data": {
            "query": q,
            "results": search_results[:limit],
            "total": len(search_results)
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }


@router.get("/global")
async def global_search(
    q: str = Query(..., description="Global search query"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types"),
    limit: int = Query(20, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(require_read_cases),
    db: Session = Depends(get_db)
):
    """Global search across all data types"""
    
    # Demo global search results
    search_results = [
        {
            "entity_type": "variant",
            "entity_id": "7:140753336:A>T",
            "title": "BRAF p.Val600Glu",
            "description": "Pathogenic missense variant in BRAF gene",
            "match_score": 0.95
        },
        {
            "entity_type": "case", 
            "entity_id": "CASE_001",
            "title": "Melanoma Case CASE_001",
            "description": "Tumor-only analysis with BRAF V600E mutation",
            "match_score": 0.85
        }
    ]
    
    return {
        "success": True,
        "data": {
            "query": q,
            "results": search_results[:limit],
            "total": len(search_results)
        },
        "meta": {
            "timestamp": time.time(),
            "version": "1.0.0"
        }
    }