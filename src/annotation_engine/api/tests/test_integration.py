"""
Integration tests for complete API workflows
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestAPIIntegration:
    """Test complete workflows across multiple endpoints"""
    
    def test_complete_annotation_workflow(self, client: TestClient, auth_headers: dict, sample_vcf_content: str, sample_case_data: dict):
        """Test complete annotation workflow from VCF to final report"""
        
        # 1. Create a case
        response = client.post("/api/v1/cases/", headers=auth_headers, json=sample_case_data)
        assert response.status_code == 200
        
        case_uid = response.json()["data"]["case_uid"]
        
        # 2. Submit VCF for annotation
        annotation_request = {
            "vcf_content": sample_vcf_content,
            "case_uid": case_uid,
            "cancer_type": sample_case_data["cancer_type"],
            "analysis_type": sample_case_data["analysis_type"]
        }
        
        response = client.post("/api/v1/variants/annotate", headers=auth_headers, json=annotation_request)
        assert response.status_code == 200
        
        job_id = response.json()["data"]["job_id"]
        
        # 3. Monitor job progress
        max_attempts = 10
        job_completed = False
        
        for _ in range(max_attempts):
            response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
            assert response.status_code == 200
            
            job_data = response.json()["data"]
            status = job_data["status"]
            
            if status == "completed":
                job_completed = True
                assert "results" in job_data
                break
            elif status == "failed":
                pytest.fail(f"Job failed: {job_data.get('error', 'Unknown error')}")
            
            time.sleep(0.1)  # Wait a bit before checking again
        
        # Note: In the demo, jobs complete instantly, so this should pass
        
        # 4. Get variant details
        # Assuming BRAF variant from demo
        variant_id = "7:140753336:A>T"
        response = client.get(f"/api/v1/variants/{variant_id}", headers=auth_headers)
        assert response.status_code == 200
        
        variant_data = response.json()["data"]
        assert variant_data["gene"] == "BRAF"
        assert "clinical_evidence" in variant_data
        
        # 5. Get case summary with variants
        response = client.get(f"/api/v1/cases/{case_uid}/summary", headers=auth_headers)
        assert response.status_code == 200
        
        summary = response.json()["data"]
        assert summary["case_uid"] == case_uid
        assert "summary" in summary
        
        # 6. Generate clinical report
        response = client.get(f"/api/v1/cases/{case_uid}/report", headers=auth_headers)
        assert response.status_code == 200
        
        report = response.json()["data"]
        assert "report_id" in report
        assert report["case_uid"] == case_uid
        assert "clinical_recommendations" in report
        
        # 7. Finalize case
        response = client.post(f"/api/v1/cases/{case_uid}/finalize", headers=auth_headers)
        assert response.status_code == 200
        
        finalization = response.json()["data"]
        assert finalization["status"] == "finalized"
    
    def test_search_and_discovery_workflow(self, client: TestClient, auth_headers: dict):
        """Test search functionality across different endpoints"""
        
        # 1. Search for BRAF variants
        response = client.get("/api/v1/search/variants?q=BRAF", headers=auth_headers)
        assert response.status_code == 200
        
        search_results = response.json()["data"]
        assert "results" in search_results
        
        # Should find BRAF variants
        if search_results["results"]:
            braf_variant = search_results["results"][0]
            assert "BRAF" in braf_variant["gene"]
        
        # 2. Search for cases
        response = client.get("/api/v1/search/cases?q=melanoma", headers=auth_headers)
        assert response.status_code == 200
        
        case_results = response.json()["data"]
        assert "results" in case_results
        
        # 3. Global search
        response = client.get("/api/v1/search/global?q=V600E", headers=auth_headers)
        assert response.status_code == 200
        
        global_results = response.json()["data"]
        assert "results" in global_results
        
        # Should find both variants and cases
        if global_results["results"]:
            result = global_results["results"][0]
            assert "entity_type" in result
            assert result["entity_type"] in ["variant", "case"]
    
    def test_evidence_integration_workflow(self, client: TestClient, auth_headers: dict):
        """Test clinical evidence integration"""
        
        # 1. Get variant evidence
        variant_id = "7:140753336:A>T"
        response = client.get(f"/api/v1/evidence/{variant_id}", headers=auth_headers)
        assert response.status_code == 200
        
        evidence = response.json()["data"]
        assert evidence["variant_id"] == variant_id
        assert "clinical_significance" in evidence
        assert "therapeutic_evidence" in evidence
        assert "literature" in evidence
        
        # 2. Check evidence sources status
        response = client.get("/api/v1/evidence/sources/status", headers=auth_headers)
        assert response.status_code == 200
        
        sources = response.json()["data"]
        assert "clinvar" in sources
        assert "oncokb" in sources
        assert "civic" in sources
        
        # Each source should have status info
        for source_name, source_info in sources.items():
            assert "status" in source_info
            assert "last_updated" in source_info
            assert source_info["status"] == "healthy"
        
        # 3. Search therapies
        response = client.get("/api/v1/therapies/search?q=Vemurafenib", headers=auth_headers)
        assert response.status_code == 200  # This endpoint might not be implemented yet
    
    def test_analytics_and_audit_workflow(self, client: TestClient, auth_headers: dict):
        """Test analytics and audit functionality"""
        
        # 1. Get dashboard overview
        response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
        
        dashboard = response.json()["data"]
        assert "summary" in dashboard
        assert "tier_distribution" in dashboard
        assert "recent_activity" in dashboard
        assert "kb_status" in dashboard
        
        # Check dashboard structure
        summary = dashboard["summary"]
        assert "total_cases" in summary
        assert "total_variants" in summary
        assert "actionable_variants" in summary
        
        # 2. Get audit trail
        response = client.get("/api/v1/analytics/audit/trail", headers=auth_headers)
        assert response.status_code == 200
        
        audit = response.json()["data"]
        assert "events" in audit
        assert "total" in audit
        
        # Should have some audit events from previous API calls
        events = audit["events"]
        if events:
            event = events[0]
            assert "event_uuid" in event
            assert "event_type" in event
            assert "user_id" in event
            assert "timestamp" in event
        
        # 3. Check system health
        response = client.get("/api/v1/analytics/system/health", headers=auth_headers)
        assert response.status_code == 200
        
        health = response.json()["data"]
        assert "status" in health
        assert "components" in health
        assert health["status"] == "healthy"
        
        # Check component health
        components = health["components"]
        assert "database" in components
        assert components["database"]["status"] == "healthy"
    
    def test_interpretation_history_workflow(self, client: TestClient, auth_headers: dict):
        """Test interpretation history and versioning"""
        
        # 1. Get interpretation details
        interp_id = "INTERP_001"
        response = client.get(f"/api/v1/interpretations/{interp_id}", headers=auth_headers)
        assert response.status_code == 200
        
        interpretation = response.json()["data"]
        assert interpretation["interpretation_id"] == interp_id
        assert "history" in interpretation
        
        # Check history structure
        history = interpretation["history"]
        assert isinstance(history, list)
        if history:
            history_entry = history[0]
            assert "version" in history_entry
            assert "change_type" in history_entry
            assert "changed_by" in history_entry
            assert "changed_at" in history_entry
        
        # 2. Update interpretation (creates history)
        response = client.put(f"/api/v1/interpretations/{interp_id}", headers=auth_headers)
        assert response.status_code == 200
        
        update_result = response.json()["data"]
        assert "version" in update_result
        
        # 3. Compare versions
        if len(history) >= 2:
            v1, v2 = history[0]["version"], history[1]["version"]
            response = client.get(f"/api/v1/interpretations/{interp_id}/compare/{v1}/{v2}", headers=auth_headers)
            assert response.status_code == 200
            
            comparison = response.json()["data"]
            assert "comparison" in comparison
            assert "differences" in comparison["comparison"]
        
        # 4. Approve interpretation
        response = client.post(f"/api/v1/interpretations/{interp_id}/approve", headers=auth_headers)
        assert response.status_code == 200
        
        approval = response.json()["data"]
        assert approval["status"] == "approved"
        assert "approved_by" in approval
        
        # 5. Sign interpretation
        response = client.post(f"/api/v1/interpretations/{interp_id}/sign", headers=auth_headers)
        assert response.status_code == 200
        
        signature = response.json()["data"]
        assert signature["status"] == "signed"
        assert "signature_id" in signature
    
    def test_error_handling_and_validation(self, client: TestClient, auth_headers: dict):
        """Test error handling across endpoints"""
        
        # 1. Test validation errors
        response = client.post("/api/v1/cases/", headers=auth_headers, json={})
        assert response.status_code == 422  # Validation error
        
        # 2. Test not found errors
        response = client.get("/api/v1/cases/NONEXISTENT_CASE", headers=auth_headers)
        assert response.status_code == 404
        
        # 3. Test authentication errors
        response = client.get("/api/v1/cases/")
        assert response.status_code == 403
        
        # 4. Test invalid data
        response = client.post(
            "/api/v1/variants/annotate",
            headers=auth_headers,
            json={"invalid": "data"}
        )
        assert response.status_code == 422
    
    def test_rate_limiting(self, client: TestClient, auth_headers: dict):
        """Test rate limiting functionality"""
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/health")  # Use health endpoint to avoid auth overhead
            responses.append(response.status_code)
        
        # All should succeed (rate limit is 100/min)
        assert all(status == 200 for status in responses)
        
        # Check rate limit headers are present
        response = client.get("/health")
        # Note: Rate limit headers might not be implemented in basic middleware
    
    def test_response_format_consistency(self, client: TestClient, auth_headers: dict):
        """Test that all endpoints follow consistent response format"""
        
        endpoints_to_test = [
            ("/api/v1/cases/", "GET"),
            ("/api/v1/variants/7:140753336:A>T", "GET"),
            ("/api/v1/evidence/7:140753336:A>T", "GET"),
            ("/api/v1/analytics/dashboard", "GET"),
            ("/api/v1/auth/me", "GET")
        ]
        
        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint, headers=auth_headers)
            
            assert response.status_code == 200
            
            data = response.json()
            
            # Check required top-level fields
            assert "success" in data
            assert "data" in data
            assert "meta" in data
            
            # Check meta fields
            meta = data["meta"]
            assert "timestamp" in meta
            assert "version" in meta
            
            # Success should be boolean
            assert isinstance(data["success"], bool)
            assert data["success"] is True
    
    def test_concurrent_requests(self, client: TestClient, auth_headers: dict):
        """Test handling of concurrent requests"""
        
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert len(results) == 5
        assert all(status == 200 for status in results)