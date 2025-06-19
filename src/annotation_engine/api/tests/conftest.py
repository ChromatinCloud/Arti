"""
Test configuration and fixtures for API tests
"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from annotation_engine.api.main import app
from annotation_engine.api.core.database import get_db
from annotation_engine.db.base import Base


@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    # Create temporary database file
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    db_url = f"sqlite:///{db_path}"
    
    # Set test environment
    os.environ["DATABASE_URL"] = db_url
    os.environ["ENVIRONMENT"] = "testing"
    
    # Create engine and tables
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    Base.metadata.create_all(bind=engine)
    
    yield TestingSessionLocal
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def db_session(test_db):
    """Create database session for test"""
    session = test_db()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(test_db):
    """Create test client with test database"""
    def override_get_db():
        session = test_db()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for tests"""
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo_user", "password": "demo_password"}
    )
    
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    """Get admin authentication headers"""
    # For testing, we'll use the same token but with admin role
    # In production, this would be a separate admin user
    response = client.post(
        "/api/v1/auth/login", 
        json={"username": "demo_user", "password": "demo_password"}
    )
    
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_vcf_content():
    """Sample VCF content for testing"""
    return """##fileformat=VCFv4.2
##reference=GRCh38
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
7	140753336	.	A	T	100	PASS	.	GT:AD:DP:VAF	0/1:50,45:95:0.47
"""


@pytest.fixture
def sample_case_data():
    """Sample case data for testing"""
    return {
        "patient_id": "TEST_PATIENT_001",
        "cancer_type": "melanoma",
        "analysis_type": "tumor_only",
        "tumor_sample_id": "TUMOR_001",
        "clinical_notes": "Test case for API testing"
    }