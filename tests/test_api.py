from fastapi.testclient import TestClient
from api.main import app
from api.api_key_validator import validate_api_keys

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "version": "1.0.0"}

def test_get_queue():
    response = client.get("/api/v1/queue")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_memory_stats():
    response = client.get("/api/v1/memory/stats")
    assert response.status_code == 200
    assert "total_events" in response.json()

def test_api_key_validator():
    errors = validate_api_keys()
    assert isinstance(errors, list)
