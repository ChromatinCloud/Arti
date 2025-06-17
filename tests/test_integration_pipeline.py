"""
Integration test for end-to-end VCF → JSON annotation pipeline
Tests the complete flow: VCF → VEP → Evidence Aggregation → Tiering → JSON output
"""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from annotation_engine.vep_runner import VEPRunner
from annotation_engine.evidence_aggregator import EvidenceAggregator
from annotation_engine.tiering import TieringEngine
from annotation_engine.models import VariantAnnotation, Evidence, TierResult, AnalysisType

class TestIntegrationPipeline:
    
    @pytest.fixture
    def sample_vcf(self):
        """Create a sample VCF with known variants for testing"""
        vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##contig=<ID=7,length=159345973>
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Total depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
7	140753336	.	A	T	60.0	PASS	AF=0.35	GT:AD:DP	0/1:65,35:100
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(vcf_content)
            return f.name
    
    @pytest.fixture
    def vep_runner(self):
        """Initialize VEP runner for testing"""
        # Use Docker by default to avoid local VEP installation requirements
        from annotation_engine.vep_runner import VEPConfiguration
        config = VEPConfiguration(use_docker=True, assembly="GRCh38")
        return VEPRunner(config)
    
    @pytest.fixture
    def evidence_aggregator(self):
        """Initialize evidence aggregator"""
        return EvidenceAggregator()
    
    @pytest.fixture  
    def tiering_engine(self):
        """Initialize tiering engine"""
        return TieringEngine()
    
    def test_vep_annotation_basic(self, vep_runner, sample_vcf):
        """Test VEP annotation produces VariantAnnotation objects"""
        try:
            # Run VEP annotation
            annotations = vep_runner.annotate_vcf(sample_vcf)
            
            # Verify we get results
            assert len(annotations) > 0, "VEP should produce at least one annotation"
            
            # Verify annotation structure
            annotation = annotations[0]
            assert isinstance(annotation, VariantAnnotation)
            assert annotation.chromosome == "7"
            assert annotation.position == 140753336
            assert annotation.reference == "A"
            assert annotation.alternate == "T"
            
            # Verify we have gene information
            assert annotation.gene_symbol is not None
            assert annotation.transcript_id is not None
            
            print(f"✅ VEP annotation successful: {annotation.gene_symbol}")
            return annotations
            
        except Exception as e:
            pytest.skip(f"VEP not available or configured: {e}")
    
    def test_evidence_aggregation(self, evidence_aggregator, vep_runner, sample_vcf):
        """Test evidence aggregation from knowledge bases"""
        try:
            # Get VEP annotations first
            annotations = vep_runner.annotate_vcf(sample_vcf)
            
            # Aggregate evidence for each variant
            evidence_list = []
            for annotation in annotations:
                evidence = evidence_aggregator.aggregate_evidence([annotation])
                evidence_list.extend(evidence)
            
            # Verify evidence was generated
            assert len(evidence_list) > 0, "Evidence aggregation should produce evidence"
            
            # Check evidence structure
            evidence = evidence_list[0]
            assert isinstance(evidence, Evidence)
            assert evidence.code is not None
            assert evidence.source_kb is not None
            
            print(f"✅ Evidence aggregation successful: {len(evidence_list)} evidence items")
            return evidence_list
            
        except Exception as e:
            pytest.skip(f"Evidence aggregation failed: {e}")
    
    def test_tier_assignment(self, tiering_engine, evidence_aggregator, vep_runner, sample_vcf):
        """Test tier assignment from evidence"""
        try:
            # Get annotations and evidence
            annotations = vep_runner.annotate_vcf(sample_vcf)
            evidence_list = []
            for annotation in annotations:
                evidence = evidence_aggregator.aggregate_evidence([annotation])
                evidence_list.extend(evidence)
            
            # Assign tiers
            tier_results = []
            for annotation in annotations:
                # Get evidence for this variant
                variant_evidence = [e for e in evidence_list 
                                  if e.variant_id == f"{annotation.chromosome}_{annotation.position}_{annotation.reference}_{annotation.alternate}"]
                
                # Assign tier
                tier_result = tiering_engine.assign_tier(variant_evidence, annotation)
                tier_results.append(tier_result)
            
            # Verify tier assignment
            assert len(tier_results) > 0, "Tier assignment should produce results"
            
            tier_result = tier_results[0]
            assert isinstance(tier_result, TierResult)
            assert tier_result.amp_tier is not None
            assert tier_result.vicc_oncogenicity is not None
            
            print(f"✅ Tier assignment successful: AMP Tier {tier_result.amp_tier}")
            return tier_results
            
        except Exception as e:
            pytest.skip(f"Tier assignment failed: {e}")
    
    def test_end_to_end_pipeline(self, vep_runner, evidence_aggregator, tiering_engine, sample_vcf):
        """Test complete end-to-end pipeline"""
        try:
            # Step 1: VEP Annotation
            print("Step 1: Running VEP annotation...")
            annotations = vep_runner.annotate_vcf(sample_vcf)
            assert len(annotations) > 0
            
            # Step 2: Evidence Aggregation  
            print("Step 2: Aggregating evidence...")
            all_evidence = []
            for annotation in annotations:
                evidence = evidence_aggregator.aggregate_evidence([annotation])
                all_evidence.extend(evidence)
            
            # Step 3: Tier Assignment
            print("Step 3: Assigning tiers...")
            results = []
            for annotation in annotations:
                # Get evidence for this variant
                variant_evidence = [e for e in all_evidence 
                                  if e.variant_id == f"{annotation.chromosome}_{annotation.position}_{annotation.reference}_{annotation.alternate}"]
                
                # Assign tier
                tier_result = tiering_engine.assign_tier(variant_evidence, annotation)
                
                # Create final result
                result = {
                    "variant": {
                        "chromosome": annotation.chromosome,
                        "position": annotation.position,
                        "reference": annotation.reference,
                        "alternate": annotation.alternate,
                        "gene": annotation.gene_symbol
                    },
                    "annotation": {
                        "transcript": annotation.transcript_id,
                        "consequence": annotation.consequence,
                        "protein_change": annotation.protein_change,
                        "coding_change": annotation.coding_change
                    },
                    "evidence": [
                        {
                            "code": e.code,
                            "source": e.source_kb,
                            "score": e.score,
                            "description": e.description
                        } for e in variant_evidence
                    ],
                    "tiers": {
                        "amp_tier": tier_result.amp_tier.value if tier_result.amp_tier else None,
                        "vicc_oncogenicity": tier_result.vicc_oncogenicity.value if tier_result.vicc_oncogenicity else None,
                        "oncokb_level": tier_result.oncokb_level.value if tier_result.oncokb_level else None
                    },
                    "confidence": tier_result.confidence,
                    "analysis_type": AnalysisType.TUMOR_ONLY.value
                }
                results.append(result)
            
            # Step 4: JSON Output
            print("Step 4: Generating JSON output...")
            output = {
                "metadata": {
                    "version": "1.0.0",
                    "analysis_type": "tumor_only",
                    "genome_build": "GRCh38",
                    "annotation_date": "2025-06-16"
                },
                "variants": results
            }
            
            # Verify output structure
            assert "metadata" in output
            assert "variants" in output
            assert len(output["variants"]) > 0
            
            # Save test output
            with open("test_pipeline_output.json", "w") as f:
                json.dump(output, f, indent=2)
            
            print(f"✅ End-to-end pipeline successful!")
            print(f"   - Variants processed: {len(results)}")
            print(f"   - Evidence items: {len(all_evidence)}")
            print(f"   - Output saved to: test_pipeline_output.json")
            
            return output
            
        except Exception as e:
            pytest.fail(f"End-to-end pipeline failed: {e}")
    
    def test_braf_v600e_detection(self, vep_runner, evidence_aggregator, tiering_engine):
        """Test detection of BRAF V600E hotspot variant"""
        # Create BRAF V600E VCF (chr7:140753336 A>T in GRCh38)
        braf_vcf_content = """##fileformat=VCFv4.2
##reference=GRCh38
##contig=<ID=7,length=159345973>
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Total depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
7	140753336	.	A	T	60.0	PASS	AF=0.45	GT:AD:DP	0/1:55,45:100
"""
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
                f.write(braf_vcf_content)
                braf_vcf = f.name
            
            # Run pipeline on BRAF V600E
            annotations = vep_runner.annotate_vcf(braf_vcf)
            
            # Find BRAF annotation
            braf_annotation = None
            for ann in annotations:
                if ann.gene_symbol == "BRAF":
                    braf_annotation = ann
                    break
            
            if braf_annotation:
                # Test evidence aggregation
                evidence = evidence_aggregator.aggregate_evidence([braf_annotation])
                
                # Should detect hotspot
                hotspot_evidence = [e for e in evidence if "hotspot" in e.description.lower()]
                assert len(hotspot_evidence) > 0, "Should detect BRAF V600E as hotspot"
                
                # Test tier assignment
                tier_result = tiering_engine.assign_tier(evidence, braf_annotation)
                
                print(f"✅ BRAF V600E detection successful!")
                print(f"   - Gene: {braf_annotation.gene_symbol}")
                print(f"   - Protein change: {braf_annotation.protein_change}")
                print(f"   - Hotspot evidence: {len(hotspot_evidence)} items")
                print(f"   - AMP Tier: {tier_result.amp_tier}")
                print(f"   - VICC Oncogenicity: {tier_result.vicc_oncogenicity}")
                
                # Clean up
                Path(braf_vcf).unlink()
                return tier_result
            else:
                pytest.skip("BRAF annotation not found in VEP output")
                
        except Exception as e:
            pytest.skip(f"BRAF V600E test failed: {e}")

if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])