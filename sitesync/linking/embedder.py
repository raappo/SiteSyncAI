"""
SiteSync AI — API-Based Embedder (Zero Local Download)

Embedding priority (all API-based, no model files downloaded):
  1. Azure OpenAI Embeddings  — if AZURE_OPENAI_* keys configured
  2. NVIDIA NIM Embeddings    — nvidia/nv-embedqa-mistral-7b-v2 (free with NIM key)
  3. N-gram character hashing — deterministic offline fallback (always works)

No torch. No sentence-transformers. No heavy downloads. GitHub-friendly.
"""
from __future__ import annotations

import hashlib
import pickle
from typing import Optional

import numpy as np
import requests
from rich.console import Console

from sitesync.config import settings

console = Console()

# In-process memory cache: avoids re-embedding identical strings
_embed_cache: dict[str, np.ndarray] = {}


# ─── Backend 1: Azure OpenAI Embeddings ──────────────────────────────────────

def _embed_azure_openai(text: str) -> Optional[np.ndarray]:
    """
    Call Azure OpenAI Embeddings endpoint.
    Requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env.
    Model: text-embedding-3-small (1536-dim) — cheap & fast.
    """
    if not settings.has_azure_openai:
        return None

    url = (
        f"{settings.azure_openai_endpoint.rstrip('/')}"
        f"/openai/deployments/{settings.azure_openai_embedding_deployment}"
        f"/embeddings?api-version={settings.azure_openai_api_version}"
    )
    try:
        r = requests.post(
            url,
            headers={
                "api-key": settings.azure_openai_api_key,
                "Content-Type": "application/json",
            },
            json={"input": text, "model": settings.azure_openai_embedding_deployment},
            timeout=15,
        )
        if r.status_code == 200:
            vec = np.array(r.json()["data"][0]["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        else:
            console.print(f"[yellow]Azure OAI embed HTTP {r.status_code}[/yellow]")
            return None
    except Exception as e:
        console.print(f"[yellow]Azure OAI embed error: {e}[/yellow]")
        return None


# ─── Backend 2: NVIDIA NIM Embeddings ────────────────────────────────────────

def _embed_nvidia(text: str, input_type: str = "passage") -> Optional[np.ndarray]:
    """
    Call NVIDIA NIM embedding API.
    Model: nvidia/nv-embedqa-mistral-7b-v2 (4096-dim)
    input_type: 'passage' for indexing, 'query' for search.
    """
    if not settings.has_nvidia:
        return None

    try:
        r = requests.post(
            f"{settings.nvidia_base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "input": text,
                "model": settings.nvidia_embedding_model,
                "input_type": input_type,
                "truncate": "END",
                "encoding_format": "float",
            },
            timeout=15,
        )
        if r.status_code == 200:
            vec = np.array(r.json()["data"][0]["embedding"], dtype=np.float32)
            norm = np.linalg.norm(vec)
            return vec / norm if norm > 0 else vec
        else:
            console.print(f"[yellow]NVIDIA embed HTTP {r.status_code}: {r.text[:60]}[/yellow]")
            return None
    except Exception as e:
        console.print(f"[yellow]NVIDIA embed error: {e}[/yellow]")
        return None


# ─── Backend 3: N-gram character hashing (always-on offline fallback) ────────

def _embed_ngram(text: str, dim: int = 384) -> np.ndarray:
    """
    Deterministic character tri-gram hashing into a dense vector.
    Not semantic, but reproducible and works with zero internet.
    Used ONLY when all API backends are unavailable.
    """
    text = text.lower()
    vec = np.zeros(dim, dtype=np.float32)
    for i in range(max(len(text) - 2, 1)):
        trigram = text[i:i + 3]
        h = int(hashlib.md5(trigram.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


# ─── Public API ───────────────────────────────────────────────────────────────

def embed_text(text: str, input_type: str = "query") -> np.ndarray:
    """
    Embed a text string using the best available backend (with caching).

    Priority: Azure OpenAI → NVIDIA NIM → N-gram fallback
    input_type: 'query' for matching, 'passage' for indexing schedule nodes.
    """
    cache_key = f"{input_type}:{text}"
    if cache_key in _embed_cache:
        return _embed_cache[cache_key]

    vec: Optional[np.ndarray] = None
    backend_used = "?"

    # 1. Azure OpenAI
    if settings.has_azure_openai:
        vec = _embed_azure_openai(text)
        if vec is not None:
            backend_used = "Azure OpenAI"

    # 2. NVIDIA NIM
    if vec is None and settings.has_nvidia:
        vec = _embed_nvidia(text, input_type=input_type)
        if vec is not None:
            backend_used = "NVIDIA NIM"

    # 3. Offline n-gram fallback
    if vec is None:
        vec = _embed_ngram(text)
        backend_used = "n-gram (offline)"
        console.print(
            "[dim yellow]⚠ Using offline n-gram embedder — semantic matching quality reduced[/dim yellow]"
        )

    _embed_cache[cache_key] = vec
    return vec


def embed_text_passage(text: str) -> np.ndarray:
    """Embed a document/schedule passage (for indexing)."""
    return embed_text(text, input_type="passage")


def serialize(vec: np.ndarray) -> bytes:
    """Serialize numpy array → bytes for SQLite BLOB storage."""
    return pickle.dumps(vec.astype(np.float32))


def deserialize(blob: bytes) -> np.ndarray:
    """Deserialize bytes from SQLite BLOB → numpy array."""
    return pickle.loads(blob).astype(np.float32)
