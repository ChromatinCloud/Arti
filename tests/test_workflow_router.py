"""
Test workflow router functionality
"""

import pytest
from annotation_engine.workflow_router import (
    WorkflowRouter, EvidenceSource, create_workflow_router
)
from annotation_engine.models import AnalysisType


class TestWorkflowRouter:
    """Test workflow routing logic"""
    
    def test_tumor_normal_config(self):
        """Test tumor-normal pathway configuration"""
        router = create_workflow_router(AnalysisType.TUMOR_NORMAL)
        
        assert router.pathway.name == "Tumor-Normal Somatic"
        assert router.pathway.analysis_type == AnalysisType.TUMOR_NORMAL
        assert router.pathway.require_normal_comparison is True
        
        # Check KB priorities - clinical should be highest
        priorities = router.get_kb_priority_order()
        assert priorities[0] == EvidenceSource.ONCOKB
        assert priorities[1] == EvidenceSource.FDA_APPROVED
        
        # Check evidence weights
        assert router.get_evidence_weight(EvidenceSource.ONCOKB) == 1.0
        assert router.get_evidence_weight(EvidenceSource.GNOMAD) == 0.2  # Low for T/N
        
        # Check VAF thresholds
        assert router.get_vaf_threshold("min_tumor_vaf") == 0.05
        assert router.get_vaf_threshold("max_normal_vaf") == 0.02
    
    def test_tumor_only_config(self):
        """Test tumor-only pathway configuration"""
        router = create_workflow_router(AnalysisType.TUMOR_ONLY)
        
        assert router.pathway.name == "Tumor-Only Somatic"
        assert router.pathway.analysis_type == AnalysisType.TUMOR_ONLY
        assert router.pathway.require_normal_comparison is False
        
        # Check KB priorities - population DBs should be higher
        priorities = router.get_kb_priority_order()
        # Clinical still first
        assert priorities[0] == EvidenceSource.ONCOKB
        # But population DBs come sooner
        gnomad_index = priorities.index(EvidenceSource.GNOMAD)
        assert gnomad_index < 10  # Should be in top 10 for tumor-only
        
        # Check evidence weights - population DBs weighted higher
        assert router.get_evidence_weight(EvidenceSource.GNOMAD) == 0.7  # Much higher for T/O
        assert router.get_evidence_weight(EvidenceSource.CLINVAR) == 0.6
        
        # Check VAF thresholds - more conservative
        assert router.get_vaf_threshold("min_tumor_vaf") == 0.10
        assert router.get_vaf_threshold("max_population_af") == 0.001
    
    def test_variant_filtering_tumor_normal(self):
        """Test variant filtering for tumor-normal pathway"""
        router = create_workflow_router(AnalysisType.TUMOR_NORMAL)
        
        # Should pass: good somatic variant
        assert not router.should_filter_variant(
            tumor_vaf=0.20, normal_vaf=0.01, population_af=0.0001
        )
        
        # Should filter: too much in normal
        assert router.should_filter_variant(
            tumor_vaf=0.20, normal_vaf=0.05, population_af=0.0001
        )
        
        # Should filter: low tumor VAF
        assert router.should_filter_variant(
            tumor_vaf=0.03, normal_vaf=0.0, population_af=0.0001
        )
        
        # Should pass: hotspot with lower VAF
        assert not router.should_filter_variant(
            tumor_vaf=0.06, normal_vaf=0.0, population_af=0.0001, is_hotspot=True
        )
    
    def test_variant_filtering_tumor_only(self):
        """Test variant filtering for tumor-only pathway"""
        router = create_workflow_router(AnalysisType.TUMOR_ONLY)
        
        # Should pass: good somatic variant
        assert not router.should_filter_variant(
            tumor_vaf=0.20, population_af=0.00001
        )
        
        # Should filter: common variant
        assert router.should_filter_variant(
            tumor_vaf=0.20, population_af=0.01
        )
        
        # Should filter: low VAF (higher threshold for T/O)
        assert router.should_filter_variant(
            tumor_vaf=0.08, population_af=0.0001
        )
        
        # Should pass: hotspot even with population frequency
        assert not router.should_filter_variant(
            tumor_vaf=0.15, population_af=0.002, is_hotspot=True
        )
    
    def test_clonality_classification(self):
        """Test VAF clonality classification"""
        router = create_workflow_router(AnalysisType.TUMOR_NORMAL)
        
        assert router.classify_vaf_clonality(0.45) == "clonal"
        assert router.classify_vaf_clonality(0.15) == "subclonal"
        assert router.classify_vaf_clonality(0.30) == "indeterminate"
    
    def test_evidence_score_adjustment(self):
        """Test evidence score adjustment based on pathway"""
        router = create_workflow_router(AnalysisType.TUMOR_ONLY)
        
        evidence_list = [
            {"source_kb": "OncoKB", "score": 10},
            {"source_kb": "gnomAD", "score": 5},
            {"source_kb": "COSMIC_Hotspot", "score": 8},
        ]
        
        adjusted = router.adjust_evidence_scores(evidence_list)
        
        # OncoKB should maintain full weight
        assert adjusted[0]["adjusted_score"] == 10.0
        assert adjusted[0]["pathway_weight"] == 1.0
        
        # gnomAD should have higher weight in tumor-only
        assert adjusted[1]["adjusted_score"] == 3.5  # 5 * 0.7
        assert adjusted[1]["pathway_weight"] == 0.7
        
        # COSMIC hotspot should have good weight
        assert adjusted[2]["adjusted_score"] == 6.4  # 8 * 0.8
        assert adjusted[2]["pathway_weight"] == 0.8
    
    def test_pathway_summary(self):
        """Test pathway summary generation"""
        router = create_workflow_router(AnalysisType.TUMOR_NORMAL, tumor_type="LUAD")
        summary = router.get_pathway_summary()
        
        assert summary["pathway_name"] == "Tumor-Normal Somatic"
        assert summary["analysis_type"] == "TUMOR_NORMAL"
        assert summary["tumor_type"] == "LUAD"
        assert summary["min_coverage"] == 50
        assert len(summary["top_5_kb_priorities"]) == 5
        assert summary["flags"]["use_population_filtering"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])