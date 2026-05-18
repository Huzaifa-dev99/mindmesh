from typing import Any
from uuid import uuid4

from app.core.database import connect, ensure_database
from app.core.logging import get_logger, trace
from app.core.serialization import serialize_datetime

logger = get_logger(__name__)

SYSTEM_PROMPT_NAME = "rag_answer"
CONTEXTUALIZE_PROMPT_NAME = "contextualize_query"
ROUTER_PROMPT_NAME = "query_router"
WEB_SEARCH_PROMPT_NAME = "web_search_answer"
DIRECT_PROMPT_NAME = "direct_answer"

DEFAULT_PROMPTS = {
    SYSTEM_PROMPT_NAME: {
        "title": "RAG answer prompt",
        "description": "Controls how the assistant answers with retrieved context.",
        "content": """
You are a reliable Retrieval-Augmented Generation (RAG) assistant.

Your task is to answer the user's question strictly using the provided retrieved context.
Do not use outside knowledge, assumptions, or fabricated information.

Guidelines:
- Base every answer only on the retrieved context.
- If the answer cannot be found in the context, respond with:
  "I do not know based on the indexed documents."
- Keep responses concise, accurate, and directly relevant to the question.
- When applicable, cite supporting sources using bracket notation such as [1], [2], etc.
- Do not mention information that is not explicitly present in the context.
- Prefer clear and factual language over speculation or interpretation.

Original user question:
{query}

Contextualized retrieval query:
{contextualized_query}

Retrieved context:
{context}
""".strip(),
    },
    CONTEXTUALIZE_PROMPT_NAME: {
        "title": "Contextualize query prompt",
        "description": "Rewrites follow-up questions into standalone retrieval queries.",
        "content": """
You are a query rewriting assistant for a RAG system.

Rewrite the latest user query into a standalone search query using the chat history.
Use the history only to resolve references such as pronouns, follow-up questions, or implied subjects.

Guidelines:
- Always rewrite the query to be fully self-contained and understandable without the chat history.
- Preserve the user's original intent.
- Keep the rewritten query concise.
- Do not answer the question.
- Do not add facts that are not present in the chat history.

Chat history:
{history}

Latest user query:
{query}

Return only the standalone query.
""".strip(),
    },
    ROUTER_PROMPT_NAME: {
        "title": "Query router prompt",
        "description": "Chooses retrieval, web search, or a direct answer path.",
        "content": """
You are a routing component for a RAG assistant.

Choose exactly one route for the latest user query.

Routes:
- retrieval: Use when the user asks about uploaded/indexed documents, policies, internal knowledge, previous document content, or anything likely to be answered from the vector database.
- web_search: Use when the user asks for current, recent, time-sensitive, external, public, or real-world information that may have changed.
- direct: Use only for simple greetings, small talk, or operational questions that do not require indexed documents or current web facts.

Guidelines:
- Prefer retrieval when the user refers to "the document", "uploaded file", "policy", "manual", "indexed data", or asks a question that could be answered by private documents.
- Prefer web_search for words like latest, today, yesterday, current, news, price, weather, score, release, recent, or when the answer depends on external facts.
- Do not answer the query.

Return strict JSON only:
{
  "route": "retrieval" | "web_search" | "direct",
  "reasoning": "brief reason"
}

Query:
{query}
""".strip(),
    },
    WEB_SEARCH_PROMPT_NAME: {
        "title": "Web search answer prompt",
        "description": "Generates a cited answer from Tavily web search results.",
        "content": """
You are a web-grounded answer assistant.

Answer the user's question using only the provided web search results.
If the results do not contain enough information, say that the web results were insufficient.

Guidelines:
- Keep the answer concise and factual.
- Cite sources using bracket notation such as [1], [2].
- Do not cite sources that do not support the statement.
- Do not use outside knowledge.

User question:
{query}

Web search results:
{context}
""".strip(),
    },
    DIRECT_PROMPT_NAME: {
        "title": "Direct answer prompt",
        "description": "Controls direct responses when retrieval and web search are not used.",
        "content": """
You are a helpful local assistant.

Answer the user's question directly and concisely.
Do not claim to have searched the web or read indexed documents for this answer.
If the user asks about uploaded documents, explain that retrieval needs to be enabled.

User question:
{query}
""".strip(),
    },
}

def seed_default_prompts() -> None:
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            for name, prompt in DEFAULT_PROMPTS.items():
                cursor.execute(
                    """
                    INSERT INTO rag.prompts (
                        name,
                        title,
                        description,
                        active_version
                    )
                    VALUES (%s, %s, %s, 1)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (name, prompt["title"], prompt["description"]),
                )
                cursor.execute(
                    """
                    INSERT INTO rag.prompt_versions (
                        id,
                        prompt_name,
                        version,
                        content,
                        change_note
                    )
                    VALUES (%s, %s, 1, %s, %s)
                    ON CONFLICT (prompt_name, version) DO NOTHING
                    """,
                    (
                        uuid4(),
                        name,
                        prompt["content"],
                        "Initial prompt extracted from codebase.",
                    ),
                )
        conn.commit()
    logger.debug("default prompt seeding checked", extra={"event": {"prompt_count": len(DEFAULT_PROMPTS)}})


def _row_to_prompt(row: dict) -> dict:
    return {
        "name": row["name"],
        "title": row["title"],
        "description": row["description"],
        "active_version": row["active_version"],
        "content": row["content"],
        "created_at": serialize_datetime(row["created_at"]),
        "updated_at": serialize_datetime(row["updated_at"]),
        "versions": row.get("versions") or [],
    }


def list_prompts(include_versions: bool = True) -> list[dict]:
    trace("Prompt listing started", logger)
    seed_default_prompts()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    prompt.name,
                    prompt.title,
                    prompt.description,
                    prompt.active_version,
                    prompt.created_at,
                    prompt.updated_at,
                    version.content
                FROM rag.prompts AS prompt
                JOIN rag.prompt_versions AS version
                    ON version.prompt_name = prompt.name
                   AND version.version = prompt.active_version
                ORDER BY prompt.name ASC
                """
            )
            prompts = [_row_to_prompt(row) for row in cursor.fetchall()]

            if include_versions:
                for prompt in prompts:
                    cursor.execute(
                        """
                        SELECT version, change_note, created_at
                        FROM rag.prompt_versions
                        WHERE prompt_name = %s
                        ORDER BY version DESC
                        """,
                        (prompt["name"],),
                    )
                    prompt["versions"] = [
                        {
                            "version": row["version"],
                            "change_note": row["change_note"],
                            "created_at": serialize_datetime(row["created_at"]),
                        }
                        for row in cursor.fetchall()
                    ]

    logger.info("prompt listing completed", extra={"event": {"prompt_count": len(prompts)}})
    trace(f"Prompt listing completed with {len(prompts)} prompt(s)", logger)
    return prompts


def get_prompt_content(name: str) -> str:
    seed_default_prompts()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT version.content
                FROM rag.prompts AS prompt
                JOIN rag.prompt_versions AS version
                    ON version.prompt_name = prompt.name
                   AND version.version = prompt.active_version
                WHERE prompt.name = %s
                """,
                (name,),
            )
            row = cursor.fetchone()

    if row:
        logger.debug("prompt content loaded", extra={"event": {"prompt_name": name}})
        return row["content"]

    if name in DEFAULT_PROMPTS:
        logger.warning("prompt content fell back to code default", extra={"event": {"prompt_name": name}})
        return DEFAULT_PROMPTS[name]["content"]

    raise ValueError(f"Unknown prompt: {name}")


def render_prompt(name: str, **values: Any) -> str:
    """Render only explicit {name} placeholders, leaving JSON braces untouched."""
    content = get_prompt_content(name)
    for key, value in values.items():
        content = content.replace(f"{{{key}}}", str(value))

    return content


def update_prompt(name: str, content: str, change_note: str | None = None) -> dict:
    trace("Prompt update started", logger)
    seed_default_prompts()
    normalized = content.strip()
    if not normalized:
        raise ValueError("Prompt content cannot be empty")

    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    prompt.active_version,
                    version.content
                FROM rag.prompts AS prompt
                JOIN rag.prompt_versions AS version
                    ON version.prompt_name = prompt.name
                   AND version.version = prompt.active_version
                WHERE prompt.name = %s
                """,
                (name,),
            )
            current = cursor.fetchone()
            if not current:
                raise ValueError(f"Unknown prompt: {name}")

            if current["content"].strip() == normalized:
                conn.commit()
                logger.info("prompt update skipped without content changes", extra={"event": {"prompt_name": name}})
                prompt = [prompt for prompt in list_prompts() if prompt["name"] == name][0]
                trace("Prompt update skipped without changes", logger)
                return prompt

            new_version = int(current["active_version"]) + 1
            cursor.execute(
                """
                INSERT INTO rag.prompt_versions (
                    id,
                    prompt_name,
                    version,
                    content,
                    change_note
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (uuid4(), name, new_version, normalized, change_note),
            )
            cursor.execute(
                """
                UPDATE rag.prompts
                SET active_version = %s,
                    updated_at = NOW()
                WHERE name = %s
                """,
                (new_version, name),
            )
        conn.commit()

    prompt = [prompt for prompt in list_prompts() if prompt["name"] == name][0]
    logger.info(
        "prompt updated",
        extra={"event": {"prompt_name": name, "active_version": prompt["active_version"]}},
    )
    trace("Prompt update completed", logger)
    return prompt
