# SiteSync AI

> **Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red.svg)](https://streamlit.io)

## Problem Statement

Infrastructure projects suffer from a disconnect between micro-level field execution and macro-level planning schedules (Primavera/MS Project). Updates are **manual, error-prone, and delayed**. SiteSync AI solves this by bridging the **Planning-to-Execution gap** using AI.

---

## Architecture

```
Field Input (text/PDF/Excel/voice)
        │
        ▼
┌─────────────────┐     ┌──────────────────────────┐
│  Ingestion Layer│────▶│  LLM Extraction Layer     │
│  (doc_parser,   │     │  (NVIDIA NIM → ExpLabs →  │
│   text_agent,   │     │   offline mock fallback)   │
│   voice_agent)  │     │  → ActivityUpdate schema  │
└─────────────────┘     └────────────┬─────────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Linking Layer       │
                          │  Semantic cosine +   │
                          │  RapidFuzz hybrid    │
                          │  → MatchResult       │
                          └──────────┬──────────┘
                                     │
                         ┌───────────▼───────────┐
                         │  Routing Engine        │
                         │  conf ≥ 0.85 → Apply  │
                         │  conf < 0.85 → Review │
                         └───────────┬───────────┘
                                     │
                    ┌────────────────┼──────────────────┐
                    ▼                ▼                   ▼
             Schedule DB       Review Queue        ChromaDB
           (SQLite/SQLAlchemy)  (PENDING items)  (Institutional Memory)
                    │
                    ▼
           Analytics Layer
           (KPI Engine, Forecaster, Gantt Builder)
```

## Modules

| Module | Path | Description |
|--------|------|-------------|
| **Ingestion** | `sitesync/ingestion/` | PDF/Excel/text/voice parsers, LCEL Time Agent |
| **Extraction** | `sitesync/extraction/` | LLM extraction to `ActivityUpdate` schema |
| **Linking** | `sitesync/linking/` | Semantic + fuzzy schedule matching with confidence |
| **Routing** | `sitesync/routing/` | Auto-apply vs review-queue decision engine |
| **Analytics** | `sitesync/analytics/` | KPI engine, SPI forecaster, Plotly Gantt |
| **Memory** | `sitesync/memory/` | ChromaDB institutional project memory |
| **DB** | `sitesync/db/` | SQLAlchemy models, session, seed script |
| **Config** | `sitesync/config.py` | Pydantic Settings (env vars, API keys) |
| **API** | `api/` | FastAPI REST layer |

## LLM & Embedding Priority

| Tier | Provider | Purpose |
|------|----------|---------|
| 1st | NVIDIA NIM | LLM extraction + embeddings |
| 2nd | Experiential Labs | LLM fallback (free tier) |
| 3rd | Azure OpenAI | Embedding alternative |
| Offline | N-gram hashing | Zero-download embedding fallback |

## Setup

```bash
# 1. Install dependencies (uses uv)
pip install uv
uv sync

# 2. Copy and fill in your API keys
cp .env.example .env
# Edit .env with your NVIDIA_API_KEY or EXPLABS_API_KEY

# 3. Seed the database with the baseline schedule
uv run sitesync-seed
# or: uv run python -m sitesync.db.seed

# 4. Run the Streamlit web UI
uv run streamlit run frontend/app.py

# 5. (Optional) Run the FastAPI backend
uv run uvicorn api.main:app --reload --port 8000
```

## Sample Data

| File | Description |
|------|-------------|
| `data/baseline_schedule.csv` | 50 realistic L5/L6 EPC activities (Civil, Piping, Electrical, Instrumentation, HSE) — used to seed the schedule DB |
| `data/sample_field_updates.csv` | 20 realistic field progress update rows — use as spreadsheet input in the UI |
| `data/site_diary_text.txt` | Sample daily progress report (site diary) — use as text input in the UI |
| `data/piping_progress.xlsx` | Sample Excel piping progress report — use as spreadsheet input |

## API Reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/process` | Extract → Link → Route a field update |
| `GET` | `/api/v1/queue` | Get all PENDING review queue items |
| `GET` | `/api/v1/memory?q=<query>` | Semantic search in project memory |
| `GET` | `/api/v1/memory/stats` | Memory collection stats |
| `GET` | `/docs` | Interactive Swagger UI |

### Example: Process a field update

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "Piping team welded 9 joints on Line 24-HO-101 hot oil line today, total 32% progress.", "evidence_type": "text"}'
```

## Running Tests

```bash
# Run all tests with verbose output
uv run pytest tests/ -v

# Run a specific test file
uv run pytest tests/test_linker.py -v

# Run with coverage (install pytest-cov first)
uv run pytest tests/ --cov=sitesync --cov-report=term-missing
```

### Test Coverage

| Test File | What It Tests |
|-----------|---------------|
| `test_config.py` | Settings, API key detection, embedding backend |
| `test_extractor.py` | JSON parsing, mock fallback, date normalization |
| `test_linker.py` | Confidence scoring, semantic matching, edge cases |
| `test_router.py` | Auto-apply, review queue, contradiction detection |
| `test_pipeline_integration.py` | End-to-end Extract→Link→Route pipeline |
| `test_doc_parser.py` | PDF/Excel/text/image parsing |
| `test_analytics.py` | KPI engine, forecaster, Gantt builder |
| `test_raptor.py` | Hybrid matcher, abbreviation expansion |
| `test_memory.py` | ChromaDB upsert, query, filtering |
| `test_api.py` | FastAPI endpoints |

## Confidence Formula

```
confidence = (0.60 × semantic_cosine)
           + (0.25 × evidence_weight)
           + (0.15 × temporal_score)

Evidence weights: photo=1.0, spreadsheet=0.85, scanned_doc=0.75, text=0.60
Temporal score: 1.0 if date within planned window, decays linearly beyond ±30 days
```

Auto-apply threshold: `0.85` (configurable via `CONFIDENCE_THRESHOLD` in `.env`)
