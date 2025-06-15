"""
Test cases for Dynamic Somatic Confidence (DSC) calculation

Tests the DSC scoring model that replaces flat confidence penalties
for tumor-only analysis with sophisticated evidence-based scoring.
"""

import pytest
from pathlib import Path
import sys

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    VariantAnnotation, Evidence, DynamicSomaticConfidence, 
    AnalysisType, HotspotEvidence, PopulationFrequency
)
from annotation_engine.evidence_aggregator import DynamicSomaticConfidenceCalculator


class TestDynamicSomaticConfidenceCalculation:
    """Test DSC calculation across different variant scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.dsc_calculator = DynamicSomaticConfidenceCalculator()
    
    def test_high_confidence_somatic_hotspot(self):
        """Test DSC for high-confidence somatic variant at cancer hotspot"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            vaf=0.45,  # High VAF
            tumor_purity=0.8,  # Good purity
            consequence=["missense_variant"],
            hotspot_evidence=[HotspotEvidence(
                source="COSMIC_Hotspots",
                samples_observed=500,
                cancer_types=["melanoma", "lung"],
                hotspot_type="single_residue"
            )],
            population_frequencies=[PopulationFrequency(
                database="gnomAD",
                population="global",
                allele_frequency=0.0001  # Very rare in population
            )]
        )
        
        evidence_list = [
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022",
                source_kb="COSMIC_Hotspots",
                description="Well-established hotspot BRAF V600E"
            )
        ]
        
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=0.8
        )
        
        # High confidence somatic - should be > 0.9 for Tier I eligibility
        assert dsc_result.dsc_score > 0.9
        assert dsc_result.vaf_purity_score > 0.8  # Good VAF/purity consistency
        assert dsc_result.prior_probability_score > 0.8  # Hotspot gives high somatic prior
        assert dsc_result.hotspot_evidence is True
        assert "vaf_purity" in dsc_result.modules_available
        assert "prior_probability" in dsc_result.modules_available
    
    def test_moderate_confidence_somatic(self):
        """Test DSC for moderate confidence somatic variant"""
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            vaf=0.25,  # Moderate VAF
            tumor_purity=0.6,  # Moderate purity
            consequence=["missense_variant"],
            population_frequencies=[PopulationFrequency(
                database="gnomAD",
                population="global",
                allele_frequency=0.0005  # Rare but present
            )]
        )
        
        evidence_list = [
            Evidence(
                code="OM1",
                score=2,
                guideline="VICC_2022",
                source_kb="CIViC",
                description="Critical functional domain in TP53"
            )
        ]
        
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=0.6
        )
        
        # Moderate confidence - should be 0.6-0.9 for Tier II eligibility
        assert 0.6 <= dsc_result.dsc_score <= 0.9
        assert dsc_result.hotspot_evidence is False
        assert dsc_result.population_frequency == 0.0005
    
    def test_low_confidence_potential_germline(self):
        """Test DSC for variant with germline characteristics"""
        variant = VariantAnnotation(
            chromosome="1",
            position=12345678,
            reference="G",
            alternate="A",
            gene_symbol="UNKNOWN_GENE",
            vaf=0.48,  # Near 50% suggests germline
            tumor_purity=0.9,  # High purity but VAF suggests germline
            consequence=["synonymous_variant"],
            population_frequencies=[PopulationFrequency(
                database="gnomAD",
                population="global",
                allele_frequency=0.02  # Common in population
            )],
            clinvar_significance="Benign"
        )
        
        evidence_list = [
            Evidence(
                code="SBVS1",
                score=-4,
                guideline="VICC_2022",
                source_kb="gnomAD",
                description="High population frequency"
            )
        ]
        
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=0.9
        )
        
        # Low confidence somatic - should be < 0.6
        assert dsc_result.dsc_score < 0.6
        assert dsc_result.vaf_purity_score < 0.5  # VAF inconsistent with somatic
        assert dsc_result.prior_probability_score < 0.5  # High pop freq suggests germline
        assert dsc_result.population_frequency == 0.02
        assert dsc_result.clinvar_germline is True
    
    def test_dsc_with_missing_tumor_purity(self):
        """Test DSC calculation when tumor purity is unknown"""
        variant = VariantAnnotation(
            chromosome="12",
            position=25398281,
            reference="C",
            alternate="A",
            gene_symbol="KRAS",
            vaf=0.35,  # Moderate VAF
            tumor_purity=None,  # Unknown purity
            consequence=["missense_variant"],
            hotspot_evidence=[HotspotEvidence(
                source="COSMIC_Hotspots",
                samples_observed=100,
                cancer_types=["colon"],
                hotspot_type="single_residue"
            )]
        )
        
        evidence_list = [
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022",
                source_kb="COSMIC_Hotspots",
                description="Well-established KRAS G12C hotspot"
            )
        ]
        
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=None
        )
        
        # Should still calculate DSC but with reduced confidence
        assert 0.5 <= dsc_result.dsc_score <= 0.9
        assert dsc_result.vaf_purity_score is None  # Can't calculate without purity
        assert dsc_result.prior_probability_score > 0.7  # Hotspot still gives good prior
        assert dsc_result.dsc_confidence < 1.0  # Reduced confidence due to missing data
        assert "prior_probability" in dsc_result.modules_available
        assert "vaf_purity" not in dsc_result.modules_available
    
    def test_extreme_vaf_scenarios(self):
        """Test DSC for extreme VAF scenarios"""
        # Very high VAF in high purity tumor (suggests loss of heterozygosity)
        high_vaf_variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            vaf=0.85,  # Very high VAF
            tumor_purity=0.9,
            consequence=["nonsense_variant"]
        )
        
        evidence_list = [
            Evidence(
                code="OVS1",
                score=8,
                guideline="VICC_2022",
                source_kb="ClinVar",
                description="Null variant in tumor suppressor"
            )
        ]
        
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            high_vaf_variant, evidence_list, tumor_purity=0.9
        )
        
        # High VAF + high purity + null variant should still be high confidence somatic
        assert dsc_result.dsc_score > 0.8
        assert dsc_result.vaf_purity_score > 0.6  # High VAF can be somatic (LOH)
    
    def test_dsc_confidence_modulation(self):
        """Test DSC confidence modulation based on available evidence"""
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            vaf=0.3,
            tumor_purity=0.7,
            consequence=["missense_variant"]
        )
        
        # Minimal evidence
        minimal_evidence = [
            Evidence(
                code="OP4",
                score=1,
                guideline="VICC_2022",
                source_kb="gnomAD",
                description="Absent from population databases"
            )
        ]
        
        # Rich evidence
        rich_evidence = [
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022",
                source_kb="COSMIC_Hotspots",
                description="Well-established hotspot"
            ),
            Evidence(
                code="OM2",
                score=2,
                guideline="VICC_2022",
                source_kb="CIViC",
                description="Functional studies"
            ),
            Evidence(
                code="OP1",
                score=1,
                guideline="VICC_2022",
                source_kb="dbNSFP",
                description="Computational evidence"
            )
        ]
        
        dsc_minimal = self.dsc_calculator.calculate_dsc_score(
            variant, minimal_evidence, tumor_purity=0.7
        )
        dsc_rich = self.dsc_calculator.calculate_dsc_score(
            variant, rich_evidence, tumor_purity=0.7
        )
        
        # Rich evidence should give higher DSC and confidence
        assert dsc_rich.dsc_score > dsc_minimal.dsc_score
        assert dsc_rich.dsc_confidence > dsc_minimal.dsc_confidence
        assert len(dsc_rich.modules_available) >= len(dsc_minimal.modules_available)


class TestDSCTierRequirements:
    """Test DSC thresholds for tier assignment per TN_VERSUS_TO.md"""
    
    def test_tier_i_dsc_requirement(self):
        """Test that Tier I requires DSC > 0.9"""
        # This would be tested in tier assignment, but verify DSC calculation
        # can achieve > 0.9 for appropriate variants
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            vaf=0.4,
            tumor_purity=0.8,
            hotspot_evidence=[HotspotEvidence(
                source="COSMIC_Hotspots",
                samples_observed=1000,
                cancer_types=["melanoma"],
                hotspot_type="single_residue"
            )]
        )
        
        evidence_list = [
            Evidence(
                code="OS3",
                score=4,
                guideline="VICC_2022", 
                source_kb="COSMIC_Hotspots",
                description="Well-established hotspot BRAF V600E"
            ),
            Evidence(
                code="OS2",
                score=4,
                guideline="AMP_2017",
                source_kb="OncoKB",
                description="FDA-approved biomarker"
            )
        ]
        
        calculator = DynamicSomaticConfidenceCalculator()
        dsc_result = calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=0.8
        )
        
        # Should meet Tier I DSC requirement
        assert dsc_result.dsc_score > 0.9
    
    def test_tier_ii_dsc_requirement(self):
        """Test that Tier II requires DSC > 0.6"""
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            vaf=0.25,
            tumor_purity=0.6
        )
        
        evidence_list = [
            Evidence(
                code="OM1",
                score=2,
                guideline="VICC_2022",
                source_kb="CIViC",
                description="Critical functional domain"
            ),
            Evidence(
                code="OP2",
                score=1,
                guideline="VICC_2022",
                source_kb="COSMIC",
                description="Somatic in multiple tumors"
            )
        ]
        
        calculator = DynamicSomaticConfidenceCalculator()
        dsc_result = calculator.calculate_dsc_score(
            variant, evidence_list, tumor_purity=0.6
        )
        
        # Should meet Tier II DSC requirement
        assert dsc_result.dsc_score > 0.6
        assert dsc_result.dsc_score <= 0.9  # But not Tier I level


if __name__ == "__main__":
    pytest.main([__file__])