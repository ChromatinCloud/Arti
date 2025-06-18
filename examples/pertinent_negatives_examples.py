"""
Comprehensive Pertinent Negatives Examples

This demonstrates the enhanced pertinent negatives generator that handles
diverse types of negative findings beyond just gene mutations.
"""

from annotation_engine.canned_text_generator_v2 import EnhancedPertinentNegativesGenerator


def example_gbm_comprehensive_negatives():
    """
    Example: Comprehensive GBM negative findings
    Shows chromosomal alterations, methylation, specific variants, fusions, etc.
    """
    print("=" * 80)
    print("Example: Glioblastoma Multiforme - Comprehensive Negative Findings")
    print("=" * 80)
    
    generator = EnhancedPertinentNegativesGenerator()
    
    # Comprehensive negative findings for GBM
    negative_findings_data = {
        # Gene mutations tested
        "genes_tested": [
            "IDH1", "IDH2", "ATRX", "TP53", "PTEN", "PIK3CA", "PIK3R1",
            "CDKN2A", "CDKN2B", "RB1", "NF1", "PDGFRA", "KIT", "BRAF"
        ],
        
        # Chromosomal alterations
        "chromosomal_analysis": {
            "chr7_gain": False,
            "chr10_loss": False,
            "chr1p19q_codeletion": False,
            "chr9p21_deletion": False,
            "chr19q13_deletion": False
        },
        
        # Methylation analysis
        "methylation_tested": ["MGMT", "TERT", "CpG_island_methylator"],
        "methylation_results": {
            "MGMT": "unmethylated",
            "TERT": "unmethylated", 
            "CpG_island_methylator": "negative"
        },
        
        # Copy number analysis
        "copy_number_tested": ["EGFR", "PDGFRA", "CDK4", "MDM2", "CDK6", "CCND2"],
        "copy_number_results": {
            "EGFR": 2.1,  # Normal copy number
            "PDGFRA": 1.8,
            "CDK4": 2.0,
            "MDM2": 1.9,
            "CDK6": 2.1,
            "CCND2": 2.0
        },
        
        # Specific variant analysis
        "specific_variants_tested": ["EGFRvIII", "TERT_C228T", "TERT_C250T"],
        "specific_variant_results": {
            "EGFRvIII": "not detected",
            "TERT_C228T": "not detected", 
            "TERT_C250T": "not detected"
        },
        
        # Fusion analysis
        "fusion_analysis": {
            "fusions_tested": ["FGFR3-TACC3", "FGFR1-TACC1", "EGFR-SEPT14", "NTRK1/2/3"],
            "results": "negative"
        },
        
        # Expression/protein markers
        "expression_markers": {
            "EGFR": "normal",
            "p53": "wild-type pattern",
            "ATRX": "retained",
            "IDH1_R132H": "negative"
        },
        
        # Molecular signatures
        "signatures_analyzed": ["G-CIMP", "RTK_signature", "mesenchymal_signature"],
        "signature_results": {
            "G-CIMP": "negative",
            "RTK_signature": "inactive",
            "mesenchymal_signature": "inactive"
        },
        
        # Quality metrics
        "coverage_info": "All coding regions achieved >500x coverage; copy number analysis performed with >200 informative SNPs",
        "method_note": "Comprehensive genomic profiling using hybrid capture NGS, methylation-specific PCR, and SNP array analysis"
    }
    
    texts = generator.generate_pertinent_negatives(
        cancer_type="glioblastoma",
        negative_findings_data=negative_findings_data
    )
    
    for i, text in enumerate(texts, 1):
        print(f"\nNegative Finding Text #{i}:")
        print(f"Confidence: {text.confidence:.1%}")
        print(f"Content:\n{text.content}")
        print(f"Evidence: {', '.join(text.evidence_support)}")
        print("-" * 60)


def example_colorectal_negatives():
    """
    Example: Colorectal cancer pertinent negatives
    Shows RAS/RAF mutations, MLH1 methylation, HER2, CMS classification
    """
    print("\n" + "=" * 80)
    print("Example: Colorectal Cancer - Therapy-Relevant Negative Findings")
    print("=" * 80)
    
    generator = EnhancedPertinentNegativesGenerator()
    
    negative_findings_data = {
        "genes_tested": [
            "KRAS", "NRAS", "BRAF", "PIK3CA", "APC", "TP53", 
            "SMAD4", "FBXW7", "POLE", "POLD1"
        ],
        
        "methylation_tested": ["MLH1", "MGMT"],
        "methylation_results": {
            "MLH1": "unmethylated",
            "MGMT": "unmethylated"
        },
        
        "copy_number_tested": ["HER2", "FGFR2", "MYC"],
        "copy_number_results": {
            "HER2": 1.9,  # No amplification
            "FGFR2": 2.1,
            "MYC": 2.0
        },
        
        "signatures_analyzed": ["CMS", "MSI", "HRD"],
        "signature_results": {
            "CMS": "CMS2 (canonical)",
            "MSI": "MSS",
            "HRD": "HR-proficient"
        },
        
        "expression_markers": {
            "MLH1": "retained",
            "MSH2": "retained", 
            "MSH6": "retained",
            "PMS2": "retained"
        },
        
        "additional_negatives": [
            {
                "type": "microsatellite",
                "target": "MSI_analysis",
                "description": "Microsatellite analysis: stable (MSS). No evidence of mismatch repair deficiency.",
                "clinical_relevance": "MSS status suggests standard chemotherapy rather than immunotherapy"
            }
        ],
        
        "coverage_info": "All exons achieved >300x coverage; MSI analysis included 5 standard markers",
        "method_note": "RAS/RAF analysis performed using ddPCR for enhanced sensitivity"
    }
    
    texts = generator.generate_pertinent_negatives(
        cancer_type="colorectal",
        negative_findings_data=negative_findings_data
    )
    
    for i, text in enumerate(texts, 1):
        print(f"\nNegative Finding Text #{i}:")
        print(f"Content:\n{text.content}")
        print("-" * 60)


def example_lung_adenocarcinoma_negatives():
    """
    Example: Lung adenocarcinoma pertinent negatives
    Shows targetable driver analysis, PD-L1, fusion testing
    """
    print("\n" + "=" * 80)
    print("Example: Lung Adenocarcinoma - Targetable Driver Analysis")
    print("=" * 80)
    
    generator = EnhancedPertinentNegativesGenerator()
    
    negative_findings_data = {
        "genes_tested": [
            "EGFR", "KRAS", "ALK", "ROS1", "BRAF", "MET", "RET", 
            "ERBB2", "PIK3CA", "STK11", "KEAP1", "NF1"
        ],
        
        "fusion_analysis": {
            "fusions_tested": ["ALK", "ROS1", "RET", "NTRK1", "NTRK2", "NTRK3", "FGFR3"],
            "results": "negative",
            "method": "NGS-based fusion detection with manual review"
        },
        
        "copy_number_tested": ["MET", "ERBB2", "FGFR1", "CCND1"],
        "copy_number_results": {
            "MET": 2.8,  # Below amplification threshold
            "ERBB2": 2.1,
            "FGFR1": 1.9,
            "CCND1": 2.0
        },
        
        "expression_markers": {
            "PD-L1": "TPS <1%",
            "ALK": "negative by IHC",
            "ROS1": "negative by IHC"
        },
        
        "signatures_analyzed": ["STK11_loss", "KEAP1_loss", "smoking_signature"],
        "signature_results": {
            "STK11_loss": "intact",
            "KEAP1_loss": "intact", 
            "smoking_signature": "low (5 mutations)"
        },
        
        "specific_variants_tested": [
            "EGFR_exon19del", "EGFR_L858R", "EGFR_T790M", 
            "KRAS_G12C", "BRAF_V600E"
        ],
        "specific_variant_results": {
            "EGFR_exon19del": "not detected",
            "EGFR_L858R": "not detected",
            "EGFR_T790M": "not detected",
            "KRAS_G12C": "not detected", 
            "BRAF_V600E": "not detected"
        },
        
        "coverage_info": "All targeted regions achieved >1000x coverage; fusion analysis covered all known breakpoints",
        "method_note": "Comprehensive genomic profiling using 500+ gene panel with validated fusion detection"
    }
    
    texts = generator.generate_pertinent_negatives(
        cancer_type="lung adenocarcinoma", 
        negative_findings_data=negative_findings_data
    )
    
    for i, text in enumerate(texts, 1):
        print(f"\nNegative Finding Text #{i}:")
        print(f"Content:\n{text.content}")
        print("-" * 60)


def example_breast_cancer_comprehensive():
    """
    Example: Breast cancer comprehensive molecular profiling negatives
    Shows hormone receptors, HER2, homologous recombination deficiency
    """
    print("\n" + "=" * 80)
    print("Example: Breast Cancer - Comprehensive Molecular Profile")
    print("=" * 80)
    
    generator = EnhancedPertinentNegativesGenerator()
    
    negative_findings_data = {
        "genes_tested": [
            "PIK3CA", "TP53", "CDH1", "GATA3", "MAP3K1", "NCOR1",
            "AKT1", "ERBB2", "ERBB3", "FGFR1", "CCND1"
        ],
        
        "expression_markers": {
            "ER": "negative (<1%)",
            "PR": "negative (<1%)", 
            "HER2": "0 (negative)",
            "Ki-67": "high (65%)"
        },
        
        "copy_number_tested": ["HER2", "FGFR1", "CCND1", "MYC", "TOPK"],
        "copy_number_results": {
            "HER2": 1.8,  # Not amplified
            "FGFR1": 2.0,
            "CCND1": 2.1,
            "MYC": 1.9,
            "TOPK": 2.0
        },
        
        "signatures_analyzed": ["HRD", "BRCAness", "luminal_signature", "basal_signature"],
        "signature_results": {
            "HRD": "HR-proficient (score: 15)",
            "BRCAness": "negative",
            "luminal_signature": "inactive",
            "basal_signature": "active"
        },
        
        "methylation_tested": ["BRCA1", "CDKN2A"],
        "methylation_results": {
            "BRCA1": "unmethylated",
            "CDKN2A": "unmethylated"
        },
        
        "additional_negatives": [
            {
                "type": "subtype",
                "target": "molecular_subtype", 
                "description": "Molecular subtyping: Triple-negative breast cancer (TNBC) with basal-like features.",
                "clinical_relevance": "TNBC subtype indicates need for chemotherapy-based treatment approaches"
            }
        ],
        
        "coverage_info": "All coding regions >500x coverage; HRD analysis based on genome-wide SNP array",
        "method_note": "Integrated analysis including NGS, IHC, and FISH for HER2"
    }
    
    texts = generator.generate_pertinent_negatives(
        cancer_type="breast cancer",
        negative_findings_data=negative_findings_data
    )
    
    for i, text in enumerate(texts, 1):
        print(f"\nNegative Finding Text #{i}:")
        print(f"Content:\n{text.content}")
        print("-" * 60)


def run_all_pertinent_negative_examples():
    """Run all pertinent negative examples"""
    examples = [
        example_gbm_comprehensive_negatives,
        example_colorectal_negatives,
        example_lung_adenocarcinoma_negatives,
        example_breast_cancer_comprehensive
    ]
    
    for example in examples:
        example()
        print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print("ENHANCED PERTINENT NEGATIVES EXAMPLES")
    print("Demonstrating comprehensive negative findings beyond gene mutations")
    print()
    
    run_all_pertinent_negative_examples()
    
    print("\nTYPES OF PERTINENT NEGATIVES COVERED:")
    print("• Gene mutations (driver genes, tumor suppressors)")
    print("• Chromosomal alterations (+7/-10, 1p/19q codeletion)")
    print("• Methylation status (MGMT, MLH1, TERT promoter)")
    print("• Copy number alterations (amplifications, deletions)")
    print("• Fusion events (targetable fusions, rearrangements)")
    print("• Specific variants (EGFRvIII, TERT promoter mutations)")
    print("• Expression markers (hormone receptors, PD-L1)")
    print("• Molecular signatures (CMS, HRD, G-CIMP)")
    print("• Protein markers (IHC results)")
    print("• Pathway alterations (RTK, DNA repair)")
    print("\nThis comprehensive approach ensures all clinically relevant")
    print("negative findings are appropriately documented.")