# MindMesh Mermaid Diagrams

These diagrams use Mermaid icon nodes with Iconify identifiers such as `logos:react`, `logos:fastapi-icon`, and `logos:postgresql`. Renderers need Mermaid icon support enabled. If a renderer does not support icon nodes, the labels still describe the technology role.

## Technology Architecture

```mermaid
flowchart TB
    User@{ icon: "material-symbols:person", label: "Single local user", pos: "t", h: 56 }
    Browser@{ icon: "logos:chrome", label: "Browser", pos: "t", h: 56 }

    subgraph FE["Frontend container"]
        React@{ icon: "logos:react", label: "React", pos: "t", h: 56 }
        Vite@{ icon: "logos:vitejs", label: "Vite", pos: "t", h: 56 }
        Tailwind@{ icon: "logos:tailwindcss-icon", label: "Tailwind CSS", pos: "t", h: 56 }
        Lucide@{ icon: "lucide:icons", label: "Lucide icons", pos: "t", h: 56 }
    end

    subgraph BE["Backend container"]
        FastAPI@{ icon: "logos:fastapi-icon", label: "FastAPI", pos: "t", h: 56 }
        Python@{ icon: "logos:python", label: "Python", pos: "t", h: 56 }
        SQLAlchemy@{ icon: "devicon:sqlalchemy", label: "SQLAlchemy", pos: "t", h: 56 }
        Alembic@{ icon: "simple-icons:alembic", label: "Alembic", pos: "t", h: 56 }
        LangChain@{ icon: "simple-icons:langchain", label: "LangChain-ready agents", pos: "t", h: 56 }
    end

    subgraph Stores["Local storage services"]
        Postgres@{ icon: "logos:postgresql", label: "PostgreSQL", pos: "t", h: 56 }
        Qdrant@{ icon: "simple-icons:qdrant", label: "Qdrant", pos: "t", h: 56 }
        MinIO@{ icon: "simple-icons:minio", label: "MinIO", pos: "t", h: 56 }
    end

    subgraph AI["AI and tools"]
        Groq@{ icon: "simple-icons:groq", label: "Groq API", pos: "t", h: 56 }
        Tavily@{ icon: "simple-icons:tavily", label: "Tavily Search", pos: "t", h: 56 }
    end

    Docker@{ icon: "logos:docker-icon", label: "Docker Compose", pos: "t", h: 56 }

    User --> Browser --> React
    React --> Vite
    React --> Tailwind
    React --> Lucide
    React -->|REST /v1| FastAPI
    FastAPI --> Python
    FastAPI --> SQLAlchemy --> Postgres
    FastAPI --> Alembic --> Postgres
    FastAPI -->|vectors and retrieval| Qdrant
    FastAPI -->|document originals| MinIO
    FastAPI -->|chat completions| Groq
    FastAPI -->|optional web search| Tavily
    Docker --> FE
    Docker --> BE
    Docker --> Stores
```

## Agentic Routing Flow

```mermaid
flowchart TD
    User@{ icon: "material-symbols:person", label: "User query", pos: "t", h: 54 }
    ChatUI@{ icon: "logos:react", label: "Chat UI", pos: "t", h: 54 }
    API@{ icon: "logos:fastapi-icon", label: "POST /v1/chat", pos: "t", h: 54 }
    Supervisor@{ icon: "material-symbols:account-tree", label: "Supervisor Agent", pos: "t", h: 54 }
    Intent{Intent}
    NotesAgent@{ icon: "material-symbols:note-stack", label: "Notes Agent", pos: "t", h: 54 }
    DocsAgent@{ icon: "material-symbols:docs", label: "Documents Agent", pos: "t", h: 54 }
    WebAgent@{ icon: "material-symbols:travel-explore", label: "Web Search Agent", pos: "t", h: 54 }
    Direct@{ icon: "material-symbols:chat", label: "Direct answer", pos: "t", h: 54 }
    QNotes@{ icon: "simple-icons:qdrant", label: "Qdrant notes", pos: "t", h: 54 }
    QDocs@{ icon: "simple-icons:qdrant", label: "Qdrant documents", pos: "t", h: 54 }
    Tavily@{ icon: "simple-icons:tavily", label: "Tavily", pos: "t", h: 54 }
    Groq@{ icon: "simple-icons:groq", label: "Groq", pos: "t", h: 54 }
    Answer@{ icon: "material-symbols:format-quote", label: "Answer + top 5 references", pos: "t", h: 54 }
    Pills@{ icon: "material-symbols:label", label: "Citation pills", pos: "t", h: 54 }
    Preview@{ icon: "material-symbols:preview", label: "Right-pane preview", pos: "t", h: 54 }

    User --> ChatUI --> API --> Supervisor --> Intent
    Intent -->|notes, saved ideas, personal knowledge| NotesAgent
    Intent -->|documents, PDFs, files, attachments| DocsAgent
    Intent -->|current, online, external facts| WebAgent
    Intent -->|greeting, help, clarification| Direct
    NotesAgent -->|user_id-filtered top 5| QNotes --> Groq
    DocsAgent -->|user_id-filtered top 5| QDocs --> Groq
    WebAgent -->|requires Tavily key| Tavily --> Groq
    Direct --> Groq
    Groq --> Answer --> Pills --> Preview
```

## Notes Data Flow

```mermaid
flowchart LR
    Editor@{ icon: "logos:react", label: "Right-pane note editor", pos: "t", h: 54 }
    API@{ icon: "logos:fastapi-icon", label: "Knowledge API", pos: "t", h: 54 }
    Postgres@{ icon: "logos:postgresql", label: "PostgreSQL notes/tags", pos: "t", h: 54 }
    Chunker@{ icon: "material-symbols:segment", label: "Text chunking", pos: "t", h: 54 }
    Embed@{ icon: "material-symbols:network-intelligence", label: "Embedding provider", pos: "t", h: 54 }
    QNotes@{ icon: "simple-icons:qdrant", label: "Qdrant notes collection", pos: "t", h: 54 }
    Chat@{ icon: "material-symbols:chat", label: "Notes RAG query", pos: "t", h: 54 }
    Citations@{ icon: "material-symbols:label", label: "Reference pills", pos: "t", h: 54 }

    Editor -->|title, content, tags| API
    API -->|canonical note row| Postgres
    API --> Chunker --> Embed -->|vectors + note metadata + user_id| QNotes
    Chat -->|semantic search| QNotes -->|top 5 note chunks| Citations
```

## Document Data Flow

```mermaid
flowchart LR
    Upload@{ icon: "logos:react", label: "Library import", pos: "t", h: 54 }
    API@{ icon: "logos:fastapi-icon", label: "Knowledge API", pos: "t", h: 54 }
    MinIO@{ icon: "simple-icons:minio", label: "MinIO originals", pos: "t", h: 54 }
    Chunker@{ icon: "material-symbols:segment", label: "Document chunking", pos: "t", h: 54 }
    Embed@{ icon: "material-symbols:network-intelligence", label: "Embedding provider", pos: "t", h: 54 }
    QDocs@{ icon: "simple-icons:qdrant", label: "Qdrant documents collection", pos: "t", h: 54 }
    DocsAgent@{ icon: "material-symbols:docs", label: "Documents Agent", pos: "t", h: 54 }
    Preview@{ icon: "material-symbols:preview", label: "Preview with MinIO path", pos: "t", h: 54 }

    Upload -->|file content| API
    API -->|original object, D:/volumes/minio| MinIO
    API --> Chunker --> Embed -->|vectors + chunk metadata + MinIO path + user_id| QDocs
    DocsAgent -->|semantic retrieval top 5| QDocs --> Preview
    Preview -->|source location| MinIO
```

## Chat Reference Opening Flow

```mermaid
flowchart TD
    Pill@{ icon: "material-symbols:label", label: "Reference pill", pos: "t", h: 54 }
    Source{source_type}
    Note@{ icon: "material-symbols:note-stack", label: "Note preview", pos: "t", h: 54 }
    Document@{ icon: "material-symbols:docs", label: "Document preview", pos: "t", h: 54 }
    Web@{ icon: "material-symbols:open-in-new", label: "External web URL", pos: "t", h: 54 }
    Pane@{ icon: "material-symbols:right-panel-open", label: "Right pane", pos: "t", h: 54 }
    Browser@{ icon: "logos:chrome", label: "New browser tab", pos: "t", h: 54 }

    Pill --> Source
    Source -->|note| Note --> Pane
    Source -->|document| Document --> Pane
    Source -->|web| Web --> Browser
```

