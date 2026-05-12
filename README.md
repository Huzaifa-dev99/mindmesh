# MindMesh

MindMesh is a self-hosted AI journaling and knowledge management platform. It combines journals, notes, tags, semantic search, and RAG chat over a private personal memory store.

## What Is Included

- FastAPI backend with versioned routes, OpenAPI docs, CORS, request logging, exception handling, and health checks
- PostgreSQL data model with UUID primary keys, timestamps, soft deletion, tags, conversations, messages, and embedding metadata
- Alembic migration setup with an initial schema
- Qdrant vector store integration with collection initialization, upsert, search, and source deletion
- Local open-source embeddings through FastEmbed, with a provider abstraction for future model swaps
- Groq chat integration for chat, summaries, and RAG answer generation
- React + Tailwind frontend with Dashboard, Journal, Notes, AI Chat, Search, and Settings views
- JWT authentication foundation with password hashing and protected routes
- Docker Compose stack for backend, frontend, Postgres, and Qdrant
- Pytest foundation with API and service-adjacent examples

## Architecture

The backend keeps the existing layered structure:

- `app/api`: FastAPI routing and dependencies
- `app/schemas`: Pydantic request and response DTOs
- `app/models`: SQLAlchemy ORM entities
- `app/repositories`: database access
- `app/services`: business workflows, ingestion, search, chat
- `app/ai`: provider abstractions, prompts, embeddings, chunking
- `app/db`: database and Qdrant clients
- `alembic`: migrations

The frontend is a lightweight Vite React application:

- `src/App.tsx`: authenticated app routing
- `src/components`: app shell, auth, and shared UI blocks
- `src/pages`: dashboard, journal, notes, chat, search, and settings views
- `src/lib/api.ts`: typed backend API wrapper
- `src/hooks`: session and data orchestration

## Quick Start

1. Copy environment defaults:

   ```bash
   cp .env.example .env
   ```

2. Add `GROQ_API_KEY` in `.env` if you want AI responses. Without it, storage and search still work.

3. Start the full local stack:

   ```bash
   docker compose up --build
   ```

4. Open:

   - Frontend: http://localhost:8501
   - Backend: http://localhost:8000
   - API docs: http://localhost:8000/docs
   - Qdrant dashboard/API: http://localhost:6335
   - PostgreSQL host port: `5433` by default, mapped to container port `5432`

The backend runs `alembic upgrade head` before starting.

## Environment

Important variables:

- `DATABASE_URL`: PostgreSQL connection string
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: database container setup
- `QDRANT_URL`: Qdrant endpoint
- `QDRANT_COLLECTION`: vector collection name
- `EMBEDDING_MODEL`: FastEmbed model name
- `EMBEDDING_DIMENSION`: vector size, default `384`
- `GROQ_API_KEY`: Groq API key
- `SECRET_KEY`: JWT signing secret
- `CORS_ORIGINS`: comma-separated frontend origins
- `WORKSPACE_PIN`: local single-user frontend passcode, default `0000`
- `SINGLE_USER_EMAIL`, `SINGLE_USER_PASSWORD`: internal local backend account used after unlock

## Development

Backend:

```bash
cd backend
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 8501
```

Tests:

```bash
cd backend
pytest
```

## Current Roadmap

- Add refresh tokens and user password reset flow
- Add richer timeline filters and bulk re-indexing endpoints
- Add streaming chat responses
- Add export/import for journals and notes
- Add optional local LLM provider behind the existing AI abstraction
