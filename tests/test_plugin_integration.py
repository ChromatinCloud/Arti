"""
Test VEP plugin integration and data extraction
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.annotation_engine.vep_runner import VEPRunner, VEPConfiguration
from src.annotation_engine.evidence_aggregator import EvidenceAggregator
from src.annotation_engine.models import VariantAnnotation, AnalysisType


class TestPluginIntegration:
    """Test VEP plugin data extraction and evidence processing"""
    
    def test_plugin_data_extraction(self):
        """Test that VEP plugin data is correctly extracted"""
        
        # Mock VEP JSON output with plugin data
        mock_vep_output = {
            "id": "test_variant",
            "input": "1\t100\t.\tA\tT\t.\t.\t.",
            "most_severe_consequence": "missense_variant",
            "transcript_consequences": [
                {
                    "canonical": 1,
                    "gene_symbol": "TEST_GENE",
                    "transcript_id": "ENST00000001",
                    "consequence_terms": ["missense_variant"],
                    "hgvsc": "c.100A>T",
                    "hgvsp": "p.Lys34Asn",
                    "impact": "MODERATE",
                    
                    # Mock plugin outputs
                    "alphamissense_score": 0.8,
                    "alphamissense_prediction": "pathogenic",
                    "revel_score": 0.7,
                    "spliceai_pred_ds_ag": 0.1,
                    "spliceai_pred_ds_al": 0.05,
                    "spliceai_pred_ds_dg": 0.02,
                    "spliceai_pred_ds_dl": 0.03,
                    "gerp_rs": 5.2,
                    "ada_score": 0.3,
                    "rf_score": 0.25
                }
            ],
            "colocated_variants": []
        }
        
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            runner = VEPRunner()
            
            # Test plugin data extraction
            annotation = runner._create_variant_annotation_from_vep(mock_vep_output)
            
            assert annotation is not None
            assert annotation.plugin_data is not None
            
            # Check pathogenicity scores
            path_scores = annotation.plugin_data.get("pathogenicity_scores", {})
            assert "alphamissense" in path_scores
            assert path_scores["alphamissense"]["score"] == 0.8
            assert path_scores["alphamissense"]["prediction"] == "pathogenic"
            assert "revel" in path_scores
            assert path_scores["revel"]["score"] == 0.7
            
            # Check splicing scores
            splice_scores = annotation.plugin_data.get("splicing_scores", {})
            assert "spliceai" in splice_scores
            spliceai_data = splice_scores["spliceai"]
            assert spliceai_data["ds_ag"] == 0.1
            assert spliceai_data["ds_al"] == 0.05
            
            # Check conservation data
            conservation = annotation.plugin_data.get("conservation_data", {})
            assert conservation.get("gerp") == 5.2
            
    def test_evidence_aggregator_plugin_processing(self):
        """Test that evidence aggregator correctly processes plugin data"""
        
        # Create a variant annotation with plugin data
        variant = VariantAnnotation(
            chromosome="1",
            position=100,
            reference="A",
            alternate="T",
            gene_symbol="TEST_GENE",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.8, "prediction": "pathogenic"},
                    "revel": {"score": 0.7},
                    "eve": {"score": 0.6, "class": "pathogenic"}
                },
                "splicing_scores": {
                    "spliceai": {
                        "ds_ag": 0.9,  # High splicing disruption
                        "ds_al": 0.1,
                        "ds_dg": 0.05,
                        "ds_dl": 0.02
                    }
                },
                "conservation_data": {
                    "gerp": 5.5,  # Highly conserved
                    "loftool": 0.05  # Loss-of-function intolerant
                }
            }
        )
        
        aggregator = EvidenceAggregator()
        evidence_list = aggregator._get_functional_prediction_evidence(variant, AnalysisType.TUMOR_ONLY)
        
        # Should have evidence from multiple sources
        assert len(evidence_list) > 0
        
        # Check for high-evidence pathogenicity predictions
        pathogenic_evidence = [e for e in evidence_list if e.code == "OP1_HIGH"]
        assert len(pathogenic_evidence) >= 2  # AlphaMissense and EVE should both contribute
        
        # Check for splicing evidence
        splice_evidence = [e for e in evidence_list if e.code == "OP2_SPLICE"]
        assert len(splice_evidence) >= 1  # SpliceAI should contribute
        
        # Check confidence scores are appropriate
        for evidence in evidence_list:
            assert evidence.confidence > 0.0
            assert evidence.confidence <= 1.0
            
    def test_consensus_evidence_generation(self):
        """Test consensus evidence from multiple predictors"""
        
        # Variant with strong consensus for pathogenic
        variant = VariantAnnotation(
            chromosome="1",
            position=100,
            reference="A",
            alternate="T",
            gene_symbol="TEST_GENE",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": 0.8},  # pathogenic
                    "revel": {"score": 0.7},          # pathogenic
                    "eve": {"score": 0.6},            # pathogenic
                    "varity": {"score": 0.8},         # pathogenic
                    "bayesdel": {"score": 0.1}        # benign
                }
            }
        )
        
        aggregator = EvidenceAggregator()
        evidence_list = aggregator._get_functional_prediction_evidence(variant, AnalysisType.TUMOR_ONLY)
        
        # Should have consensus evidence
        consensus_evidence = [e for e in evidence_list if e.code == "OP1_CONSENSUS"]
        assert len(consensus_evidence) == 1  # Strong pathogenic consensus
        
        consensus = consensus_evidence[0]
        assert consensus.score == 2  # High evidence score
        assert "4/5" in consensus.description  # 4 out of 5 predictors agree
        
    def test_plugin_fallback_handling(self):
        """Test handling when plugin data is missing or malformed"""
        
        # Variant with no plugin data
        variant_no_plugins = VariantAnnotation(
            chromosome="1",
            position=100,
            reference="A",
            alternate="T",
            gene_symbol="TEST_GENE",
            consequence=["missense_variant"],
            plugin_data={}
        )
        
        aggregator = EvidenceAggregator()
        evidence_list = aggregator._get_functional_prediction_evidence(variant_no_plugins, AnalysisType.TUMOR_ONLY)
        
        # Should handle gracefully with no evidence
        assert isinstance(evidence_list, list)
        assert len(evidence_list) == 0
        
        # Variant with malformed plugin data
        variant_malformed = VariantAnnotation(
            chromosome="1",
            position=100,
            reference="A",
            alternate="T",
            gene_symbol="TEST_GENE",
            consequence=["missense_variant"],
            plugin_data={
                "pathogenicity_scores": {
                    "alphamissense": {"score": "invalid_score"},  # Invalid data
                    "revel": {"score": None},                     # Null data
                }
            }
        )
        
        evidence_list = aggregator._get_functional_prediction_evidence(variant_malformed, AnalysisType.TUMOR_ONLY)
        
        # Should handle gracefully without crashing
        assert isinstance(evidence_list, list)
        # May have some evidence if any data is valid, but shouldn't crash


if __name__ == "__main__":
    pytest.main([__file__])