"""
Tests for the configuration module.
"""
import pytest

class TestSettings:
    """Tests for Settings configuration."""

    def test_active_models_empty_when_no_keys(self):
        """With no API keys, active_models should be empty."""
        from sitesync.config import Settings
        s = Settings(
            nvidia_api_key="",
            explabs_api_key="",
        )
        assert s.active_models == []

    def test_has_nvidia_false_when_empty(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="")
        assert s.has_nvidia is False

    def test_has_nvidia_true_when_set(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key-123")
        assert s.has_nvidia is True

    def test_embedding_backend_ngram_when_no_keys(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="", azure_openai_api_key="", azure_openai_endpoint="")
        assert s.embedding_backend == "ngram"

    def test_embedding_backend_nvidia_when_only_nvidia_set(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key", azure_openai_api_key="", azure_openai_endpoint="")
        assert s.embedding_backend == "nvidia"

    def test_embedding_backend_azure_takes_priority(self):
        from sitesync.config import Settings
        s = Settings(
            nvidia_api_key="test-nvidia",
            azure_openai_api_key="test-azure",
            azure_openai_endpoint="https://example.azure.com/",
        )
        assert s.embedding_backend == "azure_openai"

    def test_confidence_threshold_default(self):
        from sitesync.config import Settings
        s = Settings()
        assert s.confidence_threshold == 0.85

    def test_has_azure_di_false_when_incomplete(self):
        from sitesync.config import Settings
        s = Settings(azure_document_intelligence_endpoint="https://example.com", azure_document_intelligence_key="")
        assert s.has_azure_di is False

    def test_active_models_nvidia_only(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key", explabs_api_key="")
        models = s.active_models
        assert len(models) >= 1
        assert any("nvidia" in url or "nvidia" in model_id for url, key, model_id in models)
