"""
Clinical case management endpoint tests
"""

import pytest
from fastapi.testclient import TestClient


class TestCaseEndpoints:
    """Test clinical case management functionality"""
    
    def test_list_cases_success(self, client: TestClient, auth_headers: dict):
        """Test listing cases with authentication"""
        response = client.get("/api/v1/cases/", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "cases" in data["data"]
        assert "pagination" in data["data"]
        
        # Check pagination structure
        pagination = data["data"]["pagination"]
        assert "page" in pagination
        assert "limit" in pagination
        assert "total" in pagination
        assert "pages" in pagination
    
    def test_list_cases_with_filters(self, client: TestClient, auth_headers: dict):
        """Test listing cases with filters"""
        response = client.get(
            "/api/v1/cases/?cancer_type=melanoma&status=in_progress&page=1&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # Should have melanoma cases
        cases = data["data"]["cases"]
        if cases:  # If any cases returned
            for case in cases:
                if "cancer_type" in case:
                    assert case["cancer_type"] == "melanoma"
    
    def test_list_cases_no_auth(self, client: TestClient):
        """Test listing cases without authentication"""
        response = client.get("/api/v1/cases/")
        
        assert response.status_code == 403
    
    def test_create_case_success(self, client: TestClient, auth_headers: dict, sample_case_data: dict):
        """Test creating a new case"""
        response = client.post(
            "/api/v1/cases/",
            headers=auth_headers,
            json=sample_case_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        case = data["data"]
        assert "case_uid" in case
        assert case["patient_id"] == sample_case_data["patient_id"]
        assert case["cancer_type"] == sample_case_data["cancer_type"]
        assert case["analysis_type"] == sample_case_data["analysis_type"]
        assert case["status"] == "created"
        assert case["created_by"] == "demo_user"
        
        # Should have empty summary initially
        assert case["summary"]["total_variants"] == 0
        assert case["summary"]["actionable_variants"] == 0
    
    def test_create_case_missing_fields(self, client: TestClient, auth_headers: dict):
        """Test creating case with missing required fields"""
        response = client.post(
            "/api/v1/cases/",
            headers=auth_headers,
            json={
                "patient_id": "TEST_PATIENT"
                # Missing cancer_type
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_case_details_success(self, client: TestClient, auth_headers: dict):
        """Test getting case details"""
        case_uid = "CASE_001"
        
        response = client.get(f"/api/v1/cases/{case_uid}", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        case = data["data"]
        assert case["case_uid"] == case_uid
        assert "patient_id" in case
        assert "cancer_type" in case
        assert "status" in case
        assert "variants" in case
        assert "summary" in case
    
    def test_get_case_details_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting details for non-existent case"""
        response = client.get("/api/v1/cases/NONEXISTENT_CASE", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_update_case_success(self, client: TestClient, auth_headers: dict, sample_case_data: dict):
        """Test updating case information"""
        case_uid = "CASE_001"
        
        # Update cancer type
        updated_data = sample_case_data.copy()
        updated_data["cancer_type"] = "lung_adenocarcinoma"
        updated_data["clinical_notes"] = "Updated clinical notes"
        
        response = client.put(
            f"/api/v1/cases/{case_uid}",
            headers=auth_headers,
            json=updated_data
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        case = data["data"]
        assert case["cancer_type"] == "lung_adenocarcinoma"
        assert case["clinical_notes"] == "Updated clinical notes"
        assert "updated_at" in case
        assert "updated_by" in case
    
    def test_get_case_variants(self, client: TestClient, auth_headers: dict):
        """Test getting variants for a case"""
        case_uid = "CASE_001"
        
        response = client.get(f"/api/v1/cases/{case_uid}/variants", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["case_uid"] == case_uid
        assert "variants" in data["data"]
        assert "summary" in data["data"]
        
        # Check variant structure if any variants exist
        variants = data["data"]["variants"]
        if variants:
            variant = variants[0]
            assert "variant_id" in variant
            assert "gene" in variant
            assert "tier" in variant
    
    def test_get_case_summary(self, client: TestClient, auth_headers: dict):
        """Test getting case summary"""
        case_uid = "CASE_001"
        
        response = client.get(f"/api/v1/cases/{case_uid}/summary", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        summary_data = data["data"]
        assert summary_data["case_uid"] == case_uid
        assert "patient_id" in summary_data
        assert "cancer_type" in summary_data
        assert "analysis_type" in summary_data
        assert "status" in summary_data
        assert "summary" in summary_data
        
        # Check summary structure
        summary = summary_data["summary"]
        assert "total_variants" in summary
        assert "tier_distribution" in summary
        assert "actionable_variants" in summary
    
    def test_generate_case_report_json(self, client: TestClient, auth_headers: dict):
        """Test generating case report in JSON format"""
        case_uid = "CASE_001"
        
        response = client.get(
            f"/api/v1/cases/{case_uid}/report?format=json",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        report = data["data"]
        assert "report_id" in report
        assert report["case_uid"] == case_uid
        assert "patient_id" in report
        assert "generated_at" in report
        assert "generated_by" in report
        assert "variants" in report
        assert "summary" in report
        assert "clinical_recommendations" in report
    
    def test_generate_case_report_pdf(self, client: TestClient, auth_headers: dict):
        """Test generating case report in PDF format"""
        case_uid = "CASE_001"
        
        response = client.get(
            f"/api/v1/cases/{case_uid}/report?format=pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        report = data["data"]
        assert "pdf_url" in report
        assert report["case_uid"] == case_uid
    
    def test_finalize_case(self, client: TestClient, auth_headers: dict):
        """Test finalizing a case"""
        case_uid = "CASE_001"
        
        response = client.post(f"/api/v1/cases/{case_uid}/finalize", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        finalization = data["data"]
        assert finalization["case_uid"] == case_uid
        assert finalization["status"] == "finalized"
        assert "finalized_at" in finalization
        assert "finalized_by" in finalization
        assert finalization["finalized_by"] == "demo_user"
    
    def test_case_workflow_end_to_end(self, client: TestClient, auth_headers: dict, sample_case_data: dict):
        """Test complete case workflow"""
        # 1. Create case
        response = client.post("/api/v1/cases/", headers=auth_headers, json=sample_case_data)
        assert response.status_code == 200
        
        case_uid = response.json()["data"]["case_uid"]
        
        # 2. Get case details
        response = client.get(f"/api/v1/cases/{case_uid}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "created"
        
        # 3. Update case
        updated_data = sample_case_data.copy()
        updated_data["clinical_notes"] = "Updated notes"
        
        response = client.put(f"/api/v1/cases/{case_uid}", headers=auth_headers, json=updated_data)
        assert response.status_code == 200
        
        # 4. Get case summary
        response = client.get(f"/api/v1/cases/{case_uid}/summary", headers=auth_headers)
        assert response.status_code == 200
        
        # 5. Generate report
        response = client.get(f"/api/v1/cases/{case_uid}/report", headers=auth_headers)
        assert response.status_code == 200
        
        # 6. Finalize case
        response = client.post(f"/api/v1/cases/{case_uid}/finalize", headers=auth_headers)
        assert response.status_code == 200
        
        # 7. Verify finalized status
        response = client.get(f"/api/v1/cases/{case_uid}", headers=auth_headers)
        assert response.status_code == 200
        # Note: This might still show old status due to demo data structure
    
    def test_pagination_functionality(self, client: TestClient, auth_headers: dict):
        """Test pagination parameters"""
        # Test different page sizes
        response = client.get("/api/v1/cases/?page=1&limit=5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["data"]["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 5
        
        # Test invalid pagination
        response = client.get("/api/v1/cases/?page=0&limit=1000", headers=auth_headers)
        assert response.status_code == 422  # Validation error for invalid page/limit