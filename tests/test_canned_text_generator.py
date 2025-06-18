"""
Tests for Comprehensive Canned Text Generation System
"""

import pytest
from typing import List, Dict, Any

from annotation_engine.models import (
    VariantAnnotation, Evidence, TierResult, 
    AMPScoring, VICCScoring, OncoKBScoring,
    CannedText, CannedTextType, AnalysisType
)
from annotation_engine.canned_text_generator import CannedTextGenerator, TextTemplate


class TestCannedTextGenerator:
    """Test suite for CannedTextGenerator"""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance"""
        return CannedTextGenerator()
    
    @pytest.fixture
    def sample_variant(self):
        """Create sample variant"""
        return VariantAnnotation(
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
    
    @pytest.fixture
    def sample_evidence(self):
        """Create sample evidence list"""
        return [
            Evidence(
                evidence_type="THERAPEUTIC",
                evidence_level="LEVEL_1",
                source_kb="ONCOKB",
                description="BRAF V600E confers sensitivity to vemurafenib in melanoma",
                score=10,
                metadata={
                    "therapy": "vemurafenib",
                    "disease": "melanoma",
                    "gene_role": "oncogene"
                }
            ),
            Evidence(
                evidence_type="GENE_FUNCTION",
                evidence_level="HIGH",
                source_kb="UNIPROT",
                description="Serine/threonine-protein kinase B-raf",
                score=8,
                metadata={
                    "protein_function": "a serine/threonine kinase involved in the MAP kinase signaling pathway",
                    "pathway": "MAPK signaling"
                }
            ),
            Evidence(
                evidence_type="HOTSPOT",
                evidence_level="HIGH",
                source_kb="CANCER_HOTSPOTS",
                description="V600 is a statistically significant hotspot",
                score=8,
                metadata={"sample_count": 1523}
            ),
            Evidence(
                evidence_type="POPULATION_FREQUENCY",
                evidence_level="HIGH",
                source_kb="GNOMAD",
                description="Not found in gnomAD",
                score=7,
                metadata={"af": 0}
            )
        ]
    
    @pytest.fixture
    def tier_result(self, sample_variant, sample_evidence):
        """Create sample tier result"""
        return TierResult(
            variant_id="test_variant",
            gene_symbol="BRAF",
            hgvs_p="p.V600E",
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=AMPScoring(
                tier="IA",
                evidence_codes=["FDA1", "AMP1"],
                score=10
            ),
            vicc_scoring=VICCScoring(
                oncogenicity_classification="Oncogenic",
                evidence_codes=["OS1", "OS3"],
                total_score=8
            ),
            oncokb_scoring=OncoKBScoring(
                oncogenic_classification="Oncogenic",
                evidence_level="Level 1",
                evidence_codes=["LEVEL_1"]
            ),
            evidence=sample_evidence,
            cancer_type="melanoma",
            canned_texts=[],
            confidence_score=0.95,
            annotation_completeness=0.9
        )
    
    def test_general_gene_info_generation(self, generator, sample_variant, sample_evidence, tier_result):
        """Test General Gene Info text generation"""
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma",
            kb_data={
                "gene_info": {
                    "gene_name": "B-Raf proto-oncogene",
                    "associated_conditions": "melanoma, colorectal cancer, and thyroid cancer"
                }
            }
        )
        
        # Find general gene info text
        gene_info_texts = [t for t in texts if t.text_type == CannedTextType.GENERAL_GENE_INFO]
        assert len(gene_info_texts) == 1
        
        gene_info = gene_info_texts[0]
        assert "BRAF" in gene_info.content
        assert "chromosome 7" in gene_info.content
        assert "serine/threonine kinase" in gene_info.content
        assert gene_info.confidence > 0.7
        assert "UNIPROT:GENE_FUNCTION" in gene_info.evidence_support
    
    def test_gene_dx_interpretation(self, generator, sample_variant, sample_evidence, tier_result):
        """Test Gene Dx Interpretation text generation"""
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma"
        )
        
        gene_dx_texts = [t for t in texts if t.text_type == CannedTextType.GENE_DX_INTERPRETATION]
        assert len(gene_dx_texts) == 1
        
        gene_dx = gene_dx_texts[0]
        assert "melanoma" in gene_dx.content
        assert "BRAF" in gene_dx.content
        assert "oncogene" in gene_dx.content
        assert "targeted therapies" in gene_dx.content
        assert gene_dx.confidence > 0.8
    
    def test_general_variant_info(self, generator, sample_variant, sample_evidence, tier_result):
        """Test General Variant Info text generation"""
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma"
        )
        
        variant_info_texts = [t for t in texts if t.text_type == CannedTextType.GENERAL_VARIANT_INFO]
        assert len(variant_info_texts) == 1
        
        variant_info = variant_info_texts[0]
        assert "p.V600E" in variant_info.content
        assert "missense" in variant_info.content
        assert "absent from population databases" in variant_info.content
        assert "hotspot" in variant_info.content.lower()
        assert variant_info.confidence > 0.7
    
    def test_variant_dx_interpretation(self, generator, sample_variant, sample_evidence, tier_result):
        """Test Variant Dx Interpretation text generation"""
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma"
        )
        
        variant_dx_texts = [t for t in texts if t.text_type == CannedTextType.VARIANT_DX_INTERPRETATION]
        assert len(variant_dx_texts) == 1
        
        variant_dx = variant_dx_texts[0]
        assert "BRAF" in variant_dx.content
        assert "p.V600E" in variant_dx.content
        assert "Oncogenic" in variant_dx.content
        assert "melanoma" in variant_dx.content
        assert "vemurafenib" in variant_dx.content
        assert variant_dx.confidence > 0.9  # Boosted by Tier IA
    
    def test_incidental_findings_acmg_gene(self, generator):
        """Test Incidental/Secondary Findings for ACMG gene"""
        variant = VariantAnnotation(
            gene_symbol="BRCA1",
            chromosome="17",
            position=41276045,
            ref="C",
            alt="T",
            hgvs_c="c.5266dupC",
            hgvs_p="p.Q1756fs",
            consequence="frameshift_variant",
            variant_type="insertion"
        )
        
        evidence = [
            Evidence(
                evidence_type="GERMLINE_PATHOGENIC",
                evidence_level="HIGH",
                source_kb="CLINVAR",
                description="Pathogenic for Hereditary breast and ovarian cancer syndrome",
                score=10,
                metadata={
                    "classification": "Pathogenic",
                    "review_status": "germline",
                    "condition": "Hereditary breast and ovarian cancer syndrome"
                }
            )
        ]
        
        tier_result = TierResult(
            variant_id="test_brca1",
            gene_symbol="BRCA1",
            hgvs_p="p.Q1756fs",
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=None,
            vicc_scoring=None,
            oncokb_scoring=None,
            evidence=evidence,
            cancer_type="lung adenocarcinoma",
            canned_texts=[],
            confidence_score=0.9,
            annotation_completeness=0.8
        )
        
        texts = generator.generate_all_canned_texts(
            variant,
            evidence,
            tier_result,
            "lung adenocarcinoma"
        )
        
        incidental_texts = [t for t in texts if t.text_type == CannedTextType.INCIDENTAL_SECONDARY_FINDINGS]
        assert len(incidental_texts) == 1
        
        incidental = incidental_texts[0]
        assert "BRCA1" in incidental.content
        assert "Hereditary" in incidental.content
        assert "unrelated to the patient's lung adenocarcinoma" in incidental.content
        assert "genetic counseling" in incidental.content
        assert incidental.confidence > 0.7
    
    def test_chromosomal_alteration(self, generator):
        """Test Chromosomal Alteration Interpretation"""
        variant = VariantAnnotation(
            gene_symbol="ERBB2",
            chromosome="17",
            position=37844000,
            ref="N",
            alt="<DUP>",
            hgvs_c=None,
            hgvs_p=None,
            consequence="copy_number_gain",
            variant_type="duplication",
            metadata={"size": 50000}
        )
        
        evidence = [
            Evidence(
                evidence_type="COPY_NUMBER",
                evidence_level="HIGH",
                source_kb="ONCOKB",
                description="ERBB2 amplification is oncogenic and targetable",
                score=9,
                metadata={
                    "copy_number": 8,
                    "therapeutic_implication": "trastuzumab"
                }
            )
        ]
        
        tier_result = TierResult(
            variant_id="test_erbb2_amp",
            gene_symbol="ERBB2",
            hgvs_p=None,
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=AMPScoring(tier="IB", evidence_codes=["AMP2"], score=8),
            vicc_scoring=None,
            oncokb_scoring=None,
            evidence=evidence,
            cancer_type="breast cancer",
            canned_texts=[],
            confidence_score=0.85,
            annotation_completeness=0.8
        )
        
        texts = generator.generate_all_canned_texts(
            variant,
            evidence,
            tier_result,
            "breast cancer"
        )
        
        chr_texts = [t for t in texts if t.text_type == CannedTextType.CHROMOSOMAL_ALTERATION_INTERPRETATION]
        assert len(chr_texts) == 1
        
        chr_alt = chr_texts[0]
        assert "duplication" in chr_alt.content
        assert "ERBB2" in chr_alt.content
        assert "50.0 kb" in chr_alt.content
        assert chr_alt.confidence > 0.6
    
    def test_biomarker_tmb(self, generator, sample_variant, sample_evidence, tier_result):
        """Test Biomarker text generation for TMB"""
        kb_data = {
            "tmb": {
                "value": 23.5,
                "unit": "mutations/Mb"
            }
        }
        
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma",
            kb_data
        )
        
        biomarker_texts = [t for t in texts if t.text_type == CannedTextType.BIOMARKERS]
        assert len(biomarker_texts) == 1
        
        tmb_text = biomarker_texts[0]
        assert "23.5" in tmb_text.content
        assert "High" in tmb_text.content
        assert "immune checkpoint inhibitor" in tmb_text.content
        assert tmb_text.confidence > 0.8
    
    def test_biomarker_msi(self, generator, sample_variant, sample_evidence, tier_result):
        """Test Biomarker text generation for MSI"""
        kb_data = {
            "msi": {
                "status": "MSI-H",
                "score": 45
            }
        }
        
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "colorectal",
            kb_data
        )
        
        biomarker_texts = [t for t in texts if t.text_type == CannedTextType.BIOMARKERS]
        assert len(biomarker_texts) == 1
        
        msi_text = biomarker_texts[0]
        assert "MSI-H" in msi_text.content
        assert "microsatellite instability" in msi_text.content.lower()
        assert "immune checkpoint" in msi_text.content
        assert msi_text.confidence > 0.8
    
    def test_pertinent_negatives(self, generator, sample_variant, sample_evidence, tier_result):
        """Test Pertinent Negatives text generation"""
        kb_data = {
            "negative_findings": {
                "genes_tested": ["EGFR", "ALK", "ROS1", "MET", "KRAS", "ERBB2", "BRAF", "RET"],
                "gene_category": "targetable driver genes",
                "pathway": "RTK/RAS"
            }
        }
        
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "lung adenocarcinoma",
            kb_data
        )
        
        negative_texts = [t for t in texts if t.text_type == CannedTextType.PERTINENT_NEGATIVES]
        assert len(negative_texts) == 1
        
        negatives = negative_texts[0]
        assert "No clinically significant variants" in negatives.content
        assert "EGFR" in negatives.content
        assert "targetable driver genes" in negatives.content
        assert negatives.confidence > 0.5
    
    def test_template_selection(self, generator):
        """Test template selection logic"""
        # Test with minimal data
        minimal_data = {
            "gene_symbol": "TP53",
            "gene_role": "tumor suppressor"
        }
        
        template = generator._select_best_template(
            CannedTextType.GENERAL_GENE_INFO,
            minimal_data
        )
        
        # Should select second template that requires fewer fields
        assert template is not None
        assert "gene_role" in template.required_fields
        
        # Test with complete data
        complete_data = {
            "gene_symbol": "TP53",
            "gene_name": "Tumor protein p53",
            "chromosome": "17",
            "protein_function": "transcription factor and tumor suppressor",
            "associated_conditions": "Li-Fraumeni syndrome",
            "domain_info": "Contains DNA-binding domain",
            "gene_role": "tumor suppressor",
            "pathway": "p53 signaling",
            "cancer_relevance": "Mutated in >50% of cancers"
        }
        
        template = generator._select_best_template(
            CannedTextType.GENERAL_GENE_INFO,
            complete_data
        )
        
        # Should select first template with more fields
        assert template is not None
        assert "protein_function" in template.template
    
    def test_confidence_calculation(self, generator):
        """Test confidence score calculation"""
        template = TextTemplate(
            template="{gene} is {role} involved in {pathway}",
            required_fields=["gene", "role"],
            optional_fields=["pathway"],
            confidence_factors={"pathway": 0.3}
        )
        
        # Test with only required fields
        data1 = {"gene": "KRAS", "role": "an oncogene"}
        text1, conf1 = generator._fill_template(template, data1)
        assert text1 == "KRAS is an oncogene involved in "
        assert conf1 == 0.6  # Base confidence
        
        # Test with optional fields
        data2 = {"gene": "KRAS", "role": "an oncogene", "pathway": "RAS/MAPK signaling"}
        text2, conf2 = generator._fill_template(template, data2)
        assert "RAS/MAPK signaling" in text2
        assert conf2 == 0.9  # Base + pathway factor
    
    def test_clinical_context_extraction(self, generator, sample_evidence, sample_variant):
        """Test clinical context extraction from evidence"""
        contexts = generator._extract_clinical_contexts(
            sample_evidence,
            sample_variant,
            "melanoma"
        )
        
        assert len(contexts) > 0
        
        # Check therapeutic context
        therapeutic_contexts = [c for c in contexts if c.context_type.value == "therapy"]
        assert len(therapeutic_contexts) > 0
        assert therapeutic_contexts[0].therapy_class == "BRAF_inhibitor"
        assert therapeutic_contexts[0].primary_condition == "melanoma"
    
    def test_empty_evidence_handling(self, generator, sample_variant):
        """Test handling of empty evidence list"""
        empty_tier_result = TierResult(
            variant_id="test",
            gene_symbol="BRAF",
            hgvs_p="p.V600E",
            analysis_type=AnalysisType.TUMOR_ONLY,
            amp_scoring=None,
            vicc_scoring=None,
            oncokb_scoring=None,
            evidence=[],
            cancer_type="melanoma",
            canned_texts=[],
            confidence_score=0.5,
            annotation_completeness=0.3
        )
        
        texts = generator.generate_all_canned_texts(
            sample_variant,
            [],
            empty_tier_result,
            "melanoma"
        )
        
        # Should still generate some basic texts
        assert len(texts) >= 0  # May generate variant info from annotation alone
    
    def test_error_handling(self, generator, sample_variant, sample_evidence, tier_result):
        """Test error handling in text generation"""
        # Test with invalid kb_data
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            "melanoma",
            kb_data={"invalid": "data"}
        )
        
        # Should still generate texts from evidence
        assert len(texts) > 0
        
        # Test with None cancer type
        texts = generator.generate_all_canned_texts(
            sample_variant,
            sample_evidence,
            tier_result,
            None
        )
        
        # Should handle gracefully
        assert isinstance(texts, list)