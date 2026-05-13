# MindMesh Architecture

This document describes the implementation architecture for the MindMesh app, including frontend, backend, authentication, content storage, vector retrieval, agents, and source-opening flows.

For icon-based Mermaid diagrams covering architecture, agentic routing, notes ingestion, document ingestion, and reference-opening flows, see [diagrams.md](./diagrams.md).

## System Overview

```mermaid
flowchart TB
    User[Single Local User]

    subgraph Frontend[React Frontend]
        Lock[Privacy Lockscreen]
        Shell[App Shell and Sidebar]
        Chat[Chat Interface]
        RefPills[Reference Pills]
        Library[Content Library]
        RightPane[Right Pane Preview and Editor]
        Settings[Settings and Tools]
    end

    subgraph Backend[FastAPI Backend]
        Auth[JWT Auth Foundation]
        ChatAPI[POST /v1/chat]
        Supervisor[Supervisor Agent]
        NotesAgent[Notes Agent]
        DocsAgent[Documents Agent]
        WebAgent[Web Search Agent]
        KnowledgeAPI[Knowledge API]
        ConversationAPI[Conversation API]
        SearchAPI[Search API]
    end

    subgraph Data[Storage Layer]
        Postgres[(PostgreSQL)]
        QNotes[(Qdrant: notes)]
        QDocs[(Qdrant: documents)]
        MinIO[(MinIO Object Storage)]
    end

    subgraph External[Optional External Services]
        Groq[Groq Chat API]
        Tavily[Tavily Search API]
    end

    User --> Lock
    Lock --> Shell
    Shell --> Chat
    Shell --> Library
    Shell --> RightPane
    Shell --> Settings

    Chat --> ChatAPI
    ChatAPI --> Auth
    ChatAPI --> ConversationAPI
    ChatAPI --> Supervisor

    Supervisor --> NotesAgent
    Supervisor --> DocsAgent
    Supervisor --> WebAgent
    Supervisor --> Groq

    NotesAgent --> QNotes
    NotesAgent --> Groq
    DocsAgent --> QDocs
    DocsAgent --> Groq
    WebAgent --> Tavily
    WebAgent --> Groq

    KnowledgeAPI --> Postgres
    KnowledgeAPI --> QNotes
    KnowledgeAPI --> QDocs
    KnowledgeAPI --> MinIO
    ConversationAPI --> Postgres
    SearchAPI --> QNotes
    SearchAPI --> QDocs

    ChatAPI --> RefPills
    RefPills --> RightPane
    Library --> RightPane
```

## Chat Retrieval and Reference Flow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Chat UI
    participant API as /v1/chat
    participant S as Supervisor Agent
    participant N as Notes Agent
    participant D as Documents Agent
    participant W as Web Search Agent
    participant QN as Qdrant notes
    participant QD as Qdrant documents
    participant T as Tavily
    participant G as Groq
    participant RP as Right Pane

    U->>UI: Ask question
    UI->>API: Send message, conversation_id, optional Tavily key
    API->>S: Route query

    alt Notes intent
        S->>N: Delegate
        N->>QN: Retrieve top 5 notes
        N->>G: Generate RAG-only answer
        N-->>S: Answer plus citations
    else Documents intent
        S->>D: Delegate
        D->>QD: Retrieve top 5 document chunks
        D->>G: Generate RAG-only answer
        D-->>S: Answer plus file citations
    else Web intent
        S->>W: Delegate
        W->>T: Search web if API key exists
        W->>G: Synthesize referenced answer
        W-->>S: Answer plus web citations
    else Direct response
        S->>G: Optional direct response
        G-->>S: Assistant message
    end

    S-->>API: Final answer, route metadata, citations
    API-->>UI: Assistant message and references
    UI->>UI: Render up to 5 citation pills
    U->>UI: Click reference pill
    UI->>RP: Open note/document preview or external web URL
```

## Content Ingestion Flow

```mermaid
flowchart LR
    User[User]
    Library[Content Library]
    KnowledgeAPI[Knowledge API]
    Chunker[Chunking]
    Embedder[Embedding Provider]
    QNotes[(Qdrant notes)]
    QDocs[(Qdrant documents)]
    MinIO[(MinIO D:\\volumes\\minio)]
    Postgres[(PostgreSQL)]

    User --> Library
    Library --> KnowledgeAPI

    KnowledgeAPI -->|Create note| Postgres
    KnowledgeAPI -->|Note text| Chunker
    Chunker --> Embedder
    Embedder -->|note vectors| QNotes

    KnowledgeAPI -->|Upload document original| MinIO
    KnowledgeAPI -->|Document text| Chunker
    Chunker --> Embedder
    Embedder -->|document chunk vectors| QDocs
```

## Source Opening Flow

```mermaid
flowchart TD
    Citation[Reference Pill Click]
    SourceType{source_type}
    Note[Open Note Preview]
    Doc[Open Document Preview]
    Web[Open External URL]
    RightPane[Right Pane]
    Browser[Browser Tab]

    Citation --> SourceType
    SourceType -->|note or journal| Note
    SourceType -->|document| Doc
    SourceType -->|web| Web
    Note --> RightPane
    Doc --> RightPane
    Web --> Browser
```

## Main Components

### Frontend

- `AppShell`: navigation, sidebar, right pane host, profile/lock/settings entry points.
- `ProductivityWorkspace`: user-facing chat surface and reference rendering.
- `KnowledgeDashboard`: Library list, import actions, documents, notes, media, activity.
- `SettingsDialog`: provider settings, Tools/Tavily API key, prompts, security.
- `PrivacyLockscreen`: local PIN lock/unlock flow.

### Backend

- `ChatService`: persists messages and invokes `SupervisorAgent`.
- `SupervisorAgent`: routes queries and returns final response metadata.
- `NotesAgent`: retrieves from `notes` collection and answers only from context.
- `DocumentsAgent`: retrieves from `documents` collection and answers only from context.
- `WebSearchAgent`: uses Tavily only when an API key is available.
- `DocumentService`: stores originals in the MinIO volume path and indexes chunks in Qdrant.

## Data Isolation

- Every PostgreSQL row is owned by `user_id`.
- Every Qdrant payload includes `user_id`.
- Every retrieval filter must include `user_id`.
- MinIO object paths are namespaced by `user_id/document_id/file_name`.

## Deployment Services

```mermaid
flowchart LR
    Compose[Docker Compose]
    FE[frontend container]
    BE[backend container]
    PG[postgres container]
    QD[qdrant container]
    MI[minio container]
    VOL1[(postgres_data)]
    VOL2[(qdrant_data)]
    VOL3[(D:\\volumes\\minio)]

    Compose --> FE
    Compose --> BE
    Compose --> PG
    Compose --> QD
    Compose --> MI
    PG --> VOL1
    QD --> VOL2
    MI --> VOL3
    BE --> VOL3
```
