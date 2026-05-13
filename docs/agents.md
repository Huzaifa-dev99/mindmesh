# MindMesh Agent Architecture

MindMesh exposes one user-facing chat endpoint: `POST /v1/chat`. Every message enters the `SupervisorAgent`, which classifies intent, delegates when needed, and returns the final answer plus route metadata and citations.

## Agents

- `SupervisorAgent`: routes user queries, handles greetings/app-help directly, and remains the only user-facing entry point.
- `NotesAgent`: answers only from retrieved notes/journal context in the `notes` Qdrant collection. If retrieval is weak, it says no relevant notes were found.
- `DocumentsAgent`: answers only from retrieved document chunks in the `documents` Qdrant collection. Citations include file names and `minio_object_path`.
- `WebSearchAgent`: calls Tavily only when the query needs current or external information. It is enabled by `Settings -> Tools -> Tavily API Key` or backend `TAVILY_API_KEY`.

## Routing

- Notes: “my notes”, “saved notes”, “ideas I wrote”, personal knowledge.
- Documents: uploaded files, PDFs, documents, reports, attachments.
- Web: latest/current/news/online/external/recent facts.
- Direct: greetings, app help, or clarification.

## Qdrant Collections

`notes`

- `source_type`: `note` or `journal`
- `source_id`: note/journal UUID
- `title`, `text`, `user_id`, `tags`, metadata

`documents`

- `source_type`: `document`
- `document_id`, `source_id`
- `file_name`, `file_type`
- `chunk_id`, `chunk_index`
- `uploaded_date`, `user_id`
- `minio_object_path`
- `text`

Every query includes a `user_id` filter, so one user cannot retrieve another user’s vectors.

## MinIO

Docker Compose runs MinIO with the official image and binds the data path to:

```text
D:\volumes\minio
```

The backend writes uploaded text-readable documents into the shared MinIO data volume and stores chunks plus metadata in Qdrant. The original file path is preserved in every document chunk as `minio_object_path`.

## Prompts

Notes Agent:

```text
Answer only from retrieved notes context. If the context is insufficient, say no relevant notes were found.
```

Documents Agent:

```text
Answer only from retrieved document chunks. If context is insufficient, say no relevant documents were found. Cite file names and MinIO object paths.
```

Web Search Agent:

```text
Answer using Tavily web results with references.
```

## Error Handling

- Missing Tavily key returns guidance instead of attempting web search.
- Notes/documents with low retrieval confidence return no-answer messages.
- Document uploads currently support text-readable files; binary extraction can be added later.

