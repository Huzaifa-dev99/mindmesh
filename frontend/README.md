# MindMesh Frontend

React + Vite + TypeScript frontend for MindMesh.

## Development

```bash
npm install
npm run dev -- --host 0.0.0.0 --port 8501
```

When `VITE_API_BASE_URL` is empty, API calls use the same origin (`/v1/...`).
The Docker/Vite dev server proxies those requests to the backend through
`VITE_API_PROXY_TARGET`.

For most users, run the full stack from the repository root:

```bash
docker compose up --build
```
