"""
Variant processing endpoint tests
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestVariantEndpoints:
    """Test variant processing functionality"""
    
    def test_annotate_variants_success(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test successful variant annotation"""
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "TEST_CASE_001",
                "cancer_type": "melanoma",
                "analysis_type": "tumor_only"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data["data"]
        assert data["data"]["status"] == "queued"
    
    def test_annotate_variants_no_auth(self, client: TestClient, sample_vcf_content: str):
        """Test variant annotation without authentication"""
        response = client.post(
            "/api/v1/variants/annotate",
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "TEST_CASE_001",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 403
    
    def test_annotate_variants_missing_fields(self, client: TestClient, auth_headers: dict):
        """Test annotation with missing required fields"""
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "case_uid": "TEST_CASE_001"
                # Missing vcf_content and cancer_type
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_variant_details_braf(self, client: TestClient, auth_headers: dict):
        """Test getting BRAF variant details"""
        variant_id = "7:140753336:A>T"
        
        response = client.get(
            f"/api/v1/variants/{variant_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["variant_id"] == variant_id
        assert data["data"]["gene"] == "BRAF"
        assert data["data"]["hgvs_p"] == "p.Val600Glu"
        
        # Check comprehensive annotation data
        assert "functional_predictions" in data["data"]
        assert "population_frequencies" in data["data"]
        assert "conservation" in data["data"]
        assert "clinical_evidence" in data["data"]
        
        # Check specific prediction tools
        predictions = data["data"]["functional_predictions"]
        assert "alphamissense" in predictions
        assert "revel" in predictions
        assert "sift" in predictions
        assert "spliceai" in predictions
        
        # Check clinical evidence
        clinical = data["data"]["clinical_evidence"]
        assert "clinvar" in clinical
        assert "therapeutic" in clinical
        assert clinical["clinvar"]["significance"] == "Pathogenic"
        assert len(clinical["therapeutic"]) > 0
    
    def test_get_variant_details_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting details for non-existent variant"""
        response = client.get(
            "/api/v1/variants/1:123456:G>A",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_get_variant_details_no_auth(self, client: TestClient):
        """Test getting variant details without authentication"""
        response = client.get("/api/v1/variants/7:140753336:A>T")
        
        assert response.status_code == 403
    
    def test_batch_annotate_variants(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test batch variant annotation"""
        response = client.post(
            "/api/v1/variants/batch",
            headers=auth_headers,
            json={
                "vcf_files": [sample_vcf_content, sample_vcf_content],
                "case_uids": ["BATCH_CASE_001", "BATCH_CASE_002"],
                "cancer_types": ["melanoma", "lung_adenocarcinoma"],
                "analysis_type": "tumor_only"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data["data"]
        assert data["data"]["batch_size"] == 2
    
    def test_variant_caching(self, client: TestClient, auth_headers: dict):
        """Test that variant details are cached"""
        variant_id = "7:140753336:A>T"
        
        # First request
        response1 = client.get(
            f"/api/v1/variants/{variant_id}",
            headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["meta"]["cached"] is False
        
        # Second request should be cached
        response2 = client.get(
            f"/api/v1/variants/{variant_id}",
            headers=auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["meta"]["cached"] is True
    
    def test_annotation_job_workflow(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test complete annotation workflow with job tracking"""
        # Submit annotation job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "WORKFLOW_TEST_CASE",
                "cancer_type": "melanoma",
                "analysis_type": "tumor_only"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # Check job status
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        job_data = response.json()["data"]
        assert job_data["job_id"] == job_id
        assert job_data["status"] in ["queued", "processing", "completed"]
        assert "progress" in job_data
        assert "message" in job_data
    
    def test_response_format_consistency(self, client: TestClient, auth_headers: dict):
        """Test that all responses follow consistent format"""
        variant_id = "7:140753336:A>T"
        
        response = client.get(
            f"/api/v1/variants/{variant_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        
        # Check meta fields
        meta = data["meta"]
        assert "timestamp" in meta
        assert "version" in meta
        
        # Check data is not empty
        assert data["data"] is not None
        assert len(data["data"]) > 0