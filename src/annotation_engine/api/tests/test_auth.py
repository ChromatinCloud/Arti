"""
Authentication endpoint tests
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication functionality"""
    
    def test_health_check_no_auth(self, client: TestClient):
        """Test health check works without authentication"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "healthy"
    
    def test_root_endpoint_no_auth(self, client: TestClient):
        """Test root endpoint works without authentication"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "Annotation Engine API" in data["data"]["name"]
    
    def test_login_success(self, client: TestClient):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "demo_user", "password": "demo_password"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["user_info"]["user_id"] == "demo_user"
        assert data["data"]["user_info"]["role"] == "clinician"
    
    def test_login_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "invalid_user", "password": "wrong_password"}
        )
        
        assert response.status_code == 401
        
        data = response.json()
        assert data["success"] is False
        assert "Invalid username or password" in data["error"]["message"]
    
    def test_login_missing_fields(self, client: TestClient):
        """Test login with missing fields"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "demo_user"}  # Missing password
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_current_user(self, client: TestClient, auth_headers: dict):
        """Test getting current user info"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "demo_user"
        assert data["data"]["role"] == "clinician"
        assert "read_cases" in data["data"]["permissions"]
    
    def test_get_current_user_no_token(self, client: TestClient):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 403  # No authorization header
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    def test_refresh_token(self, client: TestClient, auth_headers: dict):
        """Test token refresh"""
        response = client.post("/api/v1/auth/refresh", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
    
    def test_logout(self, client: TestClient, auth_headers: dict):
        """Test logout"""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "logged out" in data["data"]["message"]
    
    def test_change_password(self, client: TestClient, auth_headers: dict):
        """Test password change"""
        response = client.put(
            "/api/v1/auth/password",
            headers=auth_headers,
            json={
                "current_password": "demo_password",
                "new_password": "new_secure_password"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "changed successfully" in data["data"]["message"]