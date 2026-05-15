# MindMesh

MindMesh is a self-hosted personal knowledge workspace. It combines notes, journals, document upload, semantic search, and AI chat over a private memory store.

## Tech Stack

- Frontend: React 18, Vite, TypeScript, Tailwind CSS, lucide-react
- Backend: FastAPI, Pydantic, SQLAlchemy async ORM, Alembic
- Data stores: PostgreSQL for relational data, Qdrant for vectors, local MinIO-compatible storage path for uploaded files
- AI: FastEmbed for local embeddings, Groq for current chat generation, provider/model management for Groq, OpenAI, Gemini, and Claude
- Tooling: Docker Compose, Pytest

## Core Features

- JWT-authenticated users
- Notes and journals with tags
- Semantic search across notes, journals, and global documents
- Chat with RAG routing over notes, documents, or web search
- AI Settings tab for provider API key verification and model discovery
- Per-chat model selection
- Document uploads from Library and right panel
- Document scopes:
  - `global`: available across all chats
  - `chat`: available only to the selected chat
- Document indexing status in the UI: `Uploaded`, `Indexed`, `Failed`

## Architecture

```text
frontend/
  src/
    App.tsx                  Authenticated page composition
    lib/api.ts               Typed API client
    hooks/useMindMesh.ts     Session and data orchestration
    components/              Shell, settings, lock screen, shared UI
    pages/                   Chat and Library views

backend/
  app/
    api/                     FastAPI routers and dependencies
    core/                    Config, security, logging, middleware
    db/                      PostgreSQL session and Qdrant client
    models/                  SQLAlchemy ORM models
    repositories/            Relational persistence helpers
    schemas/                 Pydantic DTOs
    services/                Business workflows
    ai/                      Embeddings, prompts, provider wrappers
  alembic/                   Database migrations
  tests/                     Pytest suite
```

## Data Flow

### Notes and Journals

1. User creates or updates content.
2. PostgreSQL stores the source record and tags.
3. Content is chunked.
4. FastEmbed creates vectors.
5. Qdrant stores vectors and retrieval payloads.

### Documents

1. User uploads a file from the Library Documents tab or right panel.
2. Frontend sends multipart form data to `/v1/knowledge/documents`.
3. Backend stores original bytes under `MINIO_DATA_PATH`.
4. Backend extracts text from supported formats:
   - TXT/MD/CSV/JSON
   - PDF via `pypdf`
   - DOCX via `python-docx`
   - PPTX via `python-pptx`
   - images receive metadata placeholders for multimodal processing
5. Extracted text is chunked and embedded.
6. Qdrant stores chunks with scope metadata.
7. Chat retrieval searches global documents plus current-chat documents only.

### Chat

1. User sends a message with selected provider/model metadata.
2. Backend creates or loads the conversation.
3. `SupervisorAgent` routes the query to notes, documents, web, or direct response.
4. RAG agents retrieve relevant chunks from Qdrant.
5. Groq generates the answer.
6. Assistant message and citation metadata are saved.

## Configuration

Copy `.env.example` to `.env` and change production secrets.

Important variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `GROQ_API_KEY`
- `TAVILY_API_KEY`
- `QDRANT_URL`
- `QDRANT_NOTES_COLLECTION`
- `QDRANT_DOCUMENTS_COLLECTION`
- `MINIO_DATA_PATH`
- `CORS_ORIGINS`

Use a strong, stable `SECRET_KEY`; it signs JWTs and encrypts saved AI API keys.

## Run Locally With Docker

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:8501
- Backend: http://localhost:8000
- API docs: http://localhost:8000/docs
- Qdrant: http://localhost:6335
- MinIO console: http://localhost:9001

The backend runs Alembic migrations before starting.

## Backend Development

```powershell
cd backend
..\.venv\Scripts\Activate.ps1
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

When running the backend on the host against Docker Compose services, use `QDRANT_URL=http://localhost:6335`.
The Docker backend container already uses `QDRANT_URL=http://qdrant:6333`.

## Frontend Development

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 8501
```

## Tests

```bash
cd backend
pytest
```

If tests fail with a FastAPI/Starlette constructor error, reinstall backend dependencies in a clean virtual environment. The project pins Starlette to the FastAPI-compatible range in `backend/pyproject.toml`.

## Production Notes

- Set `DEBUG=false`.
- Use a strong `SECRET_KEY`.
- Restrict `CORS_ORIGINS`.
- Run behind HTTPS.
- Use persistent volumes for PostgreSQL, Qdrant, and document storage.
- Prefer managed secrets for production API keys when available.
- Add background workers before indexing very large documents or high upload volume.

## Known Follow-Ups

- Streaming chat responses.
- Full non-Groq generation adapters.
- OCR for scanned PDFs and image-only documents.
- Background document indexing queue for high-volume deployments.
