"""
End-to-end workflow tests

Tests the complete annotation pipeline from VCF input to tier results,
validating the integration of all components including filtering,
variant processing, evidence aggregation, and tier assignment.
"""

import pytest
import tempfile
import json
from pathlib import Path
import sys
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.models import AnalysisType, AMPTierLevel
from annotation_engine.cli import AnnotationEngineCLI


class TestEndToEndWorkflow:
    """Test complete annotation workflows from CLI to results"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.cli = AnnotationEngineCLI()
    
    def _create_mock_vcf(self, filepath: Path, variants: List[Dict[str, Any]]):
        """Create a mock VCF file with test variants"""
        with open(filepath, 'w') as f:
            # Write VCF header
            f.write("##fileformat=VCFv4.2\n")
            f.write("##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n")
            f.write("##FORMAT=<ID=AD,Number=R,Type=Integer,Description=\"Allelic depths\">\n")
            f.write("##FORMAT=<ID=DP,Number=1,Type=Integer,Description=\"Read depth\">\n")
            f.write("##INFO=<ID=AF,Number=A,Type=Float,Description=\"Allele frequency\">\n")
            f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n")
            
            # Write variant records
            for variant in variants:
                chrom = variant.get('chrom', '7')
                pos = variant.get('pos', '140453136')
                ref = variant.get('ref', 'A')
                alt = variant.get('alt', 'T')
                qual = variant.get('qual', '60')
                filt = variant.get('filter', 'PASS')
                info = variant.get('info', 'AF=0.45')
                fmt = variant.get('format', 'GT:AD:DP')
                sample = variant.get('sample', '0/1:25,20:45')
                
                f.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t{qual}\t{filt}\t{info}\t{fmt}\t{sample}\n")
    
    @patch('annotation_engine.vep_runner.VEPRunner.annotate_vcf')
    def test_tumor_only_workflow(self, mock_vep_annotate):
        """Test complete tumor-only workflow from CLI to results"""
        
        # Import needed for mocking
        from annotation_engine.models import VariantAnnotation
        
        # Setup mock VEP annotation return
        mock_vep_annotate.return_value = [
            VariantAnnotation(
                chromosome="7",
                position=140753336,
                reference="A",
                alternate="T",
                gene_symbol="BRAF",
                transcript_id="ENST00000288602",
                consequence=["missense_variant"],
                hgvs_p="p.Val600Glu",
                hgvs_c="c.1799T>A",
                vaf=0.45,
                total_depth=45,
                tumor_vaf=0.45
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF file with GRCh38 coordinates
            vcf_file = temp_path / "tumor.vcf"
            self._create_mock_vcf(vcf_file, [
                {
                    'chrom': '7',
                    'pos': '140753336',  # GRCh38 coordinate for BRAF V600E
                    'ref': 'A',
                    'alt': 'T',
                    'info': 'AF=0.45',
                    'sample': '0/1:25,20:45'
                }
            ])
            
            # Create output directory
            output_dir = temp_path / "results"
            
            # Setup CLI arguments
            args = [
                '--input', str(vcf_file),
                '--case-uid', 'TEST_001',
                '--cancer-type', 'melanoma',
                '--output', str(output_dir),
                '--tumor-purity', '0.8'
            ]
            
            # Execute CLI
            with patch('sys.argv', ['annotation-engine'] + args):
                result = self.cli.run()
            
            # Verify successful execution
            assert result == 0
            
            # Verify VEP was called
            mock_vep_annotate.assert_called_once()
            
            # Verify output files were created
            results_file = output_dir / "annotation_results.json"
            assert results_file.exists()
            
            # Verify results content
            with open(results_file) as f:
                results = json.load(f)
            
            assert results['metadata']['total_variants'] == 1
            assert results['metadata']['analysis_type'] == 'TUMOR_ONLY'
            assert len(results['variants']) == 1
            
            # Check first variant
            variant = results['variants'][0]
            assert variant['gene_annotation']['gene_symbol'] == 'BRAF'
            assert variant['variant_id'] == '7_140753336_A_T'
    
    @patch('annotation_engine.vep_runner.VEPRunner.annotate_vcf')
    def test_tumor_normal_workflow(self, mock_vep_annotate):
        """Test complete tumor-normal workflow from CLI to results"""
        
        # Import needed for mocking
        from annotation_engine.models import VariantAnnotation
        
        # Setup mock VEP annotation return
        mock_vep_annotate.return_value = [
            VariantAnnotation(
                chromosome="17",
                position=7674220,  # GRCh38 coordinate
                reference="G",
                alternate="A",
                gene_symbol="TP53",
                transcript_id="ENST00000269305",
                consequence=["missense_variant"],
                hgvs_p="p.Arg248Gln",
                hgvs_c="c.743G>A",
                vaf=0.35,
                total_depth=45,
                tumor_vaf=0.35
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF files
            tumor_vcf = temp_path / "tumor.vcf"
            normal_vcf = temp_path / "normal.vcf"
            
            self._create_mock_vcf(tumor_vcf, [
                {
                    'chrom': '17',
                    'pos': '7674220',  # GRCh38 coordinate for TP53
                    'ref': 'G',
                    'alt': 'A',
                    'info': 'AF=0.35',
                    'sample': '0/1:30,15:45'
                }
            ])
            
            # Normal VCF without the variant (filtered out)
            self._create_mock_vcf(normal_vcf, [])
            
            # Create output directory
            output_dir = temp_path / "results"
            
            # Setup CLI arguments
            args = [
                '--tumor-vcf', str(tumor_vcf),
                '--normal-vcf', str(normal_vcf),
                '--case-uid', 'TEST_002',
                '--cancer-type', 'lung_adenocarcinoma',
                '--output', str(output_dir)
            ]
            
            # Execute CLI
            with patch('sys.argv', ['annotation-engine'] + args):
                result = self.cli.run()
            
            # Verify successful execution
            assert result == 0
            
            # Verify VEP was called
            mock_vep_annotate.assert_called_once()
            
            # Verify output files were created
            results_file = output_dir / "annotation_results.json"
            assert results_file.exists()
            
            # Verify results content
            with open(results_file) as f:
                results = json.load(f)
            
            assert results['metadata']['total_variants'] == 1
            assert results['metadata']['analysis_type'] == 'TUMOR_NORMAL'
            assert len(results['variants']) == 1
            
            # Check first variant
            variant = results['variants'][0]
            assert variant['gene_annotation']['gene_symbol'] == 'TP53'
            assert variant['variant_id'] == '17_7674220_G_A'
    
    def test_cli_validation_error_handling(self):
        """Test CLI validation error handling"""
        
        # Test missing required arguments
        args = ['--case-uid', 'TEST_003']  # Missing input and cancer-type
        
        # argparse raises SystemExit for missing required arguments
        with patch('sys.argv', ['annotation-engine'] + args):
            try:
                result = self.cli.run()
                # If we get here, test that it returned error code
                assert result == 1
            except SystemExit as e:
                # argparse exits with code 2 for missing arguments
                assert e.code == 2
    
    def test_cli_dry_run_mode(self):
        """Test CLI dry run mode (validation only)"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF file
            vcf_file = temp_path / "test.vcf"
            self._create_mock_vcf(vcf_file, [
                {
                    'chrom': '7',
                    'pos': '140453136',
                    'ref': 'A',
                    'alt': 'T'
                }
            ])
            
            # Setup CLI arguments with dry-run
            args = [
                '--input', str(vcf_file),
                '--case-uid', 'TEST_004',
                '--cancer-type', 'melanoma',
                '--dry-run'
            ]
            
            # Execute CLI
            with patch('sys.argv', ['annotation-engine'] + args):
                result = self.cli.run()
            
            # Should succeed but not run pipeline
            assert result == 0
    
    @patch('annotation_engine.vep_runner.VEPRunner.annotate_vcf')
    def test_pipeline_error_handling(self, mock_vep_annotate):
        """Test error handling when pipeline fails"""
        
        # Setup mock to raise an exception
        mock_vep_annotate.side_effect = Exception("VEP processing failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF file with valid variant
            vcf_file = temp_path / "tumor.vcf"
            self._create_mock_vcf(vcf_file, [{
                'chrom': '7',
                'pos': '140753336',  # GRCh38 BRAF coordinate
                'ref': 'A',
                'alt': 'T',
                'info': 'AF=0.45',
                'sample': '0/1:25,20:45'
            }])
            
            # Setup CLI arguments
            args = [
                '--input', str(vcf_file),
                '--case-uid', 'TEST_005',
                '--cancer-type', 'melanoma'
            ]
            
            # Execute CLI
            with patch('sys.argv', ['annotation-engine'] + args):
                result = self.cli.run()
            
            # Should succeed with fallback mode
            assert result == 0


class TestPipelineIntegration:
    """Test integration between pipeline components"""
    
    @patch('annotation_engine.variant_processor.create_variant_annotations_from_vcf')
    @patch('annotation_engine.evidence_aggregator.EvidenceAggregator')
    @patch('annotation_engine.tiering.TieringEngine')
    def test_component_integration(self, mock_tiering, mock_evidence, mock_processor):
        """Test that pipeline components are properly integrated"""
        
        # This test would verify the actual wiring between components
        # Currently we've connected via the process_vcf_to_tier_results function
        
        # Import the pipeline function
        from annotation_engine.tiering import process_vcf_to_tier_results
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            vcf_file = temp_path / "test.vcf"
            
            # Create minimal VCF
            with open(vcf_file, 'w') as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                f.write("7\t140453136\t.\tA\tT\t60\tPASS\tAF=0.45\n")
            
            # The function should exist and be callable
            # (Even if it fails due to missing VEP, it should at least be importable)
            assert callable(process_vcf_to_tier_results)


if __name__ == "__main__":
    pytest.main([__file__])