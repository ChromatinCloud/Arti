"""
Script to integrate technical comments into the Phase 3A database

This demonstrates how technical comments work with the existing schema:
1. Technical comment templates are stored in the database
2. Comments are applied during variant analysis
3. They integrate with the text template system
4. Full audit trail is maintained
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from annotation_engine.db.base import Base, get_engine, get_session
from annotation_engine.db.models import (
    Patient, Case, VariantAnalysis, Variant, 
    TieringResult, VariantInterpretation
)
from annotation_engine.db.expanded_models import (
    TextTemplate, GeneratedText, TextTemplateType
)
from annotation_engine.db.technical_comments_integration import (
    TechnicalCommentTemplate, VariantTechnicalComment,
    ChallengingRegion, populate_technical_comments,
    apply_technical_comments
)


def demonstrate_technical_comments_integration():
    """Show how technical comments integrate with Phase 3A database"""
    
    # Get database session
    session = get_session()
    
    print("=== Phase 3A Technical Comments Integration Demo ===\n")
    
    # 1. Create or update technical comment templates in database
    print("1. Loading technical comment templates into database...")
    populate_technical_comments(session)
    
    # Query and display loaded templates
    templates = session.query(TechnicalCommentTemplate).all()
    print(f"   Loaded {len(templates)} technical comment templates:")
    for template in templates[:5]:  # Show first 5
        print(f"   - {template.comment_id}: {template.technical_term} ({template.severity})")
    print("   ...\n")
    
    # 2. Create a sample case and variant for demonstration
    print("2. Creating sample case and variant...")
    
    # Create patient
    patient = Patient(patient_uid="DEMO_PT_001")
    session.add(patient)
    
    # Create case
    case = Case(
        case_uid="DEMO_CASE_001",
        patient_uid="DEMO_PT_001",
        tissue="FFPE",
        diagnosis="Melanoma",
        oncotree_id="SKCM"
    )
    session.add(case)
    
    # Create analysis
    analysis = VariantAnalysis(
        case_uid="DEMO_CASE_001",
        vcf_file_path="demo.vcf",
        total_variants_input=1000,
        variants_passing_qc=487
    )
    session.add(analysis)
    session.flush()  # Get analysis_id
    
    # Create variant in challenging region
    variant = Variant(
        variant_id="chr7:140453136:A>T",  # BRAF V600E
        analysis_id=analysis.analysis_id,
        chromosome="chr7",
        position=140453136,
        reference_allele="A",
        alternate_allele="T",
        variant_type="SNV",
        gene_symbol="BRAF",
        hgvsc="c.1799T>A",
        hgvsp="p.V600E",
        consequence="missense_variant",
        vaf=0.08,  # Low VAF
        total_depth=15,  # Low coverage
        transcript_id="ENST00000288602"
    )
    session.add(variant)
    session.commit()
    
    print(f"   Created case {case.case_uid} with BRAF V600E variant\n")
    
    # 3. Apply technical comments based on variant context
    print("3. Applying technical comments to variant...")
    
    # Define genomic context that will trigger multiple comments
    genomic_context = {
        # Will trigger TC001 (Coverage dropout)
        'mean_coverage': 15,
        'fraction_low_coverage': 0.35,
        
        # Will trigger TC010 (FFPE artifact)
        'specimen_type': 'FFPE',
        'variant_type': 'T>A',  # Reverse complement of C>T
        'vaf': 0.08,
        
        # Additional context
        'gene': 'BRAF',
        'exon': 15,
        'gc_content': 0.45,
        'mappability': 0.95
    }
    
    applied_comments = apply_technical_comments(
        session,
        variant_id=variant.variant_id,
        analysis_id=analysis.analysis_id,
        genomic_context=genomic_context
    )
    
    print(f"   Applied {len(applied_comments)} technical comments:")
    for comment in applied_comments:
        print(f"   - {comment}")
    print()
    
    # 4. Query and display applied comments
    print("4. Retrieving applied technical comments...")
    
    variant_comments = session.query(VariantTechnicalComment).filter_by(
        variant_id=variant.variant_id
    ).all()
    
    for vc in variant_comments:
        print(f"   Comment: {vc.template.technical_term}")
        print(f"   Severity: {vc.template.severity}")
        print(f"   Text: {vc.applied_comment[:200]}...")
        print(f"   Trigger values: {json.dumps(vc.trigger_values, indent=2)}")
        print()
    
    # 5. Create a challenging region entry for OncoSeq
    print("5. Adding challenging region for OncoSeq assay...")
    
    challenging_region = ChallengingRegion(
        chromosome="chr7",
        start_pos=140453100,
        end_pos=140453200,
        region_name="BRAF_V600_region",
        gene="BRAF",
        challenge_type="Coverage_Dropout",
        assay_name="oncoseq",
        challenge_description="BRAF V600 hotspot region shows consistent coverage dropout in OncoSeq v7",
        severity="medium",
        evidence_basis="Analysis of 100+ OncoSeq runs showed <20X coverage in 35% of samples",
        failure_rate={"<20X": 0.35, "<10X": 0.15},
        avg_coverage={"mean": 18.5, "median": 15, "std": 8.2}
    )
    session.add(challenging_region)
    session.commit()
    
    print(f"   Added challenging region: {challenging_region.region_name}\n")
    
    # 6. Integrate with text template system
    print("6. Integrating with text template system...")
    
    # Create a text template that includes technical comments
    tech_aware_template = TextTemplate(
        template_name="Variant Interpretation with Technical Caveats",
        template_type=TextTemplateType.VARIANT_DX_INTERPRETATION,
        version="1.0",
        template_content="""
{variant_description}

Clinical Significance: {clinical_significance}

{interpretation_text}

Technical Considerations:
{technical_comments}

Recommendation: {recommendation}
        """.strip(),
        required_fields=["variant_description", "clinical_significance", 
                        "interpretation_text", "technical_comments", "recommendation"],
        confidence_factors={"technical_comments": -0.1}  # Technical issues reduce confidence
    )
    session.add(tech_aware_template)
    session.flush()
    
    # Generate text with technical comments
    technical_comments_text = "\n".join([
        f"• {vc.applied_comment}" for vc in variant_comments
    ])
    
    generated = GeneratedText(
        variant_id=variant.variant_id,
        case_uid=case.case_uid,
        template_id=tech_aware_template.template_id,
        text_type=TextTemplateType.VARIANT_DX_INTERPRETATION,
        generated_content=f"""
BRAF p.V600E (c.1799T>A) missense variant

Clinical Significance: Pathogenic (Tier I-A)

The BRAF V600E mutation is a well-characterized oncogenic driver mutation found in approximately 
50% of melanomas. This mutation results in constitutive activation of the MAPK signaling pathway, 
leading to increased cell proliferation and survival.

Technical Considerations:
{technical_comments_text}

Recommendation: Despite technical limitations, the detection of BRAF V600E at 8% VAF warrants 
consideration for BRAF inhibitor therapy (vemurafenib, dabrafenib) in combination with MEK 
inhibitors. Orthogonal validation by an alternative method is recommended given the low coverage.
        """.strip(),
        generation_method="template",
        confidence_score=0.75,  # Reduced due to technical issues
        evidence_completeness=0.90
    )
    session.add(generated)
    session.commit()
    
    print("   Created interpretation with integrated technical comments")
    print(f"   Confidence score: {generated.confidence_score} (reduced due to technical issues)\n")
    
    # 7. Create final interpretation
    print("7. Creating final clinical interpretation...")
    
    interpretation = VariantInterpretation(
        variant_id=variant.variant_id,
        case_uid=case.case_uid,
        guideline_framework="AMP_ACMG",
        tier="I-A",
        template_id="BRAF_V600E_melanoma",
        custom_interpretation=generated.generated_content,
        clinical_significance="Pathogenic",
        therapeutic_implications="BRAF/MEK inhibitor therapy indicated",
        confidence_level="MEDIUM",  # Reduced from HIGH due to technical issues
        interpreter_notes="Technical limitations noted: low coverage and possible FFPE artifact. Recommend orthogonal validation.",
        created_by="demo_user"
    )
    session.add(interpretation)
    session.commit()
    
    print("   Created clinical interpretation with technical caveats")
    print(f"   Tier: {interpretation.tier}")
    print(f"   Confidence: {interpretation.confidence_level}")
    print(f"   Notes: {interpretation.interpreter_notes}\n")
    
    # 8. Show database relationships
    print("8. Database relationships summary:")
    print(f"   Patient ({patient.patient_uid})")
    print(f"   └── Case ({case.case_uid})")
    print(f"       └── Analysis ({analysis.analysis_id})")
    print(f"           └── Variant ({variant.variant_id})")
    print(f"               ├── Technical Comments ({len(variant_comments)})")
    print(f"               ├── Generated Text (with technical caveats)")
    print(f"               └── Clinical Interpretation (confidence adjusted)")
    
    print("\n=== Integration Complete ===")
    print("\nKey Points:")
    print("1. Technical comments are stored in the database, not files")
    print("2. They are automatically applied based on genomic context")
    print("3. They integrate with the text template system")
    print("4. They affect confidence scores and clinical recommendations")
    print("5. Full audit trail is maintained for regulatory compliance")
    
    # Cleanup
    session.close()


if __name__ == "__main__":
    # Ensure database exists
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Run demonstration
    demonstrate_technical_comments_integration()