"""
Test Migration Helpers

Utilities to help migrate old-style tests to the new dependency injection pattern.
"""

from typing import List, Dict, Any, Optional
from .models import Evidence, EvidenceStrength
from .test_mocks import create_test_variant_annotation


def migrate_old_evidence_to_new(old_evidence_dict: Dict[str, Any]) -> Evidence:
    """
    Convert old Evidence format to new Evidence model
    
    Old format had fields like 'strength', 'supporting_studies', etc.
    New format requires 'score', 'source_kb', etc.
    """
    
    # Map old strength values to new enum values
    strength_mapping = {
        "VERY_STRONG": EvidenceStrength.FDA_APPROVED,
        "STRONG": EvidenceStrength.EXPERT_CONSENSUS,
        "MODERATE": EvidenceStrength.MULTIPLE_SMALL_STUDIES,
        "SUPPORTING": EvidenceStrength.CASE_REPORTS,
        "WEAK": EvidenceStrength.PRECLINICAL
    }
    
    # Extract old fields
    code = old_evidence_dict.get("code", "UNKNOWN")
    description = old_evidence_dict.get("description", "Migrated evidence")
    old_score = old_evidence_dict.get("score", 2)
    confidence = old_evidence_dict.get("confidence", 0.8)
    old_strength = old_evidence_dict.get("strength")
    supporting_studies = old_evidence_dict.get("supporting_studies", [])
    
    # Determine guideline from code
    if "ONCOKB" in code:
        guideline = "OncoKB"
        source_kb = "OncoKB"
    elif "HOTSPOT" in code:
        guideline = "VICC_2022"
        source_kb = "COSMIC"
    elif "ClinVar" in code:
        guideline = "AMP_2017"
        source_kb = "ClinVar"
    else:
        guideline = "AMP_2017"
        source_kb = "CIViC"
    
    # Build data field with old information
    data = {
        "supporting_studies": supporting_studies,
        "original_fields": old_evidence_dict
    }
    
    if old_strength:
        if isinstance(old_strength, str):
            data["strength"] = old_strength
        else:
            data["strength"] = old_strength.value if hasattr(old_strength, 'value') else str(old_strength)
    
    return Evidence(
        code=code,
        score=old_score,
        guideline=guideline,
        source_kb=source_kb,
        description=description,
        data=data,
        confidence=confidence
    )


def create_tier_i_oncogene_evidence() -> List[Evidence]:
    """Create evidence for Tier I oncogene hotspot (like BRAF V600E)"""
    return [
        Evidence(
            code="OP3_ONCOKB_1",
            score=8,
            guideline="OncoKB",
            source_kb="OncoKB",
            description="OncoKB Level 1 - FDA-recognized biomarker for melanoma therapy",
            data={
                "strength": "FDA_APPROVED",
                "supporting_studies": ["Flaherty et al. 2010", "Hauschild et al. 2012"],
                "therapeutic_context": True
            },
            confidence=1.0
        ),
        Evidence(
            code="OP4_HOTSPOT_RECURRENT",
            score=4,
            guideline="VICC_2022",
            source_kb="COSMIC",
            description="Recurrent hotspot in 15% of melanomas with therapeutic implications",
            data={
                "strength": "STRONG",
                "supporting_studies": ["COSMIC Hotspots", "TCGA"],
                "hotspot_recurrence": 0.15
            },
            confidence=0.9
        ),
        Evidence(
            code="OS3",
            score=4,
            guideline="VICC_2022",
            source_kb="CIViC",
            description="Well-established cancer hotspot with therapeutic implications",
            data={
                "strength": "STRONG",
                "therapeutic_context": True
            },
            confidence=0.9
        )
    ]


def create_tier_iii_vus_evidence() -> List[Evidence]:
    """Create evidence for Tier III VUS variant"""
    return [
        Evidence(
            code="OM4",
            score=2,
            guideline="VICC_2022",
            source_kb="CIViC",
            description="Moderate evidence - variant in oncogenic gene but uncertain significance",
            data={
                "strength": "MODERATE",
                "supporting_studies": ["Limited case reports"]
            },
            confidence=0.6
        ),
        Evidence(
            code="PP3",
            score=1,
            guideline="AMP_2017",
            source_kb="ClinVar",
            description="Multiple lines of computational evidence support pathogenic impact",
            data={
                "strength": "SUPPORTING",
                "computational_predictions": ["REVEL: 0.7", "AlphaMissense: 0.8"]
            },
            confidence=0.5
        )
    ]


def create_tier_iv_benign_evidence() -> List[Evidence]:
    """Create evidence for Tier IV benign variant"""
    return [
        Evidence(
            code="BA1",
            score=-8,
            guideline="AMP_2017",
            source_kb="gnomAD",
            description="High population frequency - benign variant",
            data={
                "strength": "VERY_STRONG",
                "population_frequency": 0.05,
                "supporting_studies": ["gnomAD v3.1"]
            },
            confidence=0.95
        ),
        Evidence(
            code="BP4",
            score=-1,
            guideline="AMP_2017",
            source_kb="ClinVar",
            description="Multiple computational algorithms predict benign impact",
            data={
                "strength": "SUPPORTING",
                "computational_predictions": ["REVEL: 0.1", "SIFT: tolerated"]
            },
            confidence=0.7
        )
    ]


def create_tumor_suppressor_evidence() -> List[Evidence]:
    """Create evidence for tumor suppressor truncating variant"""
    return [
        Evidence(
            code="OVS1",
            score=8,
            guideline="VICC_2022",
            source_kb="CIViC",
            description="Null variant in tumor suppressor gene - very strong oncogenic evidence",
            data={
                "strength": "VERY_STRONG",
                "variant_type": "truncating",
                "gene_role": "tumor_suppressor"
            },
            confidence=0.95
        ),
        Evidence(
            code="PVS1",
            score=8,
            guideline="AMP_2017",
            source_kb="ClinVar",
            description="Loss-of-function variant in gene where LOF is known mechanism",
            data={
                "strength": "VERY_STRONG",
                "mechanism": "loss_of_function"
            },
            confidence=0.9
        )
    ]


def create_braf_v600e_variant() -> 'VariantAnnotation':
    """Create BRAF V600E variant annotation for testing"""
    from .test_mocks import create_test_variant_annotation
    
    variant = create_test_variant_annotation()
    variant.gene_symbol = "BRAF"
    variant.hgvs_p = "p.Val600Glu"
    variant.position = 140753336
    variant.is_oncogene = True
    variant.cancer_gene_census = True
    
    return variant


def create_tp53_truncating_variant() -> 'VariantAnnotation':
    """Create TP53 truncating variant for testing"""
    from .test_mocks import create_test_variant_annotation
    
    variant = create_test_variant_annotation()
    variant.chromosome = "17"
    variant.position = 7674220
    variant.reference = "G"
    variant.alternate = "T"
    variant.gene_symbol = "TP53"
    variant.hgvs_p = "p.Arg248Ter"
    variant.consequence = ["stop_gained"]
    variant.is_tumor_suppressor = True
    variant.cancer_gene_census = True
    
    return variant