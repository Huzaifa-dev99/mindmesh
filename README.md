# MM POC RAG API

FastAPI service for indexing PDF, DOCX, PPT/PPTX, and text files from S3-compatible storage into Qdrant and generating RAG answers.

## Layout

```text
app/
  api/v1/          HTTP routes and request/response schemas
  core/            configuration, logging, storage, serialization, external clients
  ml/              embedding model loading and local cache
  services/        indexing, preprocessing, retrieval, generation, registry logic
data/              runtime registry state
legacy/            old experiments kept out of the runtime path
logs/              rotating structured application logs
models/embedding/  locally cached embedding models
scripts/           command-line helpers
tests/             lightweight regression tests for core helpers
```

## Run

```powershell
python run.py
```

That single command creates/uses `.venv`, installs `requirements.txt` when it changes, and starts the FastAPI server.
If port `8000` is unavailable, the runner automatically uses the next open port and prints the actual docs URL.

To run the Streamlit chat frontend and the FastAPI backend together:

```powershell
python run.py --ui
```

To run the React frontend:

```powershell
python run.py --fe
```

The React app runs at `http://127.0.0.1:5173`. The runner installs frontend packages when needed, starts FastAPI, and points the Vite `/api` proxy at the actual backend port.

For production-like API serving without the Streamlit debug UI:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The Streamlit frontend has two pages:

- `Chat`: chat sessions grouped by date, retrieval settings, and the chat screen
- `Documents`: document upload, document status list, selected indexing, document removal, and Qdrant vector removal

Document uploads collect editable filename and tags per file. The backend stores tags as searchable metadata, assigns version `01` for the first upload of a filename, creates the next version when content changes, and reports duplicates when identical content already exists. PDF, DOCX, PPT, and PPTX files are parsed through Docling; TXT/MD files use lightweight text splitting. Indexed Qdrant metadata includes the source filename, file type, and page number when the parser provides one.

API docs:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

- `GET /api/v1/health`
- `POST /api/v1/index`
- `POST /api/v1/generate`
- `GET /api/v1/documents`
- `POST /api/v1/documents/sync`
- `POST /api/v1/documents/upload`
- `POST /api/v1/documents/index`
- `POST /api/v1/documents/remove-vectors`
- `POST /api/v1/documents/remove`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}/interactions`

## Optional CLI Helpers

```powershell
.\.venv\Scripts\python.exe scripts/index_documents.py
.\.venv\Scripts\python.exe scripts/generate_answer.py
.\.venv\Scripts\python.exe scripts/serve.py
```

## Validation

Run the lightweight regression suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover
```

Run a syntax/import check across the project:

```powershell
$files = @('main.py','run.py') + (Get-ChildItem -Path app,legacy,scripts,tests -Recurse -Filter *.py | ForEach-Object { $_.FullName })
.\.venv\Scripts\python.exe -m py_compile $files
```

## Configuration

Copy `.env.example` to `.env` and set your MinIO, Qdrant, embedding, Groq, and Postgres values. Document registry and chat interactions are stored in Postgres under the `rag` schema.

Groq is optional when you configure a saved OpenAI-compatible, Gemini, or vLLM provider through the admin UI. Logs are written as structured JSON to `logs/app.log` and `logs/errors.log`; rotate size and backup count with `MM_POC_LOG_MAX_BYTES` and `MM_POC_LOG_BACKUP_COUNT`.
