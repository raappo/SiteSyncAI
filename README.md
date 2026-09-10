# SiteSync AI

Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management.

## Problem Statement
Infrastructure projects suffer from a disconnect between micro-level field execution and macro-level planning schedules (Primavera/MS Project). Updates are manual, error-prone, and delayed. SiteSync AI solves this by bridging the Planning-to-Execution gap using AI.

## Features
- **Multimodal Ingestion**: Ingests text, spreadsheets, PDFs, and Voice (Speech-to-Text).
- **Conversational Time Agent**: LCEL-based LangChain agent to guide field supervisors.
- **LLM Information Extraction**: Extracts structured updates (`ActivityUpdate`) using NVIDIA NIM or ExpLabs APIs.
- **Semantic + Fuzzy Linking**: Matches field updates to the baseline schedule using ChromaDB (embeddings) and RapidFuzz.
- **Smart Routing & Confidence**: Auto-applies high-confidence updates; flags contradictions and low-confidence items for manual review.
- **Project Analytics & Gantt**: Real-time KPI dashboards, SPI tracking, and Plotly Gantt charts.

## Setup
```bash
# 1. Install dependencies
pip install uv
uv sync

# 2. Seed the database
uv run python -m sitesync.db.seed

# 3. Run the web UI
uv run streamlit run frontend/app.py
```

## Running Tests
```bash
uv run pytest tests/ -v
```
