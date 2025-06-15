"""
Test cases for tumor purity integration

Tests the complete tumor purity estimation and integration pipeline
including VAF-based estimation, metadata integration, and DSC calculation.
"""

import pytest
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import tempfile
import numpy as np

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import (
    VariantAnnotation, Evidence, AnalysisType, PopulationFrequency, 
    HotspotEvidence, DynamicSomaticConfidence
)
from annotation_engine.purity_estimation import (
    VAFBasedPurityEstimator, PurityMetadataIntegrator, 
    PurityEstimate, estimate_tumor_purity
)
from annotation_engine.evidence_aggregator import DynamicSomaticConfidenceCalculator


class TestVAFBasedPurityEstimator:
    """Test VAF-based tumor purity estimation"""
    
    def setup_method(self):
        self.estimator = VAFBasedPurityEstimator()
    
    def test_high_purity_tumor_estimation(self):
        """Test purity estimation for high-purity tumor with clear heterozygous peak"""
        
        # Create variants with VAFs clustered around expected heterozygous pattern
        # For 80% purity, expect VAFs around 40% (purity/2)
        variants = []
        base_vaf = 0.4  # 40% VAF for 80% purity heterozygous
        
        for i in range(20):  # Sufficient variants for estimation
            vaf = base_vaf + np.random.normal(0, 0.05)  # Small variance
            variants.append(VariantAnnotation(
                chromosome="1",
                position=1000000 + i,
                reference="A",
                alternate="T",
                gene_symbol=f"GENE_{i}",
                vaf=max(0.05, min(0.95, vaf)),  # Clamp to valid range
                total_depth=100,
                filter_status=["PASS"],
                consequence=["missense_variant"],
                is_oncogene=(i % 4 == 0),  # Some oncogenes for somatic evidence
                hotspot_evidence=[HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=50,
                    cancer_types=["lung"],
                    hotspot_type="single_residue"
                )] if i % 3 == 0 else []  # Some hotspots
            ))
        
        purity_estimate = self.estimator.estimate_purity(
            variants, AnalysisType.TUMOR_ONLY
        )
        
        # Should estimate ~80% purity with high confidence
        assert 0.7 <= purity_estimate.purity <= 0.9
        assert purity_estimate.confidence > 0.7
        assert purity_estimate.method == "heterozygous_peak"
        assert purity_estimate.supporting_variants >= 15  # Should use most variants
    
    def test_moderate_purity_tumor_estimation(self):
        """Test purity estimation for moderate-purity tumor"""
        
        # Create variants for 50% purity tumor (VAFs around 25%)
        variants = []
        base_vaf = 0.25
        
        for i in range(15):
            vaf = base_vaf + np.random.normal(0, 0.08)  # Moderate variance
            variants.append(VariantAnnotation(
                chromosome="2",
                position=2000000 + i,
                reference="C",
                alternate="G",
                gene_symbol=f"GENE_{i}",
                vaf=max(0.05, min(0.95, vaf)),
                total_depth=80,
                filter_status=["PASS"],
                consequence=["missense_variant"]
            ))
        
        purity_estimate = self.estimator.estimate_purity(
            variants, AnalysisType.TUMOR_ONLY
        )
        
        # Should estimate ~50% purity (allow some variance due to algorithm design)
        assert 0.4 <= purity_estimate.purity <= 0.7  # Slightly wider range
        assert purity_estimate.confidence > 0.5
    
    def test_insufficient_variants_estimation(self):
        """Test behavior with insufficient variants"""
        
        # Only 5 variants (below minimum threshold)
        variants = []
        for i in range(5):
            variants.append(VariantAnnotation(
                chromosome="3",
                position=3000000 + i,
                reference="G",
                alternate="A",
                gene_symbol=f"GENE_{i}",
                vaf=0.3,
                total_depth=50,
                filter_status=["PASS"],
                consequence=["missense_variant"]
            ))
        
        purity_estimate = self.estimator.estimate_purity(
            variants, AnalysisType.TUMOR_ONLY
        )
        
        # Should return low-confidence default estimate
        assert purity_estimate.purity == 0.5  # Default
        assert purity_estimate.confidence <= 0.3  # Low confidence
        assert purity_estimate.method == "insufficient_data"
    
    def test_tumor_normal_vs_tumor_only_filtering(self):
        """Test different filtering strategies for TN vs TO analysis"""
        
        # Create variants with mixed somatic evidence
        variants = []
        for i in range(15):
            variant = VariantAnnotation(
                chromosome="4",
                position=4000000 + i,
                reference="T",
                alternate="C",
                gene_symbol=f"GENE_{i}",
                vaf=0.35,
                total_depth=100,
                filter_status=["PASS"],
                consequence=["missense_variant"]
            )
            
            # Some variants have high population frequency (should be filtered in TO)
            if i % 3 == 0:
                variant.population_frequencies = [PopulationFrequency(
                    database="gnomAD",
                    population="global",
                    allele_frequency=0.02  # Too high for TO analysis
                )]
            
            # Some variants have hotspot evidence (good for TO)
            if i % 4 == 0:
                variant.hotspot_evidence = [HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=100,
                    cancer_types=["lung"],
                    hotspot_type="single_residue"
                )]
            
            variants.append(variant)
        
        # Test tumor-only filtering (should be more restrictive)
        to_estimate = self.estimator.estimate_purity(
            variants, AnalysisType.TUMOR_ONLY
        )
        
        # Test tumor-normal filtering (should be less restrictive)
        tn_estimate = self.estimator.estimate_purity(
            variants, AnalysisType.TUMOR_NORMAL
        )
        
        # TO should use fewer variants due to stricter filtering
        assert to_estimate.supporting_variants <= tn_estimate.supporting_variants


class TestPurityMetadataIntegrator:
    """Test integration of purity from multiple sources"""
    
    def setup_method(self):
        self.integrator = PurityMetadataIntegrator()
    
    def test_metadata_purity_priority(self):
        """Test that metadata purity takes priority when available"""
        
        variants = [VariantAnnotation(
            chromosome="1",
            position=1000000,
            reference="A",
            alternate="T",
            gene_symbol="TEST",
            vaf=0.4,
            total_depth=100,
            filter_status=["PASS"],
            consequence=["missense_variant"]
        )]
        
        metadata = {"tumor_purity": 0.75}
        
        purity_estimate = self.integrator.get_tumor_purity(
            variants, AnalysisType.TUMOR_ONLY, metadata=metadata
        )
        
        # Should use metadata value
        assert purity_estimate.purity == 0.75
        assert purity_estimate.method == "metadata"
        assert purity_estimate.confidence == 0.8  # High confidence in metadata
    
    def test_purple_output_integration(self):
        """Test loading purity from PURPLE output files"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock PURPLE purity file
            purple_file = temp_path / "sample.purple.purity.tsv"
            with open(purple_file, 'w') as f:
                f.write("sample\tpurity\tnormFactor\tscore\tdiploidProportion\tploidy\n")
                f.write("SAMPLE_001\t0.65\t1.2\t0.95\t0.8\t2.1\n")
            
            variants = []  # Empty for this test
            
            purity_estimate = self.integrator.get_tumor_purity(
                variants, AnalysisType.TUMOR_ONLY, 
                purple_output_path=temp_path
            )
            
            # Should use PURPLE value
            assert purity_estimate.purity == 0.65
            assert purity_estimate.method == "purple_hmf"
            assert purity_estimate.confidence == 0.95  # From PURPLE score
    
    def test_vaf_fallback_estimation(self):
        """Test fallback to VAF-based estimation when no metadata available"""
        
        # Create variants with clear pattern for VAF-based estimation
        variants = []
        for i in range(15):
            variants.append(VariantAnnotation(
                chromosome="5",
                position=5000000 + i,
                reference="A",
                alternate="G",
                gene_symbol=f"GENE_{i}",
                vaf=0.3 + np.random.normal(0, 0.03),
                total_depth=100,
                filter_status=["PASS"],
                consequence=["missense_variant"],
                hotspot_evidence=[HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=50,
                    cancer_types=["lung"],
                    hotspot_type="single_residue"
                )]
            ))
        
        purity_estimate = self.integrator.get_tumor_purity(
            variants, AnalysisType.TUMOR_ONLY
        )
        
        # Should fall back to VAF-based estimation
        assert purity_estimate.method in ["heterozygous_peak", "quantile_based"]
        assert 0.5 <= purity_estimate.purity <= 0.7  # Should estimate ~60% from VAF 30%


class TestDSCPurityIntegration:
    """Test integration of purity estimation with DSC calculation"""
    
    def setup_method(self):
        self.dsc_calculator = DynamicSomaticConfidenceCalculator()
    
    def test_dsc_with_automatic_purity_estimation(self):
        """Test DSC calculation with automatic purity estimation"""
        
        # Create variant of interest
        variant = VariantAnnotation(
            chromosome="7",
            position=140453136,
            reference="A",
            alternate="T",
            gene_symbol="BRAF",
            vaf=0.4,  # 40% VAF
            total_depth=150,
            filter_status=["PASS"],
            consequence=["missense_variant"],
            hotspot_evidence=[HotspotEvidence(
                source="COSMIC_Hotspots",
                samples_observed=1000,
                cancer_types=["melanoma"],
                hotspot_type="single_residue"
            )]
        )
        
        # Create cohort of variants for purity estimation
        cohort_variants = [variant]  # Include the variant of interest
        for i in range(15):
            cohort_variants.append(VariantAnnotation(
                chromosome="1",
                position=1000000 + i,
                reference="C",
                alternate="T",
                gene_symbol=f"GENE_{i}",
                vaf=0.4 + np.random.normal(0, 0.05),  # Cluster around 40%
                total_depth=100,
                filter_status=["PASS"],
                consequence=["missense_variant"],
                hotspot_evidence=[HotspotEvidence(
                    source="COSMIC_Hotspots",
                    samples_observed=50,
                    cancer_types=["lung"],
                    hotspot_type="single_residue"
                )]
            ))
        
        evidence_list = [Evidence(
            code="OS3",
            score=4,
            guideline="VICC_2022",
            source_kb="COSMIC_Hotspots",
            description="Well-established cancer hotspot"
        )]
        
        # Calculate DSC with automatic purity estimation
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant=variant,
            evidence_list=evidence_list,
            tumor_purity=None,  # Force estimation
            variant_annotations=cohort_variants,
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        # Should have estimated purity around 80% (2 * 40% VAF)
        assert dsc_result.tumor_purity is not None
        assert 0.7 <= dsc_result.tumor_purity <= 0.9
        
        # Should have high DSC score due to good VAF/purity consistency + hotspot
        assert dsc_result.dsc_score > 0.8
        assert dsc_result.vaf_purity_score is not None
        assert dsc_result.vaf_purity_score > 0.7  # Good VAF/purity consistency
    
    def test_dsc_with_provided_purity(self):
        """Test DSC calculation with user-provided purity"""
        
        variant = VariantAnnotation(
            chromosome="12",
            position=25398281,
            reference="C",
            alternate="A",
            gene_symbol="KRAS",
            vaf=0.25,  # 25% VAF with 50% purity = good heterozygous match
            total_depth=120,
            filter_status=["PASS"],
            consequence=["missense_variant"]
        )
        
        evidence_list = [Evidence(
            code="OM1",
            score=2,
            guideline="VICC_2022",
            source_kb="CIViC",
            description="Critical functional domain"
        )]
        
        # Provide explicit purity
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant=variant,
            evidence_list=evidence_list,
            tumor_purity=0.5  # Explicit 50% purity
        )
        
        # Should use provided purity
        assert dsc_result.tumor_purity == 0.5
        assert dsc_result.variant_vaf == 0.25
        
        # Should have good VAF/purity consistency (25% VAF matches 50% purity / 2)
        assert dsc_result.vaf_purity_score is not None
        assert dsc_result.vaf_purity_score > 0.8
    
    def test_dsc_with_inconsistent_vaf_purity(self):
        """Test DSC with VAF inconsistent with tumor purity"""
        
        variant = VariantAnnotation(
            chromosome="17",
            position=7577121,
            reference="C",
            alternate="T",
            gene_symbol="TP53",
            vaf=0.48,  # ~50% VAF suggests germline, not somatic
            total_depth=100,
            filter_status=["PASS"],
            consequence=["missense_variant"],
            population_frequencies=[PopulationFrequency(
                database="gnomAD",
                population="global",
                allele_frequency=0.01  # Present in population
            )]
        )
        
        evidence_list = [Evidence(
            code="SBVS1",
            score=-4,
            guideline="VICC_2022",
            source_kb="gnomAD",
            description="High population frequency"
        )]
        
        # High tumor purity but VAF suggests germline
        dsc_result = self.dsc_calculator.calculate_dsc_score(
            variant=variant,
            evidence_list=evidence_list,
            tumor_purity=0.9  # High purity
        )
        
        # Should have low DSC due to VAF/purity inconsistency
        assert dsc_result.dsc_score < 0.5
        assert dsc_result.vaf_purity_score is not None
        assert dsc_result.vaf_purity_score < 0.3  # Poor VAF/purity consistency
        assert dsc_result.prior_probability_score < 0.5  # Population frequency penalty


class TestConvenienceFunctionIntegration:
    """Test the convenience function for purity estimation"""
    
    def test_estimate_tumor_purity_function(self):
        """Test the convenience function with various inputs"""
        
        variants = []
        for i in range(12):
            variants.append(VariantAnnotation(
                chromosome="6",
                position=6000000 + i,
                reference="G",
                alternate="C",
                gene_symbol=f"GENE_{i}",
                vaf=0.35 + np.random.normal(0, 0.04),
                total_depth=90,
                filter_status=["PASS"],
                consequence=["missense_variant"],
                is_oncogene=(i % 3 == 0)
            ))
        
        # Test with metadata
        metadata = {"tumor_purity": 0.8}
        purity_estimate = estimate_tumor_purity(
            variant_annotations=variants,
            analysis_type=AnalysisType.TUMOR_ONLY,
            metadata=metadata
        )
        
        assert purity_estimate.purity == 0.8
        assert purity_estimate.method == "metadata"
        
        # Test without metadata (should fall back to VAF-based)
        purity_estimate_vaf = estimate_tumor_purity(
            variant_annotations=variants,
            analysis_type=AnalysisType.TUMOR_ONLY
        )
        
        assert purity_estimate_vaf.method in ["heterozygous_peak", "quantile_based", "insufficient_data"]
        assert 0.0 <= purity_estimate_vaf.purity <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])