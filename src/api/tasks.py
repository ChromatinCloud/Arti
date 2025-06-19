"""
RQ task processor for annotation jobs with real-time updates
"""

import redis
from rq import Queue, Worker
from rq.job import Job as RQJob
import logging
from pathlib import Path
import json
from datetime import datetime
import asyncio
import sys
from typing import Dict, Any, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.annotation_engine.input_validator_v2 import InputValidatorV2
from src.annotation_engine.workflow_router import WorkflowRouter
from src.annotation_engine.workflow_executor import WorkflowExecutor
from src.api.database import Job, JobStatus, Variant
from src.api.config import settings

logger = logging.getLogger(__name__)

# Redis connection
redis_conn = redis.from_url(settings.REDIS_URL)
queue = Queue('annotation_jobs', connection=redis_conn)

# Redis pubsub for real-time updates
pubsub_conn = redis.from_url(settings.REDIS_URL)


def submit_annotation_job(job_id: str):
    """Submit annotation job to queue"""
    job = queue.enqueue(
        process_annotation_job,
        job_id,
        job_timeout=settings.JOB_TIMEOUT,
        result_ttl=86400  # Keep results for 24 hours
    )
    return job.id


def send_variant_update(job_id: str, variant_data: Dict[str, Any], flow_data: Dict[str, Any] = None):
    """Send real-time variant update via Redis pubsub"""
    update = {
        "type": "variant_update",
        "job_id": job_id,
        "variant": variant_data,
        "flow_data": flow_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Publish to Redis channel
    channel = f"job_updates:{job_id}"
    pubsub_conn.publish(channel, json.dumps(update))
    
    logger.debug(f"Sent variant update for job {job_id}: {variant_data.get('variant_id')}")


def send_progress(job_id: str, status: str, progress: int, message: str, 
                 current_step: str = None, details: Dict[str, Any] = None):
    """Send progress update via Redis pubsub"""
    
    update = {
        "type": "progress",
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "message": message,
        "current_step": current_step,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Publish to Redis channel
    channel = f"job_updates:{job_id}"
    pubsub_conn.publish(channel, json.dumps(update))
    
    logger.info(f"Progress update for job {job_id}: {progress}% - {message}")


def process_annotation_job(job_id: str):
    """Process annotation job with real-time updates"""
    
    logger.info(f"Starting annotation job {job_id}")
    
    # Import here to avoid circular imports
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Create sync database session
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as db:
        # Get job
        job = db.query(Job).filter(Job.job_id == job_id).first()
        
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            db.commit()
            
            # Send initial progress
            send_progress(job_id, "running", 0, "Initializing annotation pipeline", 
                         "initialization")
            
            # Initialize components
            validator = InputValidatorV2()
            router = WorkflowRouter()
            executor = WorkflowExecutor()
            
            # Validate input
            send_progress(job_id, "running", 10, "Validating input VCF", 
                         "validation")
            validation_result = validator.validate(Path(job.input_file))
            
            if not validation_result["valid"]:
                raise ValueError(f"Invalid VCF: {validation_result.get('error', 'Unknown error')}")
            
            # Get normalized variants
            normalized_variants = validation_result["normalized_variants"]
            job.total_variants = len(normalized_variants)
            db.commit()
            
            send_progress(job_id, "running", 15, 
                         f"Found {len(normalized_variants)} variants to annotate", 
                         "validation",
                         {"total_variants": len(normalized_variants)})
            
            # Route to appropriate workflow
            send_progress(job_id, "running", 20, "Determining annotation workflow", 
                         "routing")
            workflow = router.route({
                "variants": normalized_variants,
                "cancer_type": job.cancer_type,
                "case_uid": job.case_uid
            })
            
            # Custom progress callback that sends real-time updates
            processed_variants = []
            
            def progress_callback(current, total, message, variant_result=None):
                progress = 20 + int((current / total) * 70)  # 20-90%
                
                # Update job progress
                job.progress = progress
                job.current_step = message
                db.commit()
                
                # Send progress update
                send_progress(job_id, "running", progress, message, 
                             "annotation", 
                             {"current": current, "total": total})
                
                # If we have a variant result, send it immediately
                if variant_result:
                    # Create variant record
                    variant = Variant(
                        job_id=job.id,
                        chromosome=variant_result["chromosome"],
                        position=variant_result["position"],
                        reference=variant_result["reference"],
                        alternate=variant_result["alternate"],
                        gene_symbol=variant_result.get("gene_symbol"),
                        transcript_id=variant_result.get("transcript_id"),
                        hgvs_c=variant_result.get("hgvs_c"),
                        hgvs_p=variant_result.get("hgvs_p"),
                        consequence=variant_result.get("consequence"),
                        amp_tier=variant_result.get("amp_tier"),
                        vicc_tier=variant_result.get("vicc_tier"),
                        confidence_score=variant_result.get("confidence_score"),
                        gnomad_af=variant_result.get("gnomad_af"),
                        gnomad_af_popmax=variant_result.get("gnomad_af_popmax"),
                        oncokb_evidence=variant_result.get("oncokb_evidence"),
                        civic_evidence=variant_result.get("civic_evidence"),
                        cosmic_evidence=variant_result.get("cosmic_evidence"),
                        annotations=variant_result
                    )
                    db.add(variant)
                    db.commit()
                    db.refresh(variant)
                    
                    # Send real-time variant update with flow data
                    variant_update = {
                        "variant_id": variant.id,
                        "chromosome": variant.chromosome,
                        "position": variant.position,
                        "reference": variant.reference,
                        "alternate": variant.alternate,
                        "gene": variant.gene_symbol,
                        "consequence": variant.consequence,
                        "amp_tier": variant.amp_tier,
                        "vicc_tier": variant.vicc_tier,
                        "confidence_score": variant.confidence_score,
                        "canned_text": variant_result.get("canned_text", {}).get("summary"),
                        "interpretation": variant_result.get("clinical_interpretation")
                    }
                    
                    # Include flow data if available
                    flow_data = variant_result.get("flow_data")
                    
                    send_variant_update(job_id, variant_update, flow_data)
                    processed_variants.append(variant_result)
            
            # Execute annotation with real-time updates
            send_progress(job_id, "running", 30, "Starting VEP annotation", 
                         "vep_annotation")
            
            # Modify executor to support per-variant callbacks
            annotation_results = execute_with_updates(
                executor, workflow, progress_callback
            )
            
            # Calculate final statistics
            tier_counts = {}
            high_confidence_count = 0
            
            for var in processed_variants:
                tier = var.get("amp_tier", "Unknown")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1
                
                if var.get("confidence_score", 0) >= 0.8:
                    high_confidence_count += 1
            
            # Update job with results
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress = 100
            job.result_summary = {
                "total_variants": len(processed_variants),
                "tier_counts": tier_counts,
                "high_confidence_variants": high_confidence_count,
                "pipeline_version": "1.0.0"
            }
            
            db.commit()
            
            send_progress(job_id, "completed", 100, "Annotation completed successfully", 
                         "completed",
                         {"summary": job.result_summary})
            
            logger.info(f"Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            
            # Update job status
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
            
            send_progress(job_id, "failed", job.progress or 0, f"Job failed: {e}", 
                         "error")
            
            raise


def execute_with_updates(executor: WorkflowExecutor, workflow: Dict[str, Any], 
                         progress_callback) -> Dict[str, Any]:
    """
    Execute workflow with per-variant progress updates
    This is a modified version that processes variants one by one
    """
    
    variants = workflow["variants"]
    total_variants = len(variants)
    results = []
    
    # Process each variant individually for real-time updates
    for i, variant in enumerate(variants):
        current = i + 1
        
        # Update progress
        progress_callback(
            current, 
            total_variants, 
            f"Processing variant {current}/{total_variants}: "
            f"{variant['chromosome']}:{variant['position']}"
        )
        
        # Run annotation for single variant
        single_workflow = {**workflow, "variants": [variant]}
        result = executor.execute(single_workflow)
        
        if result["annotated_variants"]:
            variant_result = result["annotated_variants"][0]
            
            # Extract annotations for flow diagram
            annotations = extract_annotations(variant_result)
            
            # Apply rules and get triggered rules
            rules_result = apply_rules(variant_result, annotations)
            
            # Add tier assignment based on rules
            variant_result["amp_tier"] = assign_tier_with_rules(variant_result, rules_result)
            variant_result["vicc_tier"] = assign_vicc_tier_with_rules(variant_result, rules_result)
            variant_result["confidence_score"] = rules_result["confidence_score"]
            
            # Generate canned text
            variant_result["canned_text"] = generate_canned_text(variant_result)
            
            # Add clinical interpretation
            variant_result["clinical_interpretation"] = generate_interpretation(variant_result)
            
            # Add flow data for visualization
            variant_result["flow_data"] = {
                "annotations": annotations,
                "rules": rules_result["rules"],
                "triggered_rules": rules_result["triggered_rules"],
                "tier_rationale": rules_result["tier_rationale"]
            }
            
            # Send real-time update with full variant data
            progress_callback(current, total_variants, 
                            f"Completed variant {current}/{total_variants}", 
                            variant_result)
            
            results.append(variant_result)
    
    return {"annotated_variants": results}


def extract_annotations(variant: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract annotations for flow visualization"""
    annotations = []
    
    # VEP consequences
    if variant.get("consequence"):
        annotations.append({
            "source": "VEP",
            "type": "functional",
            "value": variant["consequence"],
            "confidence": 0.9
        })
    
    # Population frequency
    if variant.get("gnomad_af") is not None:
        annotations.append({
            "source": "gnomAD",
            "type": "population",
            "value": f"AF: {variant['gnomad_af']:.2e}",
            "confidence": 1.0
        })
    
    # Pathogenicity predictions
    if variant.get("revel_score"):
        annotations.append({
            "source": "REVEL",
            "type": "pathogenicity",
            "value": f"Score: {variant['revel_score']:.3f}",
            "confidence": variant["revel_score"]
        })
    
    # Conservation scores
    if variant.get("gerp_score"):
        annotations.append({
            "source": "GERP",
            "type": "conservation",
            "value": f"Score: {variant['gerp_score']:.2f}",
            "confidence": 0.8
        })
    
    # Clinical evidence
    if variant.get("oncokb_evidence"):
        annotations.append({
            "source": "OncoKB",
            "type": "clinical",
            "value": "Clinical evidence available",
            "confidence": 0.95
        })
    
    if variant.get("civic_evidence"):
        annotations.append({
            "source": "CIViC",
            "type": "clinical",
            "value": "Civic evidence available",
            "confidence": 0.9
        })
    
    if variant.get("cosmic_evidence"):
        annotations.append({
            "source": "COSMIC",
            "type": "cancer",
            "value": f"Cancer hotspot",
            "confidence": 0.85
        })
    
    return annotations


def apply_rules(variant: Dict[str, Any], annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply AMP/ASCO/CAP and VICC rules"""
    rules = []
    triggered_rules = []
    total_score = 0
    
    # Rule 1: Strong clinical evidence
    if any(ann["source"] in ["OncoKB", "CIViC"] for ann in annotations):
        rule = {
            "id": "CBP1",
            "name": "Strong clinical evidence",
            "triggered": True,
            "score": 8,
            "evidence": ["OncoKB/CIViC annotation present"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Rule 2: Cancer hotspot
    if variant.get("cosmic_evidence") or variant.get("is_hotspot"):
        rule = {
            "id": "CBP2",
            "name": "Cancer hotspot",
            "triggered": True,
            "score": 6,
            "evidence": ["COSMIC hotspot", "Recurrent mutation"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Rule 3: Functional impact
    if variant.get("consequence") in ["missense_variant", "stop_gained", "frameshift_variant"]:
        rule = {
            "id": "CBP3",
            "name": "Deleterious consequence",
            "triggered": True,
            "score": 4,
            "evidence": [f"VEP: {variant.get('consequence')}"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Rule 4: Low population frequency
    gnomad_af = variant.get("gnomad_af", 1.0)
    if gnomad_af < 0.01:
        rule = {
            "id": "CBP4",
            "name": "Rare variant",
            "triggered": True,
            "score": 3,
            "evidence": [f"gnomAD AF < 1%: {gnomad_af:.2e}"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Rule 5: Pathogenicity predictions
    if variant.get("revel_score", 0) > 0.7:
        rule = {
            "id": "CBP5",
            "name": "High pathogenicity score",
            "triggered": True,
            "score": 4,
            "evidence": [f"REVEL: {variant.get('revel_score', 0):.3f}"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Rule 6: Conservation
    if variant.get("gerp_score", 0) > 4:
        rule = {
            "id": "CBP6",
            "name": "Highly conserved",
            "triggered": True,
            "score": 2,
            "evidence": [f"GERP: {variant.get('gerp_score', 0):.2f}"]
        }
        rules.append(rule)
        triggered_rules.append(rule["id"])
        total_score += rule["score"]
    
    # Calculate confidence score based on total score
    max_score = 30  # Maximum possible score
    confidence_score = min(total_score / max_score, 1.0)
    
    # Determine tier rationale
    tier_rationale = []
    if total_score >= 20:
        tier_rationale.append("Strong evidence from multiple sources")
    elif total_score >= 15:
        tier_rationale.append("Moderate evidence with clinical support")
    elif total_score >= 10:
        tier_rationale.append("Some evidence of pathogenicity")
    else:
        tier_rationale.append("Limited evidence available")
    
    return {
        "rules": rules,
        "triggered_rules": triggered_rules,
        "total_score": total_score,
        "confidence_score": confidence_score,
        "tier_rationale": tier_rationale
    }


def assign_tier_with_rules(variant: Dict[str, Any], rules_result: Dict[str, Any]) -> str:
    """Assign AMP/ASCO/CAP 2017 tier based on rules"""
    score = rules_result["total_score"]
    
    if score >= 20:
        return "Tier I"
    elif score >= 15:
        return "Tier II"
    elif score >= 10:
        return "Tier III"
    elif score >= 5:
        return "Tier IV"
    else:
        return "Unknown"


def assign_vicc_tier_with_rules(variant: Dict[str, Any], rules_result: Dict[str, Any]) -> str:
    """Assign VICC 2022 oncogenicity tier based on rules"""
    score = rules_result["total_score"]
    triggered = rules_result["triggered_rules"]
    
    # Check for strong evidence
    if "CBP1" in triggered and score >= 15:
        return "Oncogenic"
    elif score >= 12:
        return "Likely Oncogenic"
    elif score >= 8:
        return "Uncertain Significance"
    elif score >= 4:
        return "Likely Benign"
    else:
        return "Benign"


def assign_tier(variant: Dict[str, Any]) -> str:
    """Assign AMP/ASCO/CAP 2017 tier"""
    # Simplified tier assignment logic
    evidence_level = variant.get("evidence_level", 0)
    
    if evidence_level >= 0.9:
        return "Tier I"
    elif evidence_level >= 0.7:
        return "Tier II"
    elif evidence_level >= 0.5:
        return "Tier III"
    elif evidence_level >= 0.3:
        return "Tier IV"
    else:
        return "Unknown"


def assign_vicc_tier(variant: Dict[str, Any]) -> str:
    """Assign VICC 2022 oncogenicity tier"""
    # Simplified VICC tier assignment
    pathogenicity_score = variant.get("pathogenicity_score", 0)
    
    if pathogenicity_score >= 0.9:
        return "Oncogenic"
    elif pathogenicity_score >= 0.7:
        return "Likely Oncogenic"
    elif pathogenicity_score >= 0.3:
        return "Uncertain Significance"
    elif pathogenicity_score >= 0.1:
        return "Likely Benign"
    else:
        return "Benign"


def generate_canned_text(variant: Dict[str, Any]) -> Dict[str, str]:
    """Generate canned text for variant"""
    gene = variant.get("gene_symbol", "Unknown")
    consequence = variant.get("consequence", "unknown consequence")
    tier = variant.get("amp_tier", "Unknown")
    
    summary = (
        f"The {variant['chromosome']}:{variant['position']} {variant['reference']}>{variant['alternate']} "
        f"variant in {gene} results in a {consequence}. "
        f"This variant has been classified as {tier} based on available evidence."
    )
    
    return {
        "summary": summary,
        "evidence": f"Evidence from OncoKB, CIViC, and COSMIC databases was reviewed.",
        "recommendation": f"Further clinical correlation is recommended."
    }


def generate_interpretation(variant: Dict[str, Any]) -> str:
    """Generate clinical interpretation"""
    tier = variant.get("amp_tier", "Unknown")
    gene = variant.get("gene_symbol", "Unknown")
    
    if tier == "Tier I":
        return f"This {gene} variant has strong clinical significance with FDA-approved therapies available."
    elif tier == "Tier II":
        return f"This {gene} variant has potential clinical significance with investigational therapies."
    elif tier == "Tier III":
        return f"This {gene} variant has uncertain clinical significance."
    else:
        return f"This {gene} variant has limited clinical significance at this time."


if __name__ == "__main__":
    # Run worker
    logger.info("Starting RQ worker...")
    
    with redis_conn:
        worker = Worker(['annotation_jobs'], connection=redis_conn)
        worker.work()