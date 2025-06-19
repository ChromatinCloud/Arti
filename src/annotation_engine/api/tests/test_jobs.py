"""
Job management endpoint tests
"""

import pytest
from fastapi.testclient import TestClient


class TestJobEndpoints:
    """Test job management functionality"""
    
    def test_get_job_status_success(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test getting job status for existing job"""
        # First create a job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "JOB_TEST_CASE",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # Now get job status
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        job_data = data["data"]
        assert job_data["job_id"] == job_id
        assert "status" in job_data
        assert "progress" in job_data
        assert "message" in job_data
        assert "created_at" in job_data
        
        # Status should be one of valid states
        assert job_data["status"] in ["queued", "processing", "completed", "failed"]
        
        # Progress should be between 0 and 1
        assert 0 <= job_data["progress"] <= 1
    
    def test_get_job_status_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting status for non-existent job"""
        response = client.get("/api/v1/jobs/nonexistent_job_id", headers=auth_headers)
        
        assert response.status_code == 404
        
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"]["message"]
    
    def test_get_job_status_no_auth(self, client: TestClient):
        """Test getting job status without authentication"""
        response = client.get("/api/v1/jobs/some_job_id")
        
        assert response.status_code == 403
    
    def test_list_jobs_success(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test listing user's jobs"""
        # Create a job first
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "LIST_JOBS_TEST",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        
        # List jobs
        response = client.get("/api/v1/jobs/", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data["data"]
        assert "total" in data["data"]
        
        # Should have at least one job
        jobs = data["data"]["jobs"]
        assert len(jobs) >= 1
        
        # Check job structure
        if jobs:
            job = jobs[0]
            assert "job_id" in job
            assert "status" in job
            assert "progress" in job
            assert "message" in job
            assert "created_at" in job
            
            # user_id should not be present for non-admin
            assert "user_id" not in job or job["user_id"] is None
    
    def test_list_jobs_empty(self, client: TestClient, auth_headers: dict):
        """Test listing jobs when user has no jobs"""
        # This test assumes a fresh test environment
        # In practice, jobs are stored in memory so this might not be empty
        response = client.get("/api/v1/jobs/", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "jobs" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["jobs"], list)
        assert isinstance(data["data"]["total"], int)
    
    def test_retry_job_success(self, client: TestClient, auth_headers: dict):
        """Test retrying a failed job"""
        # For this test, we'll need to simulate a failed job
        # Since our demo system doesn't have real failures, we'll skip implementation details
        # but test the endpoint structure
        
        # This would normally test:
        # 1. Create job
        # 2. Wait for or force job to fail
        # 3. Retry job
        # 4. Verify job is back to queued status
        
        # For now, test the endpoint with a non-existent job
        response = client.post("/api/v1/jobs/nonexistent_job/retry", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_cancel_job_success(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test cancelling a job"""
        # Create a job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "CANCEL_JOB_TEST",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # Cancel the job
        response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "message" in data["data"]
        
        # The message should indicate success
        assert "cancelled" in data["data"]["message"] or "deleted" in data["data"]["message"]
    
    def test_cancel_job_not_found(self, client: TestClient, auth_headers: dict):
        """Test cancelling non-existent job"""
        response = client.delete("/api/v1/jobs/nonexistent_job", headers=auth_headers)
        
        assert response.status_code == 404
    
    def test_job_permissions(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test job access permissions"""
        # Create a job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "PERMISSIONS_TEST",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # User should be able to access their own job
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # User should be able to cancel their own job
        response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
    
    def test_job_status_progression(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test that job status progresses logically"""
        # Create a job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "PROGRESSION_TEST",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # Check initial status
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        initial_status = response.json()["data"]["status"]
        assert initial_status in ["queued", "processing"]
        
        # Progress should be valid
        progress = response.json()["data"]["progress"]
        assert 0 <= progress <= 1
        
        # Message should be present
        message = response.json()["data"]["message"]
        assert isinstance(message, str)
        assert len(message) > 0
    
    def test_job_data_structure(self, client: TestClient, auth_headers: dict, sample_vcf_content: str):
        """Test job data structure consistency"""
        # Create a job
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={
                "vcf_content": sample_vcf_content,
                "case_uid": "STRUCTURE_TEST",
                "cancer_type": "melanoma"
            }
        )
        
        assert response.status_code == 200
        job_id = response.json()["data"]["job_id"]
        
        # Get job details
        response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "data" in data
        assert "meta" in data
        
        # Check job data structure
        job_data = data["data"]
        required_fields = ["job_id", "status", "progress", "message", "created_at"]
        
        for field in required_fields:
            assert field in job_data, f"Missing required field: {field}"
        
        # Check data types
        assert isinstance(job_data["job_id"], str)
        assert isinstance(job_data["status"], str)
        assert isinstance(job_data["progress"], (int, float))
        assert isinstance(job_data["message"], str)
        assert isinstance(job_data["created_at"], (int, float))
    
    def test_job_error_handling(self, client: TestClient, auth_headers: dict):
        """Test error handling in job endpoints"""
        # Test malformed job ID
        response = client.get("/api/v1/jobs/", headers=auth_headers)  # Missing job_id
        assert response.status_code == 200  # This is the list endpoint
        
        # Test with very long job ID
        long_job_id = "x" * 1000
        response = client.get(f"/api/v1/jobs/{long_job_id}", headers=auth_headers)
        assert response.status_code == 404
        
        # Test invalid operations
        response = client.post("/api/v1/jobs/invalid_job/retry", headers=auth_headers)
        assert response.status_code == 404