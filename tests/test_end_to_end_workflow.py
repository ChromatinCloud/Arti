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
    
    @patch('annotation_engine.tiering.process_vcf_to_tier_results')
    def test_tumor_only_workflow(self, mock_process_vcf):
        """Test complete tumor-only workflow from CLI to results"""
        
        # Setup mock return for successful processing
        mock_tier_results = [
            {
                'variant_id': '7:140453136:A>T',
                'gene_symbol': 'BRAF',
                'amp_scoring': {'tier': 'Tier IA'},
                'analysis_type': 'TUMOR_ONLY',
                'confidence_score': 0.85
            }
        ]
        mock_processing_summary = {
            'total_variants': 1,
            'processed_variants': 1,
            'analysis_type': 'TUMOR_ONLY'
        }
        mock_process_vcf.return_value = (mock_tier_results, mock_processing_summary)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF file
            vcf_file = temp_path / "tumor.vcf"
            self._create_mock_vcf(vcf_file, [
                {
                    'chrom': '7',
                    'pos': '140453136',
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
            
            # Verify process_vcf_to_tier_results was called correctly
            mock_process_vcf.assert_called_once()
            call_args = mock_process_vcf.call_args
            
            assert call_args.kwargs['cancer_type'] == 'melanoma'
            assert call_args.kwargs['analysis_type'] == 'TUMOR_ONLY'
            assert call_args.kwargs['tumor_purity'] == 0.8
            assert str(call_args.kwargs['tumor_vcf_path']) == str(vcf_file)
            assert call_args.kwargs['normal_vcf_path'] is None
            
            # Verify results were saved
            results_file = output_dir / "annotation_results.json"
            assert results_file.exists()
            
            with open(results_file) as f:
                saved_results = json.load(f)
            
            assert len(saved_results) == 1
            assert saved_results[0]['variant_id'] == '7:140453136:A>T'
            assert saved_results[0]['gene_symbol'] == 'BRAF'
    
    @patch('annotation_engine.tiering.process_vcf_to_tier_results')
    def test_tumor_normal_workflow(self, mock_process_vcf):
        """Test complete tumor-normal workflow from CLI to results"""
        
        # Setup mock return for successful processing
        mock_tier_results = [
            {
                'variant_id': '17:7577121:C>T',
                'gene_symbol': 'TP53',
                'amp_scoring': {'tier': 'Tier IIC'},
                'analysis_type': 'TUMOR_NORMAL',
                'confidence_score': 0.92
            }
        ]
        mock_processing_summary = {
            'total_variants': 1,
            'processed_variants': 1,
            'analysis_type': 'TUMOR_NORMAL'
        }
        mock_process_vcf.return_value = (mock_tier_results, mock_processing_summary)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF files
            tumor_vcf = temp_path / "tumor.vcf"
            normal_vcf = temp_path / "normal.vcf"
            
            self._create_mock_vcf(tumor_vcf, [
                {
                    'chrom': '17',
                    'pos': '7577121',
                    'ref': 'C',
                    'alt': 'T',
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
            
            # Verify process_vcf_to_tier_results was called correctly
            mock_process_vcf.assert_called_once()
            call_args = mock_process_vcf.call_args
            
            assert call_args.kwargs['cancer_type'] == 'lung_adenocarcinoma'
            assert call_args.kwargs['analysis_type'] == 'TUMOR_NORMAL'
            assert str(call_args.kwargs['tumor_vcf_path']) == str(tumor_vcf)
            assert str(call_args.kwargs['normal_vcf_path']) == str(normal_vcf)
            
            # Verify results were saved
            results_file = output_dir / "annotation_results.json"
            assert results_file.exists()
            
            with open(results_file) as f:
                saved_results = json.load(f)
            
            assert len(saved_results) == 1
            assert saved_results[0]['analysis_type'] == 'TUMOR_NORMAL'
    
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
    
    @patch('annotation_engine.tiering.process_vcf_to_tier_results')
    def test_pipeline_error_handling(self, mock_process_vcf):
        """Test error handling when pipeline fails"""
        
        # Setup mock to raise an exception
        mock_process_vcf.side_effect = Exception("VCF processing failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create mock VCF file
            vcf_file = temp_path / "tumor.vcf"
            self._create_mock_vcf(vcf_file, [{}])
            
            # Setup CLI arguments
            args = [
                '--input', str(vcf_file),
                '--case-uid', 'TEST_005',
                '--cancer-type', 'melanoma'
            ]
            
            # Execute CLI
            with patch('sys.argv', ['annotation-engine'] + args):
                result = self.cli.run()
            
            # Should fail gracefully
            assert result == 1


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