"""
Test VEP integration for variant annotation

Tests VEP runner functionality and integration with variant processor.
"""

import pytest
import tempfile
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock
import json

# Add the annotation_engine package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.vep_runner import VEPConfiguration, VEPRunner, get_vep_version
from annotation_engine.variant_processor import VariantProcessor, create_variant_annotations_from_vcf
from annotation_engine.models import AnalysisType
from annotation_engine.validation.error_handler import ValidationError


class TestVEPConfiguration:
    """Test VEP configuration and validation"""
    
    def test_default_configuration(self):
        """Test default VEP configuration"""
        config = VEPConfiguration()
        
        assert config.assembly == "GRCh37"
        assert config.use_docker == True
        assert config.docker_image == "ensemblorg/ensembl-vep:release_114.1"
        assert config.refs_dir.name == ".refs"
    
    def test_custom_configuration(self):
        """Test custom VEP configuration"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cache_dir = temp_path / "cache"
            plugins_dir = temp_path / "plugins"
            
            config = VEPConfiguration(
                cache_dir=cache_dir,
                plugins_dir=plugins_dir,
                assembly="GRCh38",
                use_docker=False,
                vep_command="/usr/bin/vep"
            )
            
            assert config.cache_dir == cache_dir
            assert config.plugins_dir == plugins_dir
            assert config.assembly == "GRCh38"
            assert config.use_docker == False
            assert config.vep_command == "/usr/bin/vep"
    
    def test_repo_root_detection(self):
        """Test repository root detection"""
        config = VEPConfiguration()
        
        # Should find the repo root containing pyproject.toml
        assert config.repo_root.name == "Arti"
        assert (config.repo_root / "pyproject.toml").exists()


class TestVEPRunner:
    """Test VEP runner functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.test_vcf_content = '''##fileformat=VCFv4.2
##reference=GRCh37
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR
17	7674220	.	G	A	100	PASS	DP=50;AF=0.45	GT:AD:DP	0/1:27,23:50
7	140753336	.	T	A	95	PASS	DP=45;AF=0.52	GT:AD:DP	0/1:22,23:45
'''
        
        # Mock VEP JSON output
        self.mock_vep_output = [
            {
                "id": "17_7674220_G/A",
                "input": "17\t7674220\t.\tG\tA\t100\tPASS\tDP=50;AF=0.45",
                "most_severe_consequence": "missense_variant",
                "assembly_name": "GRCh37",
                "transcript_consequences": [
                    {
                        "gene_symbol": "TP53",
                        "transcript_id": "ENST00000269305",
                        "consequence_terms": ["missense_variant"],
                        "hgvsc": "ENST00000269305.8:c.742C>T",
                        "hgvsp": "ENSP00000269305.4:p.Arg248Trp",
                        "impact": "MODERATE",
                        "canonical": 1
                    }
                ],
                "colocated_variants": [
                    {
                        "id": "rs121913343",
                        "frequencies": {
                            "gnomad_exomes": 0.00001234,
                            "gnomad_genomes": 0.00000987
                        }
                    }
                ]
            }
        ]
    
    def _create_test_vcf(self, temp_dir: Path) -> Path:
        """Create test VCF file"""
        vcf_file = temp_dir / "test.vcf"
        with open(vcf_file, 'w') as f:
            f.write(self.test_vcf_content)
        return vcf_file
    
    def test_vep_runner_initialization(self):
        """Test VEP runner initialization"""
        
        # Test with mock configuration that doesn't require actual VEP
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            config = VEPConfiguration(use_docker=False, vep_command="mock_vep")
            runner = VEPRunner(config)
            
            assert runner.config == config
            assert len(runner.default_plugins) > 0
    
    def test_build_vep_command_docker(self):
        """Test Docker VEP command building"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_vcf = self._create_test_vcf(temp_path)
            output_file = temp_path / "output.json"
            
            with patch.object(VEPConfiguration, 'validate', return_value=True):
                config = VEPConfiguration(
                    use_docker=True,
                    vep_command="docker",
                    cache_dir=temp_path / "cache",
                    plugins_dir=temp_path / "plugins"
                )
                runner = VEPRunner(config)
                
                cmd = runner._build_vep_command(
                    input_vcf=input_vcf,
                    output_file=output_file,
                    output_format="json",
                    plugins=["dbNSFP,/plugins/dbNSFP.gz,ALL"]
                )
                
                assert cmd[0] == "docker"
                assert "run" in cmd
                assert "--rm" in cmd
                assert config.docker_image in cmd
                assert "vep" in cmd
                assert "--json" in cmd
    
    def test_build_vep_command_native(self):
        """Test native VEP command building"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_vcf = self._create_test_vcf(temp_path)
            output_file = temp_path / "output.json"
            
            with patch.object(VEPConfiguration, 'validate', return_value=True):
                config = VEPConfiguration(
                    use_docker=False,
                    vep_command="/usr/bin/vep",
                    cache_dir=temp_path / "cache",
                    plugins_dir=temp_path / "plugins"
                )
                runner = VEPRunner(config)
                
                cmd = runner._build_vep_command(
                    input_vcf=input_vcf,
                    output_file=output_file,
                    output_format="json",
                    plugins=["dbNSFP,/plugins/dbNSFP.gz,ALL"]
                )
                
                assert cmd[0] == "/usr/bin/vep"
                assert "--input_file" in cmd
                assert "--output_file" in cmd
                assert "--json" in cmd
                assert "--plugin" in cmd
    
    @patch('subprocess.run')
    def test_annotate_vcf_success(self, mock_subprocess):
        """Test successful VEP annotation"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_vcf = self._create_test_vcf(temp_path)
            
            # Mock successful subprocess execution
            mock_subprocess.return_value.returncode = 0
            mock_subprocess.return_value.stdout = "VEP annotation completed"
            mock_subprocess.return_value.stderr = ""
            
            # Create mock output file
            output_json = temp_path / f"{input_vcf.stem}_vep.json"
            with open(output_json, 'w') as f:
                json.dump(self.mock_vep_output, f)
            
            with patch.object(VEPConfiguration, 'validate', return_value=True):
                config = VEPConfiguration(use_docker=False, vep_command="mock_vep")
                runner = VEPRunner(config)
                
                # Mock the temporary file creation to use our temp directory
                with patch('tempfile.TemporaryDirectory') as mock_temp:
                    mock_temp.return_value.__enter__.return_value = str(temp_path)
                    
                    result = runner.annotate_vcf(input_vcf, output_format="annotations")
                    
                    # Should return VariantAnnotation objects
                    assert isinstance(result, list)
                    assert len(result) == 1
                    
                    variant = result[0]
                    assert variant.chromosome == "17"
                    assert variant.position == 7674220
                    assert variant.gene_symbol == "TP53"
                    assert variant.consequence == ["missense_variant"]
                    assert variant.hgvs_p == "ENSP00000269305.4:p.Arg248Trp"
                    
                    # Check population frequencies
                    assert len(variant.population_frequencies) == 2
                    assert variant.population_frequencies[0].database == "gnomAD"
                    assert variant.population_frequencies[0].population == "gnomad_exomes"
    
    @patch('subprocess.run')
    def test_annotate_vcf_failure(self, mock_subprocess):
        """Test VEP annotation failure handling"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_vcf = self._create_test_vcf(temp_path)
            
            # Mock failed subprocess execution
            mock_subprocess.side_effect = ValidationError(
                error_type="vep_execution_error",
                message="VEP failed"
            )
            
            with patch.object(VEPConfiguration, 'validate', return_value=True):
                config = VEPConfiguration(use_docker=False, vep_command="mock_vep")
                runner = VEPRunner(config)
                
                with pytest.raises(ValidationError) as exc_info:
                    runner.annotate_vcf(input_vcf, output_format="annotations")
                
                assert exc_info.value.error_type == "vep_execution_error"


class TestVariantProcessorIntegration:
    """Test variant processor integration with VEP"""
    
    def test_variant_processor_with_vep_config(self):
        """Test variant processor with VEP configuration"""
        
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            vep_config = VEPConfiguration(use_docker=False, vep_command="mock_vep")
            processor = VariantProcessor(vep_config=vep_config)
            
            assert processor.vep_config == vep_config
    
    def test_create_variant_annotations_from_vcf_with_vep(self):
        """Test convenience function with VEP configuration"""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test VCF
            test_vcf = temp_path / "test.vcf"
            with open(test_vcf, 'w') as f:
                f.write('''##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
17	7674220	.	G	A	100	PASS	DP=50;AF=0.45
''')
            
            with patch.object(VEPConfiguration, 'validate', return_value=True):
                vep_config = VEPConfiguration(use_docker=False, vep_command="mock_vep")
                
                # Mock the entire processing pipeline
                with patch.object(VariantProcessor, 'process_variants') as mock_process:
                    mock_process.return_value = ([], {"total_variants": 0})
                    
                    result = create_variant_annotations_from_vcf(
                        tumor_vcf_path=test_vcf,
                        analysis_type=AnalysisType.TUMOR_ONLY,
                        vep_config=vep_config
                    )
                    
                    # Should return tuple of (annotations, summary)
                    annotations, summary = result
                    assert isinstance(annotations, list)
                    assert isinstance(summary, dict)
                    
                    # Verify VEP config was passed
                    mock_process.assert_called_once()
                    call_kwargs = mock_process.call_args.kwargs
                    assert call_kwargs['tumor_vcf_path'] == test_vcf
                    assert call_kwargs['analysis_type'] == AnalysisType.TUMOR_ONLY


class TestVEPUtilities:
    """Test VEP utility functions"""
    
    @patch('subprocess.run')
    def test_get_vep_version_docker(self, mock_subprocess):
        """Test VEP version detection with Docker"""
        
        mock_subprocess.return_value.stdout = "ensembl-vep version 114.0\nOther output..."
        mock_subprocess.return_value.returncode = 0
        
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            config = VEPConfiguration(use_docker=True, vep_command="docker")
            version = get_vep_version(config)
            
            assert "ensembl-vep version 114.0" in version
    
    @patch('subprocess.run')
    def test_get_vep_version_native(self, mock_subprocess):
        """Test VEP version detection with native installation"""
        
        mock_subprocess.return_value.stdout = "ensembl-vep version 114.0\nOther output..."
        mock_subprocess.return_value.returncode = 0
        
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            config = VEPConfiguration(use_docker=False, vep_command="/usr/bin/vep")
            version = get_vep_version(config)
            
            assert "ensembl-vep version 114.0" in version
    
    @patch('subprocess.run')
    def test_get_vep_version_failure(self, mock_subprocess):
        """Test VEP version detection failure"""
        
        mock_subprocess.side_effect = Exception("Command failed")
        
        with patch.object(VEPConfiguration, 'validate', return_value=True):
            config = VEPConfiguration(use_docker=False, vep_command="/usr/bin/vep")
            version = get_vep_version(config)
            
            assert "VEP version check failed" in version


if __name__ == "__main__":
    pytest.main([__file__])