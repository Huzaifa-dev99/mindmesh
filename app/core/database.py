from threading import Lock

import psycopg
from psycopg import Connection
from psycopg import OperationalError
from psycopg.rows import dict_row

from app.core.config import (
    DATABASE_URL,
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_CONNECT_TIMEOUT,
    POSTGRES_SSLMODE,
    POSTGRES_USER,
)
from app.core.logging import get_logger, log_timing, trace

logger = get_logger(__name__)

SCHEMA_VERSION = 3
SCHEMA_DESCRIPTION = "Add workspace profile personalization and chat session organization"
_schema_init_lock = Lock()
_schema_initialized = False

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.schema_migrations (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag.users (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    name TEXT NOT NULL DEFAULT 'Local user',
    avatar_url TEXT NOT NULL DEFAULT 'https://api.dicebear.com/9.x/shapes/svg?seed=mindmesh&backgroundColor=16091f',
    bio TEXT NOT NULL DEFAULT '',
    nicknames JSONB NOT NULL DEFAULT '[]'::jsonb,
    highlight_color TEXT NOT NULL DEFAULT 'mist',
    pin_hash TEXT,
    pin_salt TEXT,
    pin_iterations INTEGER NOT NULL DEFAULT 210000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_singleton_check CHECK (id),
    CONSTRAINT users_pin_pair_check CHECK (
        (pin_hash IS NULL AND pin_salt IS NULL)
        OR (pin_hash IS NOT NULL AND pin_salt IS NOT NULL)
    )
);

ALTER TABLE rag.users
    ADD COLUMN IF NOT EXISTS bio TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS nicknames JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS highlight_color TEXT NOT NULL DEFAULT 'mist';

CREATE TABLE IF NOT EXISTS rag.documents (
    id TEXT PRIMARY KEY,
    bucket TEXT NOT NULL,
    object_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    logical_filename TEXT,
    document_version TEXT,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    lexical_hash TEXT,
    status TEXT NOT NULL DEFAULT 'not_indexed',
    etag TEXT,
    size_bytes BIGINT,
    last_modified TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    indexed_at TIMESTAMPTZ,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    point_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT documents_status_check CHECK (
        status IN ('indexed', 'not_indexed', 'failed')
    ),
    CONSTRAINT documents_bucket_key_unique UNIQUE (bucket, object_key)
);

CREATE INDEX IF NOT EXISTS documents_status_idx
    ON rag.documents (status);

CREATE INDEX IF NOT EXISTS documents_bucket_key_idx
    ON rag.documents (bucket, object_key);

ALTER TABLE rag.documents
    ADD COLUMN IF NOT EXISTS logical_filename TEXT,
    ADD COLUMN IF NOT EXISTS document_version TEXT,
    ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS lexical_hash TEXT;

CREATE INDEX IF NOT EXISTS documents_logical_filename_idx
    ON rag.documents (bucket, logical_filename);

CREATE INDEX IF NOT EXISTS documents_lexical_hash_idx
    ON rag.documents (bucket, logical_filename, lexical_hash);

CREATE INDEX IF NOT EXISTS documents_bucket_lexical_hash_idx
    ON rag.documents (bucket, lexical_hash);

CREATE TABLE IF NOT EXISTS rag.chat_sessions (
    id UUID PRIMARY KEY,
    title TEXT,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE rag.chat_sessions
    ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS rag.chat_interactions (
    id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES rag.chat_sessions(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    contextualized_query TEXT,
    answer TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    score_threshold DOUBLE PRECISION NOT NULL DEFAULT 0,
    context_count INTEGER NOT NULL DEFAULT 0,
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    route TEXT,
    route_reasoning TEXT,
    model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE rag.chat_interactions
    ADD COLUMN IF NOT EXISTS contextualized_query TEXT,
    ADD COLUMN IF NOT EXISTS route TEXT,
    ADD COLUMN IF NOT EXISTS route_reasoning TEXT;

CREATE INDEX IF NOT EXISTS chat_interactions_session_created_idx
    ON rag.chat_interactions (session_id, created_at DESC);

CREATE TABLE IF NOT EXISTS rag.chat_retrieved_chunks (
    id UUID PRIMARY KEY,
    interaction_id UUID NOT NULL
        REFERENCES rag.chat_interactions(id) ON DELETE CASCADE,
    session_id UUID NOT NULL
        REFERENCES rag.chat_sessions(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL,
    document_id TEXT REFERENCES rag.documents(id) ON DELETE SET NULL,
    vector_id TEXT,
    collection_name TEXT,
    source TEXT NOT NULL,
    score DOUBLE PRECISION,
    content_preview TEXT NOT NULL DEFAULT '',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chat_retrieved_chunks_rank_check CHECK (rank > 0),
    CONSTRAINT chat_retrieved_chunks_interaction_rank_unique
        UNIQUE (interaction_id, rank)
);

CREATE INDEX IF NOT EXISTS chat_retrieved_chunks_interaction_idx
    ON rag.chat_retrieved_chunks (interaction_id, rank);

CREATE INDEX IF NOT EXISTS chat_retrieved_chunks_session_idx
    ON rag.chat_retrieved_chunks (session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS chat_retrieved_chunks_document_idx
    ON rag.chat_retrieved_chunks (document_id);

CREATE INDEX IF NOT EXISTS chat_retrieved_chunks_vector_idx
    ON rag.chat_retrieved_chunks (vector_id);

CREATE TABLE IF NOT EXISTS rag.ai_provider_keys (
    id UUID PRIMARY KEY,
    provider TEXT NOT NULL,
    label TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_key_fingerprint TEXT NOT NULL,
    base_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_provider_keys_provider_check CHECK (
        provider IN ('openai', 'gemini', 'groq', 'vllm')
    )
);

CREATE INDEX IF NOT EXISTS ai_provider_keys_provider_idx
    ON rag.ai_provider_keys (provider, is_active);

CREATE TABLE IF NOT EXISTS rag.ai_settings (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    active_provider TEXT NOT NULL DEFAULT 'groq',
    active_key_id UUID REFERENCES rag.ai_provider_keys(id) ON DELETE SET NULL,
    active_model TEXT,
    temperature DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_tokens INTEGER,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ai_settings_singleton_check CHECK (id),
    CONSTRAINT ai_settings_provider_check CHECK (
        active_provider IN ('openai', 'gemini', 'groq', 'vllm')
    )
);

CREATE TABLE IF NOT EXISTS rag.prompts (
    name TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    active_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag.prompt_versions (
    id UUID PRIMARY KEY,
    prompt_name TEXT NOT NULL REFERENCES rag.prompts(name) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    change_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT prompt_versions_version_check CHECK (version > 0),
    CONSTRAINT prompt_versions_prompt_version_unique UNIQUE (prompt_name, version)
);

CREATE INDEX IF NOT EXISTS prompt_versions_prompt_idx
    ON rag.prompt_versions (prompt_name, version DESC);
"""


def connect() -> Connection:
    try:
        logger.debug(
            "postgres connection opening",
            extra={
                "event": {
                    "uses_database_url": bool(DATABASE_URL),
                    "host": "DATABASE_URL" if DATABASE_URL else POSTGRES_HOST,
                    "port": None if DATABASE_URL else POSTGRES_PORT,
                    "database": None if DATABASE_URL else POSTGRES_DB,
                    "user": None if DATABASE_URL else POSTGRES_USER,
                }
            },
        )
        if DATABASE_URL:
            return psycopg.connect(
                DATABASE_URL,
                connect_timeout=POSTGRES_CONNECT_TIMEOUT,
                row_factory=dict_row,
            )

        kwargs = {
            "host": POSTGRES_HOST,
            "port": POSTGRES_PORT,
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "connect_timeout": POSTGRES_CONNECT_TIMEOUT,
            "row_factory": dict_row,
        }

        if POSTGRES_PASSWORD:
            kwargs["password"] = POSTGRES_PASSWORD
        if POSTGRES_SSLMODE:
            kwargs["sslmode"] = POSTGRES_SSLMODE

        return psycopg.connect(**kwargs)
    except OperationalError as exc:
        logger.exception("postgres connection failed")
        trace("Postgres connection failed", logger)
        raise RuntimeError(
            "Could not connect to Postgres. Check DATABASE_URL or POSTGRES_* "
            "settings in .env, especially POSTGRES_PASSWORD."
        ) from exc


def _current_schema_version(conn: Connection) -> int:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT to_regclass('rag.schema_migrations') AS migration_table"
        )
        if not cursor.fetchone()["migration_table"]:
            return 0

        cursor.execute(
            "SELECT COALESCE(MAX(version), 0) AS version FROM rag.schema_migrations"
        )
        return int(cursor.fetchone()["version"] or 0)


def _apply_schema(conn: Connection, *, force: bool = False) -> bool:
    current_version = 0 if force else _current_schema_version(conn)
    if current_version >= SCHEMA_VERSION:
        logger.debug(
            "database schema already initialized",
            extra={"event": {"schema_version": current_version}},
        )
        return False

    with conn.cursor() as cursor:
        cursor.execute(SCHEMA_SQL)
        cursor.execute(
            """
            INSERT INTO rag.schema_migrations (version, description)
            VALUES (%s, %s)
            ON CONFLICT (version) DO NOTHING
            """,
            (SCHEMA_VERSION, SCHEMA_DESCRIPTION),
        )
    return True


def init_db(*, force: bool = False) -> None:
    global _schema_initialized

    if _schema_initialized and not force:
        return

    with _schema_init_lock:
        if _schema_initialized and not force:
            return

        trace("Database initialization started", logger)
        with log_timing(logger, "database_schema_init"):
            with connect() as conn:
                applied = _apply_schema(conn, force=force)
                conn.commit()
        _schema_initialized = True

        if applied:
            logger.info(
                "database schema initialized",
                extra={"event": {"schema_version": SCHEMA_VERSION}},
            )
        trace("Database initialization completed", logger)


def ensure_database() -> None:
    init_db()
