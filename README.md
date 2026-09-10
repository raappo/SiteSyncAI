# 🏗️ SiteSync AI

**Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management**

*Built for Smart India Hackathon 2024 — Problem ID 26122 (Oil India Limited)*

![SiteSync Dashboard Placeholder](https://img.shields.io/badge/Status-Working_Prototype-brightgreen)
![Tech Stack](https://img.shields.io/badge/Tech-Python_|_Streamlit_|_LangChain_|_NVIDIA_NIM-blue)

## 📌 Problem Statement

Infrastructure projects (like Oil India Limited's installations) rely on massive Level 5/Level 6 Primavera or MS Project schedules. However, field execution data comes in completely unstructured formats: 
- 💬 Messy WhatsApp messages from supervisors
- 📄 Scanned daily progress reports (PDFs)
- 📸 Field photos
- 📊 Excel spreadsheets with non-standard naming conventions

**The Problem:** Planners spend hours manually decoding this messy field data and trying to figure out which specific L5/L6 activity node it belongs to, resulting in delayed schedule updates, human error, and "garbage in, garbage out" reporting.

**Our Solution (SiteSync AI):** An autonomous, multimodal ingestion engine that accepts ANY unstructured field input, uses Large Language Models (LLMs) to structure the data, and uses vector similarity matching to automatically link the field update to the correct L5/L6 schedule node.

---

## 🚀 Current Working Prototype (V1)

We have built a fully functional, highly optimized, OS-agnostic prototype that demonstrates the entire end-to-end pipeline. 

To ensure maximum portability and zero heavy downloads (no `torch` or `sentence-transformers` required locally), we have shifted to a **100% API-Based Architecture** for the initial MVP.

### ✅ What is Working Right Now:

1. **Multimodal Data Ingestion Layer:**
   - **Time Agent (Chat):** A conversational AI that guides field supervisors to input their daily progress, asking clarifying questions if discipline, location, or quantities are missing.
   - **Document Parsing:** Integrates **Azure Document Intelligence** for high-accuracy OCR on scanned PDFs and images, with fallbacks to `pdfplumber` and `openpyxl`.

2. **LLM Extraction Engine:**
   - Uses **NVIDIA NIM (`nvidia/nemotron-3.5-lightning-30b-a3b`)** to parse messy, unstructured text into a strict JSON schema (`ActivityUpdate`).
   - Handles multi-model failovers seamlessly if primary APIs rate-limit.

3. **Semantic Linking & Matching (Zero-Local-Weight):**
   - Uses a **3-Tier API Embedding Strategy** for matching field updates to schedule nodes:
     1. *Azure OpenAI Embeddings (if configured)*
     2. *NVIDIA NIM Embeddings (`nv-embedqa-mistral-7b-v2`)*
     3. *Offline Deterministic N-Gram Hashing (Always-on fallback)*
   - Uses pure Python **ChromaDB** for institutional memory and cosine similarity.

4. **Intelligent Routing & Review Queue:**
   - **Multi-Signal Confidence Formula:** Weighs semantic similarity (60%), evidence type reliability (25% - e.g., photos > text), and temporal proximity (15%).
   - **Auto-Apply vs. Human-in-the-loop:** Updates with ≥85% confidence are automatically applied to the database. Updates < 85% are sent to the **Planner Review Queue** for manual approval/remapping.

5. **Web Interface:**
   - A modern, dark-themed Streamlit dashboard with 4 core views: Time Agent, Review Queue, Live Schedule View, and Memory Query.

---

## 🔮 Future Scope (V2 - "Heavy" Production Deployment)

While V1 is optimized for portability and hackathon demonstrations (sub 200MB footprint), the architecture is designed to scale up to enterprise-grade "heavy" deployments. 

In the future, we will implement:

1. **Local GPU-Accelerated Embedding Models:**
   - Re-integrating `sentence-transformers` and `torch` to run `all-MiniLM-L6-v2` locally for zero-latency, offline semantic matching without API limits.
2. **On-Premise LLMs (vLLM / Ollama):**
   - Deploying Llama-3 8B or Mistral locally to handle extraction securely within air-gapped corporate networks (critical for sensitive Oil & Gas data).
3. **Computer Vision for Image Verification:**
   - Using specialized Vision-Language Models (VLMs) to analyze site photos and mathematically verify if the reported percentage matches the visual evidence (e.g., counting welded spools).
4. **Direct Primavera (P6) API Integration:**
   - Replacing the SQLite database with direct bidirectional syncing to Oracle Primavera P6 EPPM via its web services API.

---

## 🛠️ How to Run Locally

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
   Create a `.env` file in the root directory (refer to `.env.example`). You will need an NVIDIA NIM API key to run the extraction engine.

3. **Install dependencies:**
   ```bash
   uv sync --no-dev
   ```

4. **Seed the database:**
   This reads the baseline schedule (`data/baseline_schedule.csv`), embeds the descriptions via API, and initializes SQLite.
   ```bash
   uv run python -m sitesync.db.seed
   ```

5. **Run the Dashboard:**
   ```bash
   uv run streamlit run frontend/app.py
   ```

The application will be available at `http://localhost:8501`.

---
*Built with ❤️ for SIH 2024*
