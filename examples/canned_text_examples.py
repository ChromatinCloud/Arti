"""
Comprehensive Examples of All 8 Canned Text Types

This module demonstrates the generation of all 8 types of canned text
for various clinical scenarios.
"""

from typing import List, Dict, Any
from annotation_engine.models import (
    VariantAnnotation, Evidence, TierResult,
    AMPScoring, VICCScoring, OncoKBScoring,
    CannedText, CannedTextType, AnalysisType
)
from annotation_engine.canned_text_generator import CannedTextGenerator
from annotation_engine.canned_text_integration import format_canned_texts_for_report


def example_1_braf_v600e_melanoma():
    """
    Example 1: BRAF V600E in Melanoma
    Demonstrates text types 1-4 (Gene and Variant Info/Interpretation)
    """
    print("=" * 80)
    print("Example 1: BRAF V600E in Melanoma")
    print("=" * 80)
    
    # Create variant
    variant = VariantAnnotation(
        gene_symbol="BRAF",
        chromosome="7",
        position=140453136,
        ref="A",
        alt="T",
        hgvs_c="c.1799T>A",
        hgvs_p="p.V600E",
        consequence="missense_variant",
        variant_type="SNV"
    )
    
    # Create evidence
    evidence_list = [
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="LEVEL_1",
            source_kb="ONCOKB",
            description="BRAF V600E mutations confer sensitivity to BRAF inhibitors (vemurafenib, dabrafenib) and MEK inhibitors in melanoma",
            score=10,
            metadata={
                "therapy": "vemurafenib",
                "disease": "melanoma",
                "gene_role": "oncogene",
                "evidence_level": "FDA-approved"
            }
        ),
        Evidence(
            evidence_type="GENE_FUNCTION",
            evidence_level="HIGH",
            source_kb="UNIPROT",
            description="B-Raf proto-oncogene, serine/threonine kinase",
            score=8,
            metadata={
                "gene_name": "B-Raf proto-oncogene",
                "protein_function": "a serine/threonine-protein kinase that acts as a regulatory link in the MAP kinase signaling pathway",
                "pathway": "RAS-RAF-MEK-ERK signaling",
                "pfam_domains": ["Protein kinase domain", "RBD domain", "C1 domain"]
            }
        ),
        Evidence(
            evidence_type="HOTSPOT",
            evidence_level="VERY_HIGH",
            source_kb="CANCER_HOTSPOTS",
            description="V600 is a statistically significant hotspot in multiple cancer types",
            score=9,
            metadata={
                "sample_count": 2341,
                "cancer_types": ["melanoma", "colorectal", "thyroid"],
                "frequency_in_melanoma": 0.52
            }
        ),
        Evidence(
            evidence_type="POPULATION_FREQUENCY",
            evidence_level="HIGH",
            source_kb="GNOMAD",
            description="Not found in gnomAD (0/250000 alleles)",
            score=7,
            metadata={"af": 0, "ac": 0, "an": 250000}
        ),
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="MODERATE",
            source_kb="ALPHAMISSENSE",
            description="Predicted pathogenic by AlphaMissense",
            score=6,
            metadata={"score": 0.98, "classification": "pathogenic"}
        ),
        Evidence(
            evidence_type="CANCER_GENE",
            evidence_level="HIGH",
            source_kb="COSMIC_CGC",
            description="BRAF is a Tier 1 cancer gene (oncogene)",
            score=8,
            metadata={
                "tier": 1,
                "role": "oncogene",
                "somatic": True,
                "germline": False
            }
        )
    ]
    
    # Create tier result
    tier_result = TierResult(
        variant_id="example1",
        gene_symbol="BRAF",
        hgvs_p="p.V600E",
        analysis_type=AnalysisType.TUMOR_ONLY,
        amp_scoring=AMPScoring(
            tier="IA",
            evidence_codes=["FDA1", "NCCN1", "HOT1"],
            score=10
        ),
        vicc_scoring=VICCScoring(
            oncogenicity_classification="Oncogenic",
            evidence_codes=["OS1", "OS3", "OM1"],
            total_score=10
        ),
        oncokb_scoring=OncoKBScoring(
            oncogenic_classification="Oncogenic",
            evidence_level="Level 1",
            evidence_codes=["LEVEL_1", "FDA_APPROVED"]
        ),
        evidence=evidence_list,
        cancer_type="melanoma",
        canned_texts=[],
        confidence_score=0.98,
        annotation_completeness=0.95
    )
    
    # Additional KB data
    kb_data = {
        "gene_info": {
            "associated_conditions": "melanoma, colorectal cancer, thyroid cancer, and lung adenocarcinoma",
            "domain_info": "Contains 3 functional domains including the kinase domain"
        },
        "cancer_frequency": {
            "melanoma": 0.52,
            "colorectal": 0.08,
            "thyroid": 0.45
        }
    }
    
    # Generate texts
    generator = CannedTextGenerator()
    texts = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="melanoma",
        kb_data=kb_data
    )
    
    # Display results
    print(format_canned_texts_for_report(texts))
    print()
    
    # Show specific text types
    for text in texts:
        print(f"\nText Type: {text.text_type}")
        print(f"Confidence: {text.confidence:.1%}")
        print(f"Content: {text.content}")
        print(f"Evidence Support: {', '.join(text.evidence_support)}")
        print(f"Triggered By: {', '.join(text.triggered_by)}")


def example_2_brca1_secondary_finding():
    """
    Example 2: BRCA1 Pathogenic Variant as Secondary Finding
    Demonstrates text type 5 (Incidental/Secondary Findings)
    """
    print("\n" + "=" * 80)
    print("Example 2: BRCA1 Pathogenic Variant as Secondary Finding")
    print("=" * 80)
    
    variant = VariantAnnotation(
        gene_symbol="BRCA1",
        chromosome="17",
        position=41276045,
        ref="C",
        alt="T",
        hgvs_c="c.68_69delAG",
        hgvs_p="p.E23Vfs*17",
        consequence="frameshift_variant",
        variant_type="deletion"
    )
    
    evidence_list = [
        Evidence(
            evidence_type="GERMLINE_PATHOGENIC",
            evidence_level="VERY_HIGH",
            source_kb="CLINVAR",
            description="Pathogenic for Hereditary breast and ovarian cancer syndrome",
            score=10,
            metadata={
                "classification": "Pathogenic",
                "review_status": "germline",
                "condition": "Hereditary breast and ovarian cancer syndrome",
                "clinical_significance": "risk factor",
                "penetrance": "high",
                "inheritance": "autosomal dominant"
            }
        ),
        Evidence(
            evidence_type="ACMG_SF",
            evidence_level="HIGH",
            source_kb="CLINGEN",
            description="BRCA1 is an ACMG SF v3.0 actionable gene",
            score=9,
            metadata={
                "sf_version": "3.0",
                "condition_category": "hereditary cancer syndromes",
                "management": "enhanced surveillance and risk-reducing interventions"
            }
        )
    ]
    
    tier_result = TierResult(
        variant_id="example2",
        gene_symbol="BRCA1",
        hgvs_p="p.E23Vfs*17",
        analysis_type=AnalysisType.TUMOR_ONLY,
        amp_scoring=None,
        vicc_scoring=None,
        oncokb_scoring=None,
        evidence=evidence_list,
        cancer_type="lung adenocarcinoma",  # Primary indication
        canned_texts=[],
        confidence_score=0.95,
        annotation_completeness=0.90
    )
    
    kb_data = {
        "acmg_info": {
            "penetrance_info": "This variant is associated with up to 87% lifetime risk of breast cancer and 40% risk of ovarian cancer",
            "screening_recommendations": "Consider referral to genetic counseling, enhanced breast cancer screening with annual MRI starting at age 25, and discussion of risk-reducing surgeries"
        }
    }
    
    generator = CannedTextGenerator()
    texts = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="lung adenocarcinoma",
        kb_data=kb_data
    )
    
    print(format_canned_texts_for_report(texts))


def example_3_erbb2_amplification():
    """
    Example 3: ERBB2 (HER2) Amplification in Breast Cancer
    Demonstrates text type 6 (Chromosomal Alteration Interpretation)
    """
    print("\n" + "=" * 80)
    print("Example 3: ERBB2 (HER2) Amplification in Breast Cancer")
    print("=" * 80)
    
    variant = VariantAnnotation(
        gene_symbol="ERBB2",
        chromosome="17",
        position=37844000,
        ref="N",
        alt="<CN8>",
        hgvs_c=None,
        hgvs_p=None,
        consequence="copy_number_gain",
        variant_type="duplication",
        metadata={
            "size": 85000,
            "copy_number": 8,
            "log2_ratio": 2.1
        }
    )
    
    evidence_list = [
        Evidence(
            evidence_type="COPY_NUMBER",
            evidence_level="VERY_HIGH",
            source_kb="ONCOKB",
            description="ERBB2 amplification is oncogenic and targetable with HER2-directed therapies",
            score=10,
            metadata={
                "therapeutic_implication": "trastuzumab, pertuzumab, T-DM1",
                "level": "Level 1",
                "fda_approved": True
            }
        ),
        Evidence(
            evidence_type="STRUCTURAL_VARIANT",
            evidence_level="HIGH",
            source_kb="COSMIC",
            description="ERBB2 amplification found in 15-20% of breast cancers",
            score=8,
            metadata={
                "frequency_breast": 0.18,
                "prognostic": "poor without treatment",
                "predictive": "excellent with HER2-targeted therapy"
            }
        )
    ]
    
    tier_result = TierResult(
        variant_id="example3",
        gene_symbol="ERBB2",
        hgvs_p=None,
        analysis_type=AnalysisType.TUMOR_NORMAL,
        amp_scoring=AMPScoring(
            tier="IA",
            evidence_codes=["FDA1", "AMP1"],
            score=10
        ),
        vicc_scoring=None,
        oncokb_scoring=OncoKBScoring(
            oncogenic_classification="Oncogenic",
            evidence_level="Level 1",
            evidence_codes=["LEVEL_1"]
        ),
        evidence=evidence_list,
        cancer_type="breast cancer",
        canned_texts=[],
        confidence_score=0.99,
        annotation_completeness=0.95
    )
    
    kb_data = {
        "structural_info": {
            "key_genes": "ERBB2 (HER2)",
            "therapeutic_vulnerability": "Multiple FDA-approved HER2-targeted therapies are available",
            "prognostic_impact": "Without treatment, HER2 amplification is associated with aggressive disease"
        }
    }
    
    generator = CannedTextGenerator()
    texts = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="breast cancer",
        kb_data=kb_data
    )
    
    print(format_canned_texts_for_report(texts))


def example_4_pertinent_negatives():
    """
    Example 4: Pertinent Negatives in NSCLC
    Demonstrates text type 7 (Pertinent Negatives)
    """
    print("\n" + "=" * 80)
    print("Example 4: Pertinent Negatives in Non-Small Cell Lung Cancer")
    print("=" * 80)
    
    # For pertinent negatives, we typically don't have a specific variant
    # This would be generated at the report level
    variant = VariantAnnotation(
        gene_symbol="PANEL",
        chromosome="NA",
        position=0,
        ref="N",
        alt="N"
    )
    
    evidence_list = []  # No positive findings
    
    tier_result = TierResult(
        variant_id="example4",
        gene_symbol="PANEL",
        hgvs_p=None,
        analysis_type=AnalysisType.TUMOR_ONLY,
        amp_scoring=None,
        vicc_scoring=None,
        oncokb_scoring=None,
        evidence=evidence_list,
        cancer_type="non-small cell lung cancer",
        canned_texts=[],
        confidence_score=0.90,
        annotation_completeness=0.95
    )
    
    kb_data = {
        "negative_findings": {
            "genes_tested": ["EGFR", "ALK", "ROS1", "BRAF", "MET", "RET", "ERBB2", "KRAS", "NTRK1", "NTRK2", "NTRK3"],
            "gene_category": "targetable driver genes",
            "pathway": "RTK/RAS/RAF",
            "coverage_statement": "All coding regions achieved >500x coverage"
        }
    }
    
    generator = CannedTextGenerator()
    texts = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="non-small cell lung cancer",
        kb_data=kb_data
    )
    
    print(format_canned_texts_for_report(texts))


def example_5_biomarkers():
    """
    Example 5: TMB and MSI Biomarkers
    Demonstrates text type 8 (Biomarkers)
    """
    print("\n" + "=" * 80)
    print("Example 5: Tumor Mutational Burden and MSI Status")
    print("=" * 80)
    
    # For biomarkers, variant info is less relevant
    variant = VariantAnnotation(
        gene_symbol="BIOMARKER",
        chromosome="NA",
        position=0,
        ref="N",
        alt="N"
    )
    
    evidence_list = []
    
    tier_result = TierResult(
        variant_id="example5",
        gene_symbol="BIOMARKER",
        hgvs_p=None,
        analysis_type=AnalysisType.TUMOR_ONLY,
        amp_scoring=None,
        vicc_scoring=None,
        oncokb_scoring=None,
        evidence=evidence_list,
        cancer_type="colorectal cancer",
        canned_texts=[],
        confidence_score=0.95,
        annotation_completeness=0.90
    )
    
    # Example 5a: High TMB
    print("\n--- Example 5a: High TMB ---")
    kb_data_tmb = {
        "tmb": {
            "value": 25.3,
            "unit": "mutations/Mb",
            "percentile": 95
        }
    }
    
    generator = CannedTextGenerator()
    texts_tmb = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="colorectal cancer",
        kb_data=kb_data_tmb
    )
    
    for text in texts_tmb:
        if text.text_type == CannedTextType.BIOMARKERS:
            print(f"TMB Text: {text.content}")
    
    # Example 5b: MSI-H
    print("\n--- Example 5b: MSI-H Status ---")
    kb_data_msi = {
        "msi": {
            "status": "MSI-H",
            "score": 48,
            "unstable_loci": 12
        }
    }
    
    texts_msi = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="colorectal cancer",
        kb_data=kb_data_msi
    )
    
    for text in texts_msi:
        if text.text_type == CannedTextType.BIOMARKERS:
            print(f"MSI Text: {text.content}")
    
    # Example 5c: PD-L1 Expression
    print("\n--- Example 5c: PD-L1 Expression ---")
    kb_data_pdl1 = {
        "biomarkers": {
            "PD-L1": {
                "name": "PD-L1 Expression",
                "value": "TPS 85%",
                "category": "High",
                "clinical_interpretation": "High PD-L1 expression",
                "therapy_associations": "pembrolizumab monotherapy"
            }
        }
    }
    
    texts_pdl1 = generator.generate_all_canned_texts(
        variant=variant,
        evidence_list=evidence_list,
        tier_result=tier_result,
        cancer_type="non-small cell lung cancer",
        kb_data=kb_data_pdl1
    )
    
    for text in texts_pdl1:
        if text.text_type == CannedTextType.BIOMARKERS:
            print(f"PD-L1 Text: {text.content}")


def run_all_examples():
    """Run all examples to demonstrate all 8 canned text types"""
    examples = [
        example_1_braf_v600e_melanoma,
        example_2_brca1_secondary_finding,
        example_3_erbb2_amplification,
        example_4_pertinent_negatives,
        example_5_biomarkers
    ]
    
    for example in examples:
        example()
        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    print("COMPREHENSIVE CANNED TEXT GENERATION EXAMPLES")
    print("Demonstrating all 8 types of clinical interpretation text")
    print()
    
    run_all_examples()
    
    print("\nSUMMARY OF CANNED TEXT TYPES:")
    print("1. General Gene Info - Basic gene function and characteristics")
    print("2. Gene Dx Interpretation - Gene significance in specific cancer")
    print("3. General Variant Info - Technical variant description")
    print("4. Variant Dx Interpretation - Clinical meaning of variant")
    print("5. Incidental/Secondary Findings - ACMG actionable findings")
    print("6. Chromosomal Alteration - CNVs, fusions, structural variants")
    print("7. Pertinent Negatives - Important negative results")
    print("8. Biomarkers - TMB, MSI, expression markers")