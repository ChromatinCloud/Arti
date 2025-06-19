"""
Variants router - handles variant data retrieval
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional, List

from ..database import get_db, User, Job, Variant
from ..models import VariantResponse, VariantDetailResponse, VariantListResponse
from ..routers.auth import get_current_user

router = APIRouter()


@router.get("/job/{job_id}", response_model=VariantListResponse)
async def list_variants(
    job_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    gene: Optional[str] = None,
    tier: Optional[str] = None,
    min_af: Optional[float] = None,
    max_af: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List variants for a job with filtering"""
    
    # Verify job ownership
    job_result = await db.execute(
        select(Job).where(
            and_(
                Job.job_id == job_id,
                Job.user_id == current_user.id
            )
        )
    )
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    # Build query
    query = select(Variant).where(Variant.job_id == job.id)
    
    # Apply filters
    if gene:
        query = query.where(Variant.gene_symbol == gene)
    
    if tier:
        query = query.where(Variant.amp_tier == tier)
    
    if min_af is not None:
        query = query.where(Variant.gnomad_af >= min_af)
    
    if max_af is not None:
        query = query.where(Variant.gnomad_af <= max_af)
    
    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Get paginated results
    offset = (page - 1) * per_page
    query = query.order_by(
        Variant.amp_tier,
        Variant.confidence_score.desc()
    ).offset(offset).limit(per_page)
    
    result = await db.execute(query)
    variants = result.scalars().all()
    
    return {
        "variants": variants,
        "total": total,
        "page": page,
        "per_page": per_page,
        "filters": {
            "gene": gene,
            "tier": tier,
            "min_af": min_af,
            "max_af": max_af
        }
    }


@router.get("/{variant_id}", response_model=VariantDetailResponse)
async def get_variant(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed variant information"""
    
    # Get variant with job info
    result = await db.execute(
        select(Variant).join(Job).where(
            and_(
                Variant.id == variant_id,
                Job.user_id == current_user.id
            )
        )
    )
    variant = result.scalar_one_or_none()
    
    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )
    
    return variant


@router.get("/{variant_id}/igv")
async def get_igv_data(
    variant_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get variant data formatted for IGV.js"""
    
    # Get variant
    result = await db.execute(
        select(Variant).join(Job).where(
            and_(
                Variant.id == variant_id,
                Job.user_id == current_user.id
            )
        )
    )
    variant = result.scalar_one_or_none()
    
    if not variant:
        raise HTTPException(
            status_code=404,
            detail="Variant not found"
        )
    
    # Format for IGV.js
    igv_data = {
        "locus": f"{variant.chromosome}:{variant.position}",
        "reference": "hg38",
        "tracks": [
            {
                "name": "Variant",
                "type": "variant",
                "format": "vcf",
                "data": [{
                    "chr": variant.chromosome,
                    "pos": variant.position,
                    "ref": variant.reference,
                    "alt": variant.alternate,
                    "info": variant.annotations
                }]
            }
        ]
    }
    
    return igv_data