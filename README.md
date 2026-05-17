# MindMesh

MindMesh is a self-hosted AI knowledge workspace for private notes, documents, semantic search, and retrieval-augmented chat. It is designed to run locally with Docker and keep user content in your own PostgreSQL, Qdrant, and local object-storage volumes.

## Key Features

- Private local workspace with a PIN lock and single-user bootstrap flow
- Notes, media references, and document library
- Document upload from the Library or context panel
- Global documents available across chats and chat-scoped documents limited to one conversation
- Document indexing for PDF, TXT, DOCX, images, PPT/PPTX, and common text formats
- Semantic retrieval over notes and documents using Qdrant
- Chat responses grounded in chat history, note context, and document context
- AI Settings for provider API key verification, model discovery, and per-chat model selection
- Model capability tags such as Reasoning, Mini, Multimodal, Fast, Coding, Vision, and MoE
- Chat rename, archive, and delete actions
- Clean responsive React interface with light/dark mode, accent themes, and compact/comfortable density

## Tech Stack

- Frontend: React 18, Vite, TypeScript, Tailwind CSS, lucide-react
- Backend: FastAPI, SQLAlchemy async ORM, Pydantic Settings, Alembic
- Storage: PostgreSQL, Qdrant, MinIO-compatible local volume for uploaded files
- AI: Groq chat provider for generation, provider/model discovery for Groq/OpenAI/Gemini/Claude, FastEmbed with deterministic hash fallback for local embeddings
- Tooling: Docker Compose, Pytest

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- Git
- Optional: a Groq API key for live AI responses
- Optional: Tavily API key for web search

## Quick Start: Local-First Dependencies

```bash
git clone https://github.com/Huzaifa-dev99/mindmesh.git
cd mindmesh
cp .env.example .env
.\scripts\start-local.ps1
```

The local-first script checks the endpoints in `.env` first:

- PostgreSQL from `DATABASE_URL`, or `POSTGRES_HOST`/`POSTGRES_PORT`
- Qdrant from `QDRANT_URL`
- MinIO from `MINIO_ENDPOINT` and `MINIO_SECURE`

If all three are already running, it starts the backend and frontend against those services without creating new dependency containers. If one is missing, it starts only the missing dependency service with Docker Compose, then points the app at the working local endpoint.

Open:

- Frontend: http://localhost:8501
- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Qdrant: http://localhost:6335
- MinIO console: http://localhost:9001

On first launch, MindMesh asks you to create a workspace PIN. The frontend then creates or logs into the local bootstrap user configured by `SINGLE_USER_EMAIL` and `SINGLE_USER_PASSWORD`.

If you want to check dependency detection without starting anything:

```powershell
.\scripts\start-local.ps1 -CheckOnly
```

To prepare only Postgres/Qdrant/MinIO and run the app yourself:

```powershell
.\scripts\start-local.ps1 -DepsOnly
```

## Full Docker Compose Start

Use this when you want Compose to own the entire stack from scratch:

```bash
docker compose up --build
```

## Required Environment Variables

Copy `.env.example` to `.env` and update at least these values before a shared or production-like deployment:

- `SECRET_KEY`: long random value used for JWT signing and saved API-key encryption
- `POSTGRES_PASSWORD`: database password
- `MINIO_SECRET_KEY`: local document storage password
- `SINGLE_USER_PASSWORD`: bootstrap user password
- `GROQ_API_KEY`: optional at startup; can also be saved from Settings > AI

Common operational settings:

- `CORS_ORIGINS`: comma-separated allowed frontend origins
- `DEBUG`: set to `false` outside local development
- `TAVILY_API_KEY`: optional web search integration
- `DATABASE_URL`: host-reachable PostgreSQL URL when connecting to an existing local container
- `QDRANT_URL`: host-reachable Qdrant URL when connecting to an existing local container
- `MINIO_ENDPOINT`: host-reachable MinIO endpoint such as `localhost:9000`
- `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`: MinIO credentials. Existing `.env` files using `MINIO_USER` and `MINIO_PASSWORD` are also supported.
- `QDRANT_NOTES_COLLECTION` and `QDRANT_DOCUMENTS_COLLECTION`: vector collection names
- `WORKSPACE_PIN`: optional preconfigured workspace PIN; otherwise the first user creates one locally

## Common Commands

```bash
# Prefer already-running Postgres/Qdrant/MinIO, starting missing dependencies only
.\scripts\start-local.ps1

# Check dependency detection only
.\scripts\start-local.ps1 -CheckOnly

# Prepare dependencies only
.\scripts\start-local.ps1 -DepsOnly

# Start or rebuild the full Compose-owned stack
docker compose up --build

# Start in the background
docker compose up -d --build

# View service logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down

# Stop and remove persistent volumes
docker compose down -v
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 8501
```

When running services directly on the host, set `DATABASE_URL` and `QDRANT_URL` to host ports, for example `QDRANT_URL=http://localhost:6335`.

## Tests

```bash
cd backend
pytest
```

The frontend currently uses TypeScript build validation:

```bash
cd frontend
npm run build
```

## Project Structure

```text
.
├── backend/
│   ├── app/
│   │   ├── ai/                 # embeddings, prompts, chat providers
│   │   ├── api/                # FastAPI routers and dependencies
│   │   ├── core/               # config, security, logging, middleware
│   │   ├── db/                 # PostgreSQL and Qdrant clients
│   │   ├── models/             # SQLAlchemy models
│   │   ├── repositories/       # persistence helpers
│   │   ├── schemas/            # Pydantic DTOs
│   │   └── services/           # business workflows and RAG agents
│   ├── alembic/                # database migrations
│   └── tests/                  # backend tests
├── frontend/
│   ├── src/
│   │   ├── components/         # app shell, settings, shared UI
│   │   ├── hooks/              # app data orchestration
│   │   ├── lib/                # typed API client
│   │   └── pages/              # chat and library screens
│   └── public/
├── docker-compose.yml
└── .env.example
```

## How Retrieval Works

1. Notes and documents are chunked and embedded.
2. Qdrant stores vectors with user, source, scope, chat, and citation metadata.
3. Each chat request includes a compact summary of recent chat history.
4. The notes agent retrieves note context using the user query plus chat-history summary.
5. The documents agent retrieves global documents and documents scoped to the current chat.
6. The supervisor combines retrieved context and citations before generating the response.

## Production Notes

- Run behind HTTPS and a real reverse proxy for public deployments.
- Restrict `CORS_ORIGINS` to trusted domains.
- Keep Docker volumes backed up: PostgreSQL, Qdrant, and MinIO data contain the user knowledge base.
- The current generation path uses the Groq-compatible chat provider. Model discovery supports additional providers, but adding generation adapters for non-Groq providers is a future extension.
- For very large documents or high upload volume, move indexing to a background worker queue.

## Contributing

Keep changes small, typed, and covered by backend tests when behavior changes. Avoid committing generated files, local secrets, virtual environments, Docker volumes, or build outputs.
