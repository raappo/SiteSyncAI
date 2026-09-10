"""
SiteSync AI — Institutional Memory (ChromaDB)

Persists finalized project execution events into ChromaDB for
semantic historical querying. Enables future project planning teams
to query: "show me past piping delays similar to this" or
"what was the actual duration for tank farm civil foundations?"
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Optional

from rich.console import Console

from sitesync.config import settings

console = Console()

_COLLECTION_NAME = "sitesync_project_memory"


def _get_client():
    """Get or create ChromaDB persistent client."""
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(settings.chroma_path),
        )
        return client
    except ImportError:
        console.print("[red]chromadb not installed. Run: uv sync[/red]")
        raise


def _get_collection():
    """Get or create the project memory collection."""
    client = _get_client()
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def upsert_event(
    event_id: int,
    activity_id: str,
    discipline: str,
    activity_description: str,
    actual_progress_pct: float,
    report_date: str,
    evidence_type: str,
    planned_start: Optional[str] = None,
    planned_end: Optional[str] = None,
    actual_start: Optional[str] = None,
    actual_end: Optional[str] = None,
    constraints: Optional[list[str]] = None,
    confidence_score: Optional[float] = None,
    extra_metadata: Optional[dict] = None,
) -> None:
    """
    Upsert a finalized event into ChromaDB project memory.
    The document text is a rich narrative for semantic search.
    """
    collection = _get_collection()

    # Compute actual duration if we have both dates
    actual_duration_days: Optional[int] = None
    if actual_start and actual_end:
        try:
            from datetime import date
            fmt = "%Y-%m-%d"
            d1 = datetime.strptime(actual_start, fmt).date()
            d2 = datetime.strptime(actual_end, fmt).date()
            actual_duration_days = (d2 - d1).days
        except Exception:
            pass

    # Narrative document for semantic embedding
    document = (
        f"Discipline: {discipline}. "
        f"Activity: {activity_description}. "
        f"Progress: {actual_progress_pct:.1f}% on {report_date}. "
        f"Evidence: {evidence_type}. "
        + (f"Constraints: {'; '.join(constraints)}. " if constraints else "")
        + (f"Actual duration: {actual_duration_days} days. " if actual_duration_days else "")
    )

    metadata: dict[str, Any] = {
        "event_id": event_id,
        "activity_id": activity_id,
        "discipline": discipline,
        "report_date": report_date,
        "actual_progress_pct": actual_progress_pct,
        "evidence_type": evidence_type,
        "confidence_score": confidence_score or 0.0,
        "constraints": json.dumps(constraints or []),
        "indexed_at": datetime.utcnow().isoformat(),
    }
    if actual_duration_days is not None:
        metadata["actual_duration_days"] = actual_duration_days
    if planned_start:
        metadata["planned_start"] = planned_start
    if planned_end:
        metadata["planned_end"] = planned_end
    if extra_metadata:
        metadata.update(extra_metadata)

    doc_id = f"event_{event_id}_{activity_id}"

    collection.upsert(
        ids=[doc_id],
        documents=[document],
        metadatas=[metadata],
    )
    console.print(f"[dim]📚 Memory upserted: {doc_id}[/dim]")


def query_memory(
    query_text: str,
    discipline_filter: Optional[str] = None,
    n_results: int = 5,
) -> list[dict]:
    """
    Semantic search across institutional memory.

    Args:
        query_text: Natural language query (e.g., "piping delays due to material shortage")
        discipline_filter: Optional filter (Civil/Piping/Electrical/etc.)
        n_results: Number of results to return.

    Returns:
        List of result dicts with document, metadata, and distance.
    """
    collection = _get_collection()

    where_filter = {}
    if discipline_filter:
        where_filter = {"discipline": {"$eq": discipline_filter}}

    kwargs = {
        "query_texts": [query_text],
        "n_results": min(n_results, collection.count() or 1),
        "include": ["documents", "metadatas", "distances"],
    }
    if where_filter:
        kwargs["where"] = where_filter

    try:
        results = collection.query(**kwargs)
    except Exception as e:
        console.print(f"[red]Memory query failed: {e}[/red]")
        return []

    output = []
    if results and results.get("ids") and results["ids"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "document": doc,
                "metadata": meta,
                "similarity": round(1.0 - dist, 4),
            })

    return output


def memory_stats() -> dict:
    """Return basic stats about the memory collection."""
    try:
        collection = _get_collection()
        count = collection.count()
        return {"total_events": count, "collection": _COLLECTION_NAME}
    except Exception as e:
        return {"error": str(e)}
