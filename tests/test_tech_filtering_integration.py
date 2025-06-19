"""
Integration tests for technical filtering API with VCF validation
"""

import pytest
import tempfile
import json
from pathlib import Path
from fastapi.testclient import TestClient
from src.annotation_engine.api.main import app


class TestTechFilteringIntegration:
    """Integration tests for tech filtering with validation"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self, client):
        """Get authentication headers"""
        # In real tests, implement proper auth
        return {"Authorization": "Bearer test-token"}
    
    @pytest.fixture
    def tumor_only_vcf(self):
        """Create test tumor-only VCF"""
        content = """##fileformat=VCFv4.2
##contig=<ID=chr7,length=159138663>
##INFO=<ID=DP,Number=1,Type=Integer,Description="Total Depth">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Genotype Quality">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TumorSample
chr7	140453136	.	A	T	100	PASS	DP=100	GT:DP:AD:GQ	0/1:100:50,50:99
chr7	140453137	.	C	G	30	LowQual	DP=10	GT:DP:AD:GQ	0/1:10:5,5:20
chr7	140453138	.	G	A	80	PASS	DP=80	GT:DP:AD:GQ	0/1:80:40,40:99
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            return f.name
    
    @pytest.fixture
    def multi_sample_vcf(self):
        """Create test multi-sample VCF"""
        content = """##fileformat=VCFv4.2
##INFO=<ID=SOMATIC,Number=0,Type=Flag,Description="Somatic mutation">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Read Depth">
##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depths">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	TUMOR	NORMAL
chr7	140453136	.	A	T	100	PASS	DP=100;SOMATIC	GT:DP:AD	0/1:100:50,50	0/0:100:100,0
chr7	140453137	.	C	G	80	PASS	DP=80;SOMATIC	GT:DP:AD	0/1:80:40,40	0/0:80:80,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            return f.name
    
    def test_tumor_only_valid_submission(self, client, auth_headers, tumor_only_vcf):
        """Test valid tumor-only submission with filters"""
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": tumor_only_vcf,
            "filters": {
                "FILTER_PASS": True,
                "MIN_QUAL": 50,
                "MIN_DP": 20,
                "MIN_GQ": 30
            },
            "metadata": {
                "case_id": "CASE_001",
                "cancer_type": "SKCM",
                "patient_uid": "PT_001",
                "tumor_purity": 0.85,
                "specimen_type": "FFPE"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "output_vcf" in data
        assert data["variant_counts"]["input"] == 3
        # After filters (PASS only, QUAL>=50), should have 2 variants
        assert data["variant_counts"]["filtered"] <= 2
    
    def test_tumor_only_with_multisample_vcf_error(self, client, auth_headers, multi_sample_vcf):
        """Test tumor-only mode rejects multi-sample VCF"""
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": multi_sample_vcf,
            "filters": {"FILTER_PASS": True},
            "metadata": {
                "case_id": "CASE_002",
                "cancer_type": "LUAD"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "VCF validation failed" in data["error"]
        assert "Tumor-only mode requires single-sample VCF" in data["error"]
    
    def test_tumor_normal_multisample_valid(self, client, auth_headers, multi_sample_vcf):
        """Test valid tumor-normal with multi-sample VCF"""
        request_data = {
            "mode": "tumor-normal",
            "assay": "default_assay",
            "input_vcf": multi_sample_vcf,
            "filters": {
                "FILTER_PASS": True,
                "MIN_VAF": 0.1,
                "NORMAL_VAF_MAX": 0.05
            },
            "metadata": {
                "case_id": "CASE_003",
                "cancer_type": "LUAD",
                "patient_uid": "PT_003"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["variant_counts"]["input"] == 2
    
    def test_tumor_normal_separate_files(self, client, auth_headers, tumor_only_vcf):
        """Test tumor-normal with separate VCF files"""
        # Create normal VCF
        normal_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	NormalSample
chr7	140453136	.	A	T	10	LowQual	DP=100	GT:DP:AD	0/0:100:95,5
chr7	140453137	.	C	G	80	PASS	DP=80	GT:DP:AD	0/0:80:80,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(normal_content)
            normal_vcf = f.name
        
        request_data = {
            "mode": "tumor-normal",
            "assay": "default_assay",
            "input_vcf": f"{tumor_only_vcf},{normal_vcf}",  # Comma-separated
            "filters": {
                "FILTER_PASS": True,
                "TUMOR_NORMAL_VAF_RATIO": 5.0
            },
            "metadata": {
                "case_id": "CASE_004",
                "cancer_type": "SKCM"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_missing_required_metadata(self, client, auth_headers, tumor_only_vcf):
        """Test missing required metadata fields"""
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": tumor_only_vcf,
            "filters": {"FILTER_PASS": True},
            "metadata": {
                # Missing case_id
                "cancer_type": "SKCM"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Metadata validation failed" in data["error"]
        assert "Missing required field: case_id" in data["error"]
    
    def test_invalid_tumor_purity(self, client, auth_headers, tumor_only_vcf):
        """Test invalid tumor purity value"""
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": tumor_only_vcf,
            "filters": {"FILTER_PASS": True},
            "metadata": {
                "case_id": "CASE_005",
                "cancer_type": "SKCM",
                "tumor_purity": 1.5  # Invalid: > 1.0
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Metadata validation failed" in data["error"]
        assert "Invalid value for tumor_purity" in data["error"]
    
    def test_multisample_with_sample_names(self, client, auth_headers):
        """Test multi-sample VCF with explicit sample name mapping"""
        # Create VCF with non-standard sample names
        content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	S1234_T_DNA	S1234_B_DNA	QC_Sample
chr7	140453136	.	A	T	100	PASS	DP=100	GT:DP:AD	0/1:100:50,50	0/0:100:100,0	0/0:50:50,0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            vcf_path = f.name
        
        request_data = {
            "mode": "tumor-normal",
            "assay": "default_assay",
            "input_vcf": vcf_path,
            "filters": {"FILTER_PASS": True},
            "metadata": {
                "case_id": "CASE_006",
                "cancer_type": "LUAD"
            },
            "tumor_sample_name": "S1234_T_DNA",
            "normal_sample_name": "S1234_B_DNA"
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.parametrize("mode,expected_error", [
        ("invalid-mode", "Invalid analysis mode"),
        ("", "Invalid analysis mode"),
        ("TumorOnly", "Invalid analysis mode"),  # Case sensitive
    ])
    def test_invalid_analysis_mode(self, client, auth_headers, tumor_only_vcf, mode, expected_error):
        """Test invalid analysis modes"""
        request_data = {
            "mode": mode,
            "assay": "default_assay",
            "input_vcf": tumor_only_vcf,
            "filters": {},
            "metadata": {
                "case_id": "CASE_007",
                "cancer_type": "SKCM"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data,
            headers=auth_headers
        )
        
        # Should handle gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
    
    def test_handoff_to_arti_pipeline(self, client, auth_headers, tumor_only_vcf):
        """Test successful handoff from tech filtering to Arti annotation"""
        # First, apply filters
        filter_request = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": tumor_only_vcf,
            "filters": {
                "FILTER_PASS": True,
                "MIN_QUAL": 50
            },
            "metadata": {
                "case_id": "CASE_008",
                "cancer_type": "SKCM",
                "patient_uid": "PT_008",
                "tumor_purity": 0.75,
                "specimen_type": "FFPE"
            }
        }
        
        filter_response = client.post(
            "/api/v1/tech-filtering/apply",
            json=filter_request,
            headers=auth_headers
        )
        
        assert filter_response.status_code == 200
        filter_data = filter_response.json()
        assert filter_data["success"] is True
        
        # Now submit to annotation pipeline
        filtered_vcf = filter_data["output_vcf"]
        
        annotation_request = {
            "vcf_path": filtered_vcf,
            "case_uid": "CASE_008",
            "cancer_type": "SKCM",
            "analysis_type": "tumor_only",
            "patient_uid": "PT_008",
            "tumor_purity": 0.75,
            "specimen_type": "FFPE"
        }
        
        annotation_response = client.post(
            "/api/v1/variants/annotate-file",
            json=annotation_request,
            headers=auth_headers
        )
        
        assert annotation_response.status_code == 200
        annotation_data = annotation_response.json()
        assert annotation_data["success"] is True
        assert "job_id" in annotation_data["data"]
        assert annotation_data["data"]["case_uid"] == "CASE_008"


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_empty_vcf(self, client):
        """Test handling of empty VCF file"""
        content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Sample1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            empty_vcf = f.name
        
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": empty_vcf,
            "filters": {"FILTER_PASS": True},
            "metadata": {
                "case_id": "CASE_EMPTY",
                "cancer_type": "SKCM"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["variant_counts"]["input"] == 0
        assert data["variant_counts"]["filtered"] == 0
    
    def test_malformed_vcf_header(self, client):
        """Test handling of malformed VCF header"""
        content = """##fileformat=VCFv4.2
#CHROM	POS	REF	ALT	QUAL	FILTER	INFO	FORMAT	Sample1
chr1	12345	G	A	80	PASS	DP=80	GT	0/1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(content)
            malformed_vcf = f.name
        
        request_data = {
            "mode": "tumor-only",
            "assay": "default_assay",
            "input_vcf": malformed_vcf,
            "filters": {},
            "metadata": {
                "case_id": "CASE_MALFORMED",
                "cancer_type": "SKCM"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Missing required column: ID" in data["error"]
    
    def test_vcf_version_mismatch_tn(self, client):
        """Test VCF version mismatch in tumor-normal separate files"""
        # Create tumor VCF v4.2
        tumor_content = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Tumor
chr1	12345	.	G	A	80	PASS	DP=80	GT	0/1
"""
        # Create normal VCF v4.3
        normal_content = """##fileformat=VCFv4.3
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	Normal
chr1	12345	.	G	A	10	PASS	DP=80	GT	0/0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(tumor_content)
            tumor_vcf = f.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(normal_content)
            normal_vcf = f.name
        
        request_data = {
            "mode": "tumor-normal",
            "assay": "default_assay",
            "input_vcf": f"{tumor_vcf},{normal_vcf}",
            "filters": {},
            "metadata": {
                "case_id": "CASE_VERSION",
                "cancer_type": "LUAD"
            }
        }
        
        response = client.post(
            "/api/v1/tech-filtering/apply",
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "VCF version mismatch" in data["error"]