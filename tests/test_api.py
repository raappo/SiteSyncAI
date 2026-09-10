"""
Tests for the FastAPI REST API layer.
Uses FastAPI TestClient with mocked pipeline dependencies.
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """Create a TestClient with fully mocked pipeline internals."""
    from fastapi.testclient import TestClient

    # We import the app AFTER overriding env so DB goes to tmp
    with patch("sitesync.extraction.extractor.get_extractor") as mock_ext, \
         patch("sitesync.linking.matcher.get_matcher") as mock_match, \
         patch("sitesync.routing.router.get_db"), \
         patch("sitesync.memory.chroma_store._get_collection"):

        from api.main import app
        return TestClient(app, raise_server_exceptions=False)


def test_health_check():
    """Health endpoint should return 200 and healthy status."""
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"


def test_get_queue_returns_list():
    """Queue endpoint should return a list (possibly empty).
    Uses the real (production) DB connection which may be empty — that's fine.
    """
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/queue")
    # Should return 200 with a list (may be empty if no pending items)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_memory_stats_returns_dict():
    """Memory stats endpoint should return a dict."""
    from fastapi.testclient import TestClient
    from api.main import app

    with patch("api.main.memory_stats", return_value={"total_events": 0, "collection": "test"}):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/memory/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data


def test_api_key_validator_returns_list():
    """validate_api_keys() should always return a list."""
    from api.api_key_validator import validate_api_keys
    errors = validate_api_keys()
    assert isinstance(errors, list)
