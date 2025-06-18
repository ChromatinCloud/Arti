"""
Enhanced Narrative Generation Examples

Demonstrates the enhanced deterministic narrative generator with:
- Reliable citation insertion and management
- Intelligent source ordering and prioritization  
- Evidence synthesis with proper attribution
- Quality assurance and consistency
"""

from annotation_engine.models import Evidence, CannedTextType
from annotation_engine.enhanced_narrative_generator import EnhancedNarrativeGenerator


def example_braf_comprehensive_narrative():
    """
    Example: BRAF V600E with comprehensive evidence from multiple sources
    Demonstrates citation ordering, source prioritization, and evidence synthesis
    """
    print("=" * 80)
    print("Example: BRAF V600E - Comprehensive Multi-Source Narrative")
    print("=" * 80)
    
    # Create comprehensive evidence from multiple sources with varying reliability
    evidence_list = [
        # Tier 1: FDA/Regulatory (highest priority)
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="FDA_APPROVED",
            source_kb="FDA",
            description="Vemurafenib is FDA-approved for treatment of unresectable or metastatic melanoma with BRAF V600E mutation",
            score=10,
            metadata={
                "therapy": "vemurafenib",
                "indication": "melanoma",
                "approval_date": "2011",
                "evidence_level": "FDA-approved"
            }
        ),
        
        # Tier 2: Professional Guidelines  
        Evidence(
            evidence_type="GUIDELINE",
            evidence_level="LEVEL_1",
            source_kb="NCCN",
            description="NCCN Guidelines recommend BRAF inhibitor therapy for BRAF V600E-mutated melanoma",
            score=9,
            metadata={
                "guideline": "NCCN Melanoma Guidelines",
                "version": "2.2024",
                "recommendation_level": "Category 1"
            }
        ),
        
        # Tier 3: Expert Curated (high quality)
        Evidence(
            evidence_type="THERAPEUTIC", 
            evidence_level="LEVEL_1",
            source_kb="ONCOKB",
            description="BRAF V600E is a predictive biomarker for response to BRAF inhibitors in melanoma",
            score=10,
            metadata={
                "therapy": "BRAF inhibitors",
                "evidence_level": "Level 1",
                "oncogenic": "Oncogenic"
            }
        ),
        
        Evidence(
            evidence_type="CLINICAL_SIGNIFICANCE",
            evidence_level="HIGH",
            source_kb="CIVIC",
            description="Strong clinical evidence supports the oncogenic role of BRAF V600E in melanoma",
            score=9,
            metadata={
                "classification": "Oncogenic",
                "evidence_rating": "5-star"
            }
        ),
        
        Evidence(
            evidence_type="CLINICAL_SIGNIFICANCE",
            evidence_level="PATHOGENIC",
            source_kb="CLINVAR",
            description="Classified as Pathogenic for melanoma predisposition",
            score=8,
            metadata={
                "classification": "Pathogenic",
                "review_status": "reviewed by expert panel",
                "pmids": ["21639808", "20818844"]
            }
        ),
        
        # Tier 4: Community/Research databases
        Evidence(
            evidence_type="HOTSPOT",
            evidence_level="HIGH", 
            source_kb="CANCER_HOTSPOTS",
            description="V600 is a statistically significant mutational hotspot with >2000 samples",
            score=8,
            metadata={
                "sample_count": 2341,
                "cancer_types": ["melanoma", "colorectal", "thyroid"],
                "frequency_melanoma": 0.52
            }
        ),
        
        Evidence(
            evidence_type="SOMATIC_MUTATION",
            evidence_level="HIGH",
            source_kb="COSMIC", 
            description="BRAF is a Tier 1 cancer gene with V600E as the most common mutation",
            score=8,
            metadata={
                "tier": 1,
                "role": "oncogene",
                "mutation_frequency": 0.6
            }
        ),
        
        Evidence(
            evidence_type="POPULATION_FREQUENCY",
            evidence_level="HIGH",
            source_kb="GNOMAD",
            description="Not observed in 250,000 population samples",
            score=7,
            metadata={
                "af": 0,
                "ac": 0,
                "an": 250000,
                "population": "global"
            }
        ),
        
        # Tier 5: Computational predictions (lower priority)
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="HIGH",
            source_kb="ALPHAMISSENSE", 
            description="Predicted to be pathogenic with high confidence",
            score=6,
            metadata={
                "score": 0.98,
                "classification": "pathogenic",
                "confidence": "high"
            }
        ),
        
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="MODERATE",
            source_kb="REVEL",
            description="REVEL score indicates deleterious effect",
            score=5,
            metadata={
                "score": 0.932,
                "classification": "deleterious"
            }
        ),
        
        # Additional therapeutic evidence
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="LEVEL_2",
            source_kb="ONCOKB",
            description="Dabrafenib + trametinib combination therapy is Level 1 evidence for BRAF V600E melanoma",
            score=10,
            metadata={
                "therapy": "dabrafenib + trametinib",
                "evidence_level": "Level 1",
                "combination": True
            }
        ),
        
        # Resistance evidence
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="HIGH",
            source_kb="CIVIC",
            description="Acquired resistance to BRAF inhibitors may occur through multiple mechanisms",
            score=7,
            metadata={
                "resistance_mechanisms": ["NRAS mutations", "MEK1 mutations", "BRAF amplification"],
                "clinical_impact": "reduced efficacy"
            }
        )
    ]
    
    # Context for narrative generation
    context = {
        "gene_symbol": "BRAF",
        "cancer_type": "melanoma",
        "variant_description": "V600E missense mutation"
    }
    
    # Generate enhanced narrative
    generator = EnhancedNarrativeGenerator()
    
    narrative_result = generator.generate_enhanced_narrative(
        evidence_list=evidence_list,
        text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
        context=context
    )
    
    print(f"Generated Narrative (Confidence: {narrative_result.confidence:.1%}):")
    print("-" * 60)
    print(narrative_result.content)
    print("-" * 60)
    print(f"Evidence Support: {', '.join(narrative_result.evidence_support[:5])}...")
    print(f"Triggered By: {', '.join(narrative_result.triggered_by)}")


def example_tp53_gene_interpretation():
    """
    Example: TP53 gene interpretation showing gene function and cancer role synthesis
    """
    print("\n" + "=" * 80)
    print("Example: TP53 Gene Interpretation - Function and Cancer Role")
    print("=" * 80)
    
    evidence_list = [
        # Gene function evidence
        Evidence(
            evidence_type="PROTEIN_FUNCTION",
            evidence_level="HIGH",
            source_kb="UNIPROT",
            description="TP53 encodes tumor protein p53, a transcription factor that regulates cell cycle and apoptosis",
            score=9,
            metadata={
                "protein_function": "transcription factor and tumor suppressor",
                "pathway": "p53 signaling pathway",
                "cellular_process": ["cell cycle control", "apoptosis", "DNA repair"]
            }
        ),
        
        Evidence(
            evidence_type="GENE_FUNCTION",
            evidence_level="HIGH", 
            source_kb="NCBI_GENE",
            description="TP53 acts as a tumor suppressor that prevents cancer formation",
            score=9,
            metadata={
                "gene_name": "tumor protein p53",
                "location": "17p13.1",
                "function_class": "tumor suppressor"
            }
        ),
        
        # Cancer role evidence
        Evidence(
            evidence_type="CANCER_GENE",
            evidence_level="VERY_HIGH",
            source_kb="COSMIC",
            description="TP53 is the most frequently mutated gene in human cancers, altered in >50% of cases",
            score=10,
            metadata={
                "tier": 1,
                "role": "tumor suppressor",
                "mutation_frequency": 0.54,
                "cancer_types": "pan-cancer"
            }
        ),
        
        Evidence(
            evidence_type="CLINICAL_SIGNIFICANCE",
            evidence_level="HIGH",
            source_kb="ONCOKB",
            description="TP53 mutations are oncogenic and associated with poor prognosis across cancer types",
            score=9,
            metadata={
                "oncogenic": "Oncogenic",
                "prognostic": "poor prognosis",
                "therapeutic": "limited targeted options"
            }
        ),
        
        # Therapeutic context
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="INVESTIGATIONAL",
            source_kb="CIVIC",
            description="TP53 restoration therapies and MDM2 inhibitors are under investigation",
            score=6,
            metadata={
                "therapies": ["APR-246", "AMG 232", "RG7112"],
                "development_stage": "clinical trials",
                "mechanism": "p53 pathway restoration"
            }
        ),
        
        # Professional guidelines
        Evidence(
            evidence_type="GUIDELINE",
            evidence_level="MODERATE",
            source_kb="NCCN",
            description="TP53 mutation status is prognostic but not routinely used for treatment selection",
            score=7,
            metadata={
                "clinical_utility": "prognostic",
                "therapeutic_utility": "limited"
            }
        )
    ]
    
    context = {
        "gene_symbol": "TP53",
        "cancer_type": "solid tumors"
    }
    
    generator = EnhancedNarrativeGenerator()
    
    narrative_result = generator.generate_enhanced_narrative(
        evidence_list=evidence_list,
        text_type=CannedTextType.GENE_DX_INTERPRETATION,
        context=context
    )
    
    print(f"Generated Narrative (Confidence: {narrative_result.confidence:.1%}):")
    print("-" * 60)
    print(narrative_result.content)


def example_variant_with_limited_evidence():
    """
    Example: Variant with limited evidence showing graceful handling
    """
    print("\n" + "=" * 80)
    print("Example: Variant with Limited Evidence - Graceful Degradation")
    print("=" * 80)
    
    evidence_list = [
        # Only computational predictions available
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="MODERATE",
            source_kb="ALPHAMISSENSE",
            description="Predicted to be likely pathogenic",
            score=5,
            metadata={
                "score": 0.75,
                "classification": "likely pathogenic"
            }
        ),
        
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="LOW",
            source_kb="SIFT",
            description="Predicted to be deleterious",
            score=4,
            metadata={
                "score": 0.02,
                "classification": "deleterious"
            }
        ),
        
        Evidence(
            evidence_type="POPULATION_FREQUENCY",
            evidence_level="MODERATE",
            source_kb="GNOMAD",
            description="Rare variant with allele frequency 0.0001%",
            score=6,
            metadata={
                "af": 0.000001,
                "ac": 3,
                "an": 250000
            }
        )
    ]
    
    context = {
        "gene_symbol": "OBSCURE1",
        "cancer_type": "rare cancer type",
        "variant_description": "c.1234G>A (p.Arg412His)"
    }
    
    generator = EnhancedNarrativeGenerator()
    
    narrative_result = generator.generate_enhanced_narrative(
        evidence_list=evidence_list,
        text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
        context=context
    )
    
    print(f"Generated Narrative (Confidence: {narrative_result.confidence:.1%}):")
    print("-" * 60)
    print(narrative_result.content)


def example_biomarker_narrative():
    """
    Example: Biomarker interpretation with TMB and MSI data
    """
    print("\n" + "=" * 80)
    print("Example: Biomarker Interpretation - TMB and MSI")
    print("=" * 80)
    
    evidence_list = [
        # TMB evidence
        Evidence(
            evidence_type="BIOMARKER",
            evidence_level="HIGH",
            source_kb="FDA",
            description="TMB-High (≥10 mutations/Mb) is FDA-approved biomarker for pembrolizumab",
            score=10,
            metadata={
                "biomarker": "TMB",
                "threshold": 10,
                "therapy": "pembrolizumab",
                "approval": "FDA-approved"
            }
        ),
        
        Evidence(
            evidence_type="BIOMARKER",
            evidence_level="HIGH",
            source_kb="NCCN",
            description="TMB ≥10 mut/Mb recommended for immunotherapy consideration across solid tumors",
            score=9,
            metadata={
                "guideline": "NCCN",
                "recommendation": "immunotherapy"
            }
        ),
        
        # MSI evidence
        Evidence(
            evidence_type="BIOMARKER", 
            evidence_level="HIGH",
            source_kb="FDA",
            description="MSI-H is FDA-approved biomarker for immune checkpoint inhibitors",
            score=10,
            metadata={
                "biomarker": "MSI",
                "status": "MSI-H",
                "therapy": "immune checkpoint inhibitors"
            }
        )
    ]
    
    context = {
        "cancer_type": "colorectal cancer",
        "tmb_value": 15.2,
        "msi_status": "MSI-H"
    }
    
    generator = EnhancedNarrativeGenerator()
    
    narrative_result = generator.generate_enhanced_narrative(
        evidence_list=evidence_list,
        text_type=CannedTextType.BIOMARKERS,
        context=context
    )
    
    print(f"Generated Narrative (Confidence: {narrative_result.confidence:.1%}):")
    print("-" * 60)
    print(narrative_result.content)


def demonstrate_citation_ordering():
    """
    Demonstrate how sources are ordered by reliability and cited properly
    """
    print("\n" + "=" * 80)
    print("Citation Ordering Demonstration")
    print("=" * 80)
    
    # Mix of sources with different reliability tiers
    evidence_list = [
        Evidence(
            evidence_type="COMPUTATIONAL",
            evidence_level="MODERATE",
            source_kb="SIFT",  # Tier 5
            description="Predicted deleterious",
            score=4
        ),
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="FDA_APPROVED", 
            source_kb="FDA",  # Tier 1 - should be cited first
            description="FDA-approved indication",
            score=10
        ),
        Evidence(
            evidence_type="CLINICAL_SIGNIFICANCE",
            evidence_level="HIGH",
            source_kb="CIVIC",  # Tier 3
            description="Strong clinical evidence",
            score=8
        ),
        Evidence(
            evidence_type="POPULATION_FREQUENCY",
            evidence_level="HIGH",
            source_kb="GNOMAD",  # Tier 4
            description="Population frequency data",
            score=7
        ),
        Evidence(
            evidence_type="GUIDELINE",
            evidence_level="HIGH",
            source_kb="NCCN",  # Tier 2
            description="Professional guideline recommendation",
            score=9
        )
    ]
    
    context = {"gene_symbol": "TEST", "cancer_type": "test cancer"}
    
    generator = EnhancedNarrativeGenerator()
    
    narrative_result = generator.generate_enhanced_narrative(
        evidence_list=evidence_list,
        text_type=CannedTextType.VARIANT_DX_INTERPRETATION,
        context=context
    )
    
    print("Expected Citation Order (by reliability tier):")
    print("1. FDA (Tier 1 - Regulatory)")
    print("2. NCCN (Tier 2 - Guidelines)")  
    print("3. CIViC (Tier 3 - Expert Curated)")
    print("4. gnomAD (Tier 4 - Community)")
    print("5. SIFT (Tier 5 - Computational)")
    print()
    print("Generated Narrative with Citations:")
    print("-" * 60)
    print(narrative_result.content)


def run_all_enhanced_narrative_examples():
    """Run all enhanced narrative examples"""
    examples = [
        example_braf_comprehensive_narrative,
        example_tp53_gene_interpretation,
        example_variant_with_limited_evidence,
        example_biomarker_narrative,
        demonstrate_citation_ordering
    ]
    
    for example in examples:
        example()
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print("ENHANCED DETERMINISTIC NARRATIVE GENERATION EXAMPLES")
    print("Demonstrating reliable citations, source ordering, and evidence synthesis")
    print()
    
    run_all_enhanced_narrative_examples()
    
    print("\nKEY FEATURES DEMONSTRATED:")
    print("✅ Reliable citation insertion and numbering")
    print("✅ Intelligent source ordering by reliability tier")
    print("✅ Evidence clustering and synthesis")
    print("✅ Proper attribution with inline citations")
    print("✅ Comprehensive reference sections")
    print("✅ Graceful handling of limited evidence") 
    print("✅ Confidence scoring based on source quality")
    print("✅ Consistent narrative flow and transitions")
    print()
    print("Source Reliability Tiers:")
    print("Tier 1: FDA, EMA (Regulatory)")
    print("Tier 2: NCCN, CAP, ASCO (Guidelines)")
    print("Tier 3: OncoKB, CIViC, ClinVar (Expert Curated)")
    print("Tier 4: COSMIC, gnomAD (Community/Research)")
    print("Tier 5: AlphaMissense, SIFT, PolyPhen (Computational)")