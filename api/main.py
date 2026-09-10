from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
from typing import List, Optional

from sitesync.config import settings
from sitesync.extraction.extractor import get_extractor
from sitesync.linking.matcher import get_matcher
from sitesync.routing.router import route
from sitesync.db.session import get_db
from sitesync.db.models import ReviewQueueItem
from sitesync.memory.chroma_store import query_memory, memory_stats

app = FastAPI(title="SiteSync AI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    raw_input: str
    evidence_type: str = "text"

class RouteResultResponse(BaseModel):
    status: str
    message: str
    event_id: Optional[int] = None
    queue_id: Optional[int] = None
    updates_extracted: int
    ms_elapsed: int

from api.api_key_validator import validate_api_keys

@app.on_event("startup")
def startup_event():
    print("🚀 Initializing SiteSync AI Backend...")
    errors = validate_api_keys()
    if errors:
        print("⚠️ Warning: Some API keys failed validation. Fallback mocks will be used if APIs are unreachable.")
    print("✅ System Ready")

@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/api/v1/process", response_model=RouteResultResponse)
def process_update(req: ExtractRequest):
    t_start = time.perf_counter()
    
    # 1. Extract
    ext_result = get_extractor().extract(req.raw_input, req.evidence_type)
    if not ext_result.updates:
        raise HTTPException(status_code=400, detail="Failed to extract any activity updates")
        
    # We'll just process the first extracted update for simplicity in the API response
    update = ext_result.updates[0]
    
    # 2. Link
    link_result = get_matcher().match(update)
    
    # 3. Route
    event = route(link_result, source_file=None)
        
    ms_elapsed = int((time.perf_counter() - t_start) * 1000)
    
    return RouteResultResponse(
        status=event.action_taken,
        message=f"Routed as {event.action_taken}",
        event_id=event.id,
        queue_id=None, # ReviewQueue logic handled internally
        updates_extracted=len(ext_result.updates),
        ms_elapsed=ms_elapsed
    )

@app.get("/api/v1/queue")
def get_queue():
    with get_db() as db:
        items = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").all()
        return [
            {
                "id": item.id,
                "status": item.status,
                "created_at": item.created_at,
                "planner_notes": item.planner_notes
            } for item in items
        ]

@app.get("/api/v1/memory")
def search_memory(q: str, discipline: Optional[str] = None, n: int = 5):
    results = query_memory(q, discipline_filter=discipline, n_results=n)
    return {"query": q, "results": results}

@app.get("/api/v1/memory/stats")
def get_memory_stats():
    return memory_stats()
