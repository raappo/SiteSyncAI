# 🏗️ SiteSync AI

**Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management**

*Built for Smart India Hackathon 2024 — Problem ID 26122 (Oil India Limited)*

![SiteSync Dashboard Placeholder](https://img.shields.io/badge/Status-Working_Prototype-brightgreen)
![Tech Stack](https://img.shields.io/badge/Tech-Python_|_Streamlit_|_LangChain_|_NVIDIA_NIM-blue)

## 📌 Problem Statement

Infrastructure mega-projects (such as those managed by Oil India Limited) rely on complex Level 5/Level 6 Primavera or MS Project schedules. However, field execution data comes in completely unstructured, messy formats: 
- 💬 Jargon-heavy WhatsApp messages from site supervisors
- 📄 Scanned daily progress reports (PDFs) and hand-written site diaries
- 📸 Field photos 
- 📊 Excel spreadsheets with non-standard naming conventions

**The Bottleneck:** Planners spend hours manually decoding this chaotic field data and trying to map it to specific L5/L6 activity nodes. This results in delayed schedule updates, human error, data silos, and ultimately, a reactive rather than proactive project management approach.

---

## 💡 The Proposed Solution (SiteSync AI)

**SiteSync AI** is an autonomous, multimodal ingestion engine that accepts ANY unstructured field input, uses Large Language Models (LLMs) to structure the data, and utilizes semantic vector similarity to automatically link the field update to the correct L5/L6 schedule node.

Our solution operates in 5 core phases:

### Phase 1: Multimodal Ingestion Layer (The "Time Agent")
Instead of forcing field workers to learn a new, complex software interface, SiteSync AI meets them where they are. 
- Supervisors can simply **speak** to the Time Agent (Voice-to-Text), send a raw text update, or upload site diaries/spreadsheets.
- Azure Document Intelligence handles high-accuracy OCR on scanned PDFs and images.

### Phase 2: Intelligent LLM Extraction
The raw, jargon-heavy input is passed to our LLM layer (powered by NVIDIA NIM / Llama 3.1). 
- The LLM acts as an expert project analyst, aggressively extracting the actual progress, dates, locations, and blockers, and standardizing them into a strict JSON payload.
- *Robustness:* The system is built with bulletproof regex boundary parsers and offline fallback mechanisms. If the primary API rate-limits, it seamlessly degrades to secondary APIs or offline mock processing to guarantee zero downtime.

### Phase 3: Semantic Linking Engine
Once the data is structured, it must be mapped to the 10,000+ line Primavera schedule.
- We use a **3-Tier API Embedding Strategy**: Azure OpenAI Embeddings → NVIDIA NIM `nv-embedqa-mistral` → Offline N-Gram Hashing (fallback).
- The engine calculates a **Multi-Signal Confidence Score** weighing Semantic Similarity (60%), Evidence Type Reliability (25% - e.g., verified spreadsheets weigh more than text), and Temporal Plausibility (15%).

### Phase 4: Autonomous Application & Planner Review
- **Auto-Apply (≥85% Confidence):** If the mathematical match is overwhelmingly positive, the actual progress is automatically applied to the schedule database.
- **Human-in-the-Loop (<85% Confidence):** Ambiguous updates are flagged and sent to a beautiful, card-based **Planner Review Queue**. The planner sees the raw text, the matched node, and a visual Confidence Breakdown bar, allowing them to approve or remap with one click.

### Phase 5: Institutional Memory
Every processed event is vectorized and stored in a pure-Python **ChromaDB** database. 
- Planners can use the **Memory Query** interface to search: *"How long did piping spools take on similar hot oil lines?"* or *"What bottlenecks occurred during civil foundations?"*
- This turns individual project delays into queryable, organizational knowledge to prevent the same mistakes on future projects.

---

## 🚀 The Prototype UI

We built a fully functional, OS-agnostic prototype using a premium **Slate Dark Industrial** Enterprise PMIS theme. The interface features:
- **Split-Pane Architecture:** Real-time extraction payloads load instantly alongside chat inputs.
- **Card Decks:** Clean, modern cards for schedule views and memory queries.
- **Early Warning Strips:** The live schedule automatically flags activities that have fallen critically behind schedule (<20% progress past planned dates).

---

## 🛠️ How to Run Locally

While V1 is optimized for hackathon demonstrations (100% API-based for sub 200MB footprint and zero-GPU requirement), the architecture is designed to scale to enterprise deployments (e.g., local vLLM / Ollama for air-gapped networks).

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Extremely fast Python package installer)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/sitesync-ai.git
   cd sitesync-ai
   ```

2. **Set up the environment:**
   Create a `.env` file in the root directory (refer to `.env.example`). You will need an NVIDIA NIM API key.

3. **Install dependencies:**
   ```bash
   uv sync --no-dev
   ```

4. **Seed the database:**
   This reads the baseline schedule (`data/baseline_schedule.csv`), embeds the descriptions, and initializes SQLite.
   ```bash
   uv run python -m sitesync.db.seed
   ```

5. **Run the Dashboard:**
   ```bash
   uv run streamlit run frontend/app.py
   ```

The application will be available at `http://localhost:8501`.

---
*Built with ❤️ for Smart India Hackathon 2024*
