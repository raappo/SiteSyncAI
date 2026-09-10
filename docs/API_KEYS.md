# API Keys Reference

This project supports the following APIs (configured in `.env`):

- **NVIDIA NIM** (`NVIDIA_API_KEY`): Primary LLM provider for fast extraction and reasoning.
- **Experiential Labs** (`EXPLABS_API_KEY`): Secondary LLM fallback provider.
- **Azure Document Intelligence** (`AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT`, `AZURE_DOCUMENT_INTELLIGENCE_KEY`): Used for extracting text and structure from complex PDFs and images.
- **Azure OpenAI** (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`): High-quality embeddings (fallback to local `sentence-transformers` / `ngram` if not provided).

## Offline Mode
If no API keys are provided, the system gracefully falls back to mock extractors and local n-gram embedding models to ensure the prototype remains functional for demonstrations.
