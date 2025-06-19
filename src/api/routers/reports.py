"""
Reports router - handles report generation
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pathlib import Path
import json
from datetime import datetime

from ..database import get_db, User, Job, Variant
from ..models import ReportRequest, ReportResponse, ReportFormat
from ..routers.auth import get_current_user
from ..config import settings

router = APIRouter()


@router.post("/{job_id}", response_model=ReportResponse)
async def generate_report(
    job_id: str,
    report_request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate report for completed job"""
    
    # Get job
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
    
    if job.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Job must be completed to generate report"
        )
    
    # Get all variants
    variant_result = await db.execute(
        select(Variant).where(Variant.job_id == job.id)
        .order_by(Variant.amp_tier, Variant.confidence_score.desc())
    )
    variants = variant_result.scalars().all()
    
    # Generate report based on format
    report_dir = Path(settings.RESULTS_DIR) / job_id
    report_dir.mkdir(parents=True, exist_ok=True)
    
    if report_request.format == ReportFormat.JSON:
        report_path = report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_data = {
            "job": {
                "id": job.job_id,
                "name": job.name,
                "cancer_type": job.cancer_type,
                "case_uid": job.case_uid,
                "created_at": job.created_at.isoformat(),
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            },
            "summary": {
                "total_variants": len(variants),
                "tier_counts": {},
                "high_confidence_variants": 0
            },
            "variants": []
        }
        
        # Count tiers
        tier_counts = {}
        high_confidence_count = 0
        
        for variant in variants:
            tier = variant.amp_tier or "Unknown"
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
            
            if variant.confidence_score and variant.confidence_score >= 0.8:
                high_confidence_count += 1
            
            variant_data = {
                "chromosome": variant.chromosome,
                "position": variant.position,
                "reference": variant.reference,
                "alternate": variant.alternate,
                "gene": variant.gene_symbol,
                "consequence": variant.consequence,
                "hgvs_c": variant.hgvs_c,
                "hgvs_p": variant.hgvs_p,
                "amp_tier": variant.amp_tier,
                "vicc_tier": variant.vicc_tier,
                "confidence_score": variant.confidence_score,
                "gnomad_af": variant.gnomad_af
            }
            
            if report_request.include_evidence:
                variant_data["evidence"] = {
                    "oncokb": variant.oncokb_evidence,
                    "civic": variant.civic_evidence,
                    "cosmic": variant.cosmic_evidence
                }
            
            if report_request.include_canned_text and variant.annotations:
                # TODO: Generate canned text from annotations
                variant_data["interpretation"] = variant.annotations.get("canned_text", "")
            
            report_data["variants"].append(variant_data)
        
        report_data["summary"]["tier_counts"] = tier_counts
        report_data["summary"]["high_confidence_variants"] = high_confidence_count
        
        # Write report
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
    elif report_request.format == ReportFormat.TSV:
        report_path = report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv"
        
        # Create TSV report
        headers = [
            "Chromosome", "Position", "Reference", "Alternate",
            "Gene", "Consequence", "HGVS_c", "HGVS_p",
            "AMP_Tier", "VICC_Tier", "Confidence_Score",
            "gnomAD_AF", "OncoKB", "CIViC", "COSMIC"
        ]
        
        with open(report_path, 'w') as f:
            f.write('\t'.join(headers) + '\n')
            
            for variant in variants:
                row = [
                    variant.chromosome,
                    str(variant.position),
                    variant.reference,
                    variant.alternate,
                    variant.gene_symbol or "",
                    variant.consequence or "",
                    variant.hgvs_c or "",
                    variant.hgvs_p or "",
                    variant.amp_tier or "",
                    variant.vicc_tier or "",
                    str(variant.confidence_score) if variant.confidence_score else "",
                    str(variant.gnomad_af) if variant.gnomad_af else "",
                    "Yes" if variant.oncokb_evidence else "No",
                    "Yes" if variant.civic_evidence else "No",
                    "Yes" if variant.cosmic_evidence else "No"
                ]
                f.write('\t'.join(row) + '\n')
    
    else:
        raise HTTPException(
            status_code=501,
            detail=f"Report format {report_request.format} not implemented yet"
        )
    
    # Return report info
    file_size = report_path.stat().st_size
    
    return {
        "job_id": job_id,
        "format": report_request.format,
        "file_url": f"/api/reports/download/{job_id}/{report_path.name}",
        "file_size": file_size,
        "generated_at": datetime.now()
    }


@router.get("/download/{job_id}/{filename}")
async def download_report(
    job_id: str,
    filename: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Download generated report"""
    
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
    
    # Check file exists
    file_path = Path(settings.RESULTS_DIR) / job_id / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report file not found"
        )
    
    # Return file
    return FileResponse(
        file_path,
        media_type='application/octet-stream',
        filename=filename
    )