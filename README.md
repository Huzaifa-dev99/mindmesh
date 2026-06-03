# MindMesh

MindMesh is a local RAG workspace for uploading documents, indexing them, and chatting with them through a FastAPI backend and React frontend.

It uses:

- FastAPI for the API
- React + Vite for the UI
- Postgres for users, documents, chat history, prompts, and AI settings
- MinIO/S3 for uploaded files
- Qdrant for vectors
- Hugging Face embeddings
- Groq, OpenAI, Gemini, or vLLM for answer generation
- Optional Tavily web search

## Quick Start

MindMesh includes a Compose file, so the full local stack can run with one command.

### 1. Clone the repo

```powershell
git clone https://github.com/Huzaifa-dev99/mindmesh.git
cd mindmesh
```

### 2. Create your `.env`

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Add at least one LLM key. Groq is the simplest first option:

```env
GROQ_API_KEY=your-groq-api-key
```

You can also add provider keys later from the React admin UI.

### 3. Start everything

```powershell
docker compose up --build
```

Open:

```text
App:       http://127.0.0.1:5173
API docs:  http://127.0.0.1:8000/docs
Health:    http://127.0.0.1:8000/api/v1/health
MinIO UI:  http://127.0.0.1:9001
Qdrant:    http://127.0.0.1:6333
```

Stop the stack:

```powershell
docker compose down
```

Remove all local Compose data:

```powershell
docker compose down -v
```

## First Use

1. Open `http://127.0.0.1:5173`.
2. Upload documents from the document library.
3. Index the uploaded documents.
4. Ask questions in chat.

Supported document types:

```text
.pdf, .docx, .ppt, .pptx, .txt, .md
```

The first indexing run may download the embedding model. With Compose, it is cached in the `embedding_cache` Docker volume.

## Compose Services

`compose.yml` starts:

- `postgres`
- `qdrant`
- `minio`
- `minio-init`
- `api`
- `frontend`

Useful checks:

```powershell
docker compose ps
docker compose logs api
docker compose logs frontend
docker compose config
```

## Local Development Without App Containers

You can run only the support services in Docker:

```powershell
docker compose up -d postgres qdrant minio minio-init
```

Then run the app from your machine:

```powershell
python run.py --fe
```

The runner creates `.venv`, installs Python dependencies, starts FastAPI, installs frontend packages when needed, and starts Vite.

Other runner commands:

```powershell
python run.py        # API only
python run.py --ui   # API + legacy Streamlit UI
```

## Important Files

```text
compose.yml             Full local stack
Dockerfile.api          Backend image
frontend/Dockerfile     Frontend image
app/                    FastAPI backend
frontend/               React frontend
legacy/                 Legacy Streamlit UI
scripts/                CLI helpers
tests/                  Python tests
.env.example            Environment template
```

## Configuration Notes

For Compose, most infrastructure values are already wired to container service names. Usually you only need to set:

```env
GROQ_API_KEY=
TAVILY_API_KEY=
ADMIN_SECRET_KEY=
```

`TAVILY_API_KEY` is optional and only needed for web search.

`ADMIN_SECRET_KEY` is optional, but recommended before saving provider keys in the admin UI. Generate one with:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Troubleshooting

- **No LLM response:** set `GROQ_API_KEY` or add a provider key in the admin UI.
- **Web search fails:** set `TAVILY_API_KEY` or turn web search off in chat.
- **Port conflict:** change `APP_PORT` or `FRONTEND_PORT` in `.env`.
- **Fresh indexing is slow:** the embedding model is downloading for the first time.
- **Need a clean reset:** run `docker compose down -v`, then `docker compose up --build`.

## Security

MindMesh is intended as a local development workspace. Do not expose it publicly without adding real authentication, HTTPS, secret management, and production hardening.
