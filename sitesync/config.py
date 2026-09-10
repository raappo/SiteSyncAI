"""
SiteSync AI — Configuration
Pydantic Settings model that reads from the .env file.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
load_dotenv(override=True)

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── NVIDIA NIM (LLM + Embeddings) ───────────────────────────────────────
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_api_key: str = ""
    nvidia_default_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"              # ✅ WORKING
    nvidia_fallback_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"   # ✅ WORKING
    # API-based embedding — zero local download
    nvidia_embedding_model: str = "nvidia/nv-embedqa-mistral-7b-v2"

    # ─── Experiential Labs (tertiary LLM fallback) ────────────────────────────
    explabs_base_url: str = "https://api.experientiallabs.ai/v1"
    explabs_api_key: str = ""
    explabs_fallback_model: str = "laguna-xs-2.1-free"

    # ─── Azure Document Intelligence (OCR / PDF / Image parsing) ─────────────
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # ─── Azure OpenAI (optional — for embeddings if you have Azure OpenAI) ───
    # Leave blank if not configured — system falls back to NVIDIA embeddings
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_api_version: str = "2024-02-01"

    # ─── Local Services ───────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/sitesync.db"
    chroma_persist_dir: str = "data/chroma_db"

    # ─── Business Logic ───────────────────────────────────────────────────────
    confidence_threshold: float = Field(default=0.85, ge=0.0, le=1.0)

    # ─── Evidence weights for multi-signal confidence ─────────────────────────
    evidence_weights: dict[str, float] = {
        "photo": 1.0,
        "spreadsheet": 0.85,
        "scanned_doc": 0.75,
        "text": 0.60,
    }

    # ─── Derived helpers ──────────────────────────────────────────────────────
    @property
    def db_path(self) -> Path:
        url = self.database_url.replace("sqlite:///", "")
        return Path(url)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_persist_dir)

    @property
    def has_nvidia(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def has_explabs(self) -> bool:
        return bool(self.explabs_api_key)

    @property
    def has_azure_di(self) -> bool:
        return bool(
            self.azure_document_intelligence_endpoint
            and self.azure_document_intelligence_key
        )

    @property
    def has_azure_openai(self) -> bool:
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    @property
    def active_models(self) -> list[tuple[str, str, str]]:
        """Return (base_url, api_key, model_id) tuples in priority order."""
        models = []
        if self.has_nvidia:
            models.append((self.nvidia_base_url, self.nvidia_api_key, self.nvidia_default_model))
            if self.nvidia_fallback_model != self.nvidia_default_model:
                models.append((self.nvidia_base_url, self.nvidia_api_key, self.nvidia_fallback_model))
        if self.has_explabs:
            models.append((self.explabs_base_url, self.explabs_api_key, self.explabs_fallback_model))
        return models

    @property
    def embedding_backend(self) -> str:
        """Returns which embedding backend is available: 'azure_openai', 'nvidia', or 'ngram'."""
        if self.has_azure_openai:
            return "azure_openai"
        if self.has_nvidia:
            return "nvidia"
        return "ngram"


# Singleton — import this everywhere
settings = Settings()
