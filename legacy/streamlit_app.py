from __future__ import annotations

import os
from html import escape
from datetime import datetime
from itertools import groupby
from typing import Any

import requests
import streamlit as st

from app.core.logging import get_logger, log_timing, trace

DEFAULT_API_BASE_URL = os.getenv(
    "STREAMLIT_API_BASE_URL",
    "http://127.0.0.1:8000/api/v1",
)

logger = get_logger(__name__)


class ApiError(Exception):
    pass


def _api_base_url() -> str:
    return st.session_state.api_base_url.rstrip("/")


def _api_url(path: str) -> str:
    return f"{_api_base_url()}{path}"


def api_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    trace(f"Streamlit API request {method} {path}", logger)
    try:
        with log_timing(logger, "streamlit_api_request", method=method, path=path):
            response = requests.request(
                method=method,
                url=_api_url(path),
                json=payload,
                params=params,
                timeout=timeout,
            )
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.exception(
            "streamlit api request returned http error",
            extra={"event": {"method": method, "path": path, "status_code": response.status_code}},
        )
        trace(f"Streamlit API request failed {method} {path}", logger)
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or str(exc)
        raise ApiError(str(detail)) from exc
    except requests.RequestException as exc:
        logger.exception(
            "streamlit api request failed",
            extra={"event": {"method": method, "path": path}},
        )
        trace(f"Streamlit API request failed {method} {path}", logger)
        raise ApiError(f"Could not connect to API: {exc}") from exc

    if not response.content:
        trace(f"Streamlit API request completed {method} {path}", logger)
        return {}

    logger.info(
        "streamlit api request completed",
        extra={"event": {"method": method, "path": path, "status_code": response.status_code}},
    )
    trace(f"Streamlit API request completed {method} {path}", logger)
    return response.json()


def upload_files(files, metadata: list[dict[str, str]]) -> dict[str, Any]:
    trace(f"Streamlit upload started for {len(files)} file(s)", logger)
    multipart_files = [
        ("files", (file.name, file.getvalue(), file.type or "application/octet-stream"))
        for file in files
    ]
    form_data = []
    for item in metadata:
        form_data.append(("filenames", item["filename"]))
        form_data.append(("tags", item["tags"]))

    try:
        with log_timing(logger, "streamlit_document_upload", file_count=len(files)):
            response = requests.post(
                _api_url("/documents/upload"),
                files=multipart_files,
                data=form_data,
                timeout=600,
            )
        response.raise_for_status()
    except requests.HTTPError as exc:
        logger.exception(
            "streamlit upload returned http error",
            extra={"event": {"status_code": response.status_code, "file_count": len(files)}},
        )
        trace("Streamlit upload failed", logger)
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text or str(exc)
        raise ApiError(str(detail)) from exc
    except requests.RequestException as exc:
        logger.exception("streamlit upload failed", extra={"event": {"file_count": len(files)}})
        trace("Streamlit upload failed", logger)
        raise ApiError(f"Could not connect to API: {exc}") from exc

    logger.info(
        "streamlit upload completed",
        extra={"event": {"status_code": response.status_code, "file_count": len(files)}},
    )
    trace("Streamlit upload completed", logger)
    return response.json()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def date_label(value: str | None) -> str:
    parsed = parse_datetime(value)
    if not parsed:
        return "Undated"

    today = datetime.now(parsed.tzinfo).date()
    date = parsed.date()
    if date == today:
        return "Today"
    if (today - date).days == 1:
        return "Yesterday"

    return date.strftime("%b %d, %Y")


def display_datetime(value: str | None) -> str:
    parsed = parse_datetime(value)
    if not parsed:
        return ""

    return parsed.strftime("%b %d, %Y %H:%M")


def compact_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text and text.lower() != "none" else fallback


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --surface: #151820;
            --surface-2: #1f2330;
            --surface-3: #252a36;
            --border: #343a48;
            --text-soft: #a7adba;
            --accent: #ff4b4b;
            --cyan: #7dc4f4;
            --green: #2bd576;
        }

        #MainMenu, footer, .stDeployButton {
            visibility: hidden;
            height: 0;
        }

        .block-container {
            max-width: 1680px;
            padding-top: 2.25rem;
            padding-bottom: 4rem;
        }

        [data-testid="stSidebar"] {
            background: #191c25;
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] label {
            color: #d8dde8;
        }

        h1 {
            letter-spacing: 0;
            font-size: 2.05rem;
            margin-bottom: 0.2rem;
        }

        h2, h3 {
            letter-spacing: 0;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            border-radius: 7px;
            min-height: 2.35rem;
            font-weight: 650;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }

        .page-kicker {
            color: var(--text-soft);
            font-size: 0.94rem;
            margin-bottom: 1.25rem;
        }

        .toolbar-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.9rem;
            margin: 1rem 0 1.6rem;
        }

        .metric-card {
            border: 1px solid var(--border);
            background: linear-gradient(180deg, #1d212b 0%, #171a23 100%);
            border-radius: 8px;
            padding: 0.95rem 1rem;
            min-height: 6.25rem;
        }

        .metric-card__label {
            color: var(--text-soft);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 0.55rem;
        }

        .metric-card__value {
            color: #f7f9ff;
            font-size: 1.7rem;
            line-height: 1.15;
            font-weight: 750;
        }

        .metric-card__note {
            color: var(--text-soft);
            margin-top: 0.45rem;
            font-size: 0.82rem;
        }

        .section-heading {
            margin-top: 1.7rem;
            margin-bottom: 0.55rem;
        }

        .section-heading__title {
            color: #f8f9ff;
            font-size: 1.12rem;
            font-weight: 750;
        }

        .section-heading__caption {
            color: var(--text-soft);
            font-size: 0.9rem;
            margin-top: 0.15rem;
        }

        .origin-pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid var(--border);
            background: #202432;
            color: #e8edf7;
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            font-size: 0.82rem;
            font-weight: 700;
            margin: 0.15rem 0 0.45rem;
        }

        .route-reason {
            color: var(--text-soft);
            font-size: 0.82rem;
            margin: -0.25rem 0 0.75rem;
        }

        .empty-chat {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #151922;
            padding: 1.15rem;
            max-width: 760px;
            margin-top: 1rem;
        }

        .empty-chat__title {
            color: #f7f9ff;
            font-weight: 750;
            font-size: 1.05rem;
            margin-bottom: 0.4rem;
        }

        .empty-chat__body {
            color: var(--text-soft);
            margin-bottom: 0.8rem;
        }

        .suggestion-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
        }

        .suggestion {
            border: 1px solid var(--border);
            border-radius: 7px;
            padding: 0.65rem 0.75rem;
            color: #dce3ef;
            background: #1b202b;
            font-size: 0.9rem;
        }

        .status-pill {
            display: inline-flex;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            font-size: 0.78rem;
            font-weight: 700;
            background: #203528;
            color: #7af0a6;
        }

        .status-pill--failed {
            background: #3a2023;
            color: #ff9090;
        }

        .status-pill--pending {
            background: #332c1d;
            color: #ffd37d;
        }

        .tag-pill {
            display: inline-block;
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 0.12rem 0.45rem;
            margin: 0.05rem;
            color: #cbd4e2;
            background: #202431;
            font-size: 0.78rem;
        }

        .bar-list {
            border: 1px solid var(--border);
            border-radius: 8px;
            background: #151922;
            padding: 0.85rem;
            min-height: 260px;
        }

        .bar-row {
            margin-bottom: 0.78rem;
        }

        .bar-row:last-child {
            margin-bottom: 0;
        }

        .bar-row__meta {
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            color: #e7ecf6;
            font-size: 0.84rem;
            font-weight: 650;
            margin-bottom: 0.32rem;
        }

        .bar-row__label {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .bar-row__value {
            color: var(--text-soft);
            flex: 0 0 auto;
        }

        .bar-track {
            height: 0.48rem;
            border-radius: 999px;
            background: #252a36;
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            border-radius: 999px;
            background: #7dc4f4;
        }

        .doc-name {
            color: #f5f7fb;
            font-weight: 750;
            line-height: 1.2;
        }

        .row-muted {
            color: var(--text-soft);
            font-size: 0.82rem;
        }

        .admin-table-row {
            border-bottom: 1px solid rgba(52, 58, 72, 0.6);
            padding: 0.3rem 0;
        }

        .sidebar-title {
            font-size: 1.05rem;
            color: #f8f9ff;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }

        .sidebar-caption {
            color: var(--text-soft);
            font-size: 0.82rem;
            margin-bottom: 0.9rem;
        }

        .sidebar-section-label {
            color: #f6f8fd;
            font-size: 0.86rem;
            font-weight: 800;
            margin: 1.2rem 0 0.45rem;
            text-transform: uppercase;
        }

        @media (max-width: 1000px) {
            .metric-grid, .suggestion-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 640px) {
            .metric-grid, .suggestion-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"# {escape(title)}")
    if subtitle:
        st.markdown(
            f"<div class='page-kicker'>{escape(subtitle)}</div>",
            unsafe_allow_html=True,
        )


def render_section_heading(title: str, caption: str | None = None) -> None:
    caption_html = (
        f"<div class='section-heading__caption'>{escape(caption)}</div>"
        if caption
        else ""
    )
    st.markdown(
        "\n".join(
            [
                "<div class='section-heading'>",
                f"<div class='section-heading__title'>{escape(title)}</div>",
                caption_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_metric_grid(metrics: list[dict[str, Any]]) -> None:
    cards = []
    for metric in metrics:
        note = compact_text(metric.get("note"))
        note_html = (
            f"<div class='metric-card__note'>{escape(note)}</div>" if note else ""
        )
        cards.append(
            "\n".join(
                [
                    "<div class='metric-card'>",
                    f"<div class='metric-card__label'>{escape(str(metric['label']))}</div>",
                    f"<div class='metric-card__value'>{escape(str(metric['value']))}</div>",
                    note_html,
                    "</div>",
                ]
            )
        )

    st.markdown(
        f"<div class='metric-grid'>{''.join(cards)}</div>",
        unsafe_allow_html=True,
    )


def status_pill(status: str | None) -> str:
    status_value = compact_text(status, "unknown")
    modifier = ""
    if status_value == "failed":
        modifier = " status-pill--failed"
    elif status_value == "not_indexed":
        modifier = " status-pill--pending"

    return (
        f"<span class='status-pill{modifier}'>"
        f"{escape(status_value.replace('_', ' '))}</span>"
    )


def normalize_tags(tags: Any) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    if isinstance(tags, (list, tuple, set)):
        return [str(tag).strip() for tag in tags if str(tag).strip()]

    return [str(tags).strip()]


def tag_pills(tags: Any) -> str:
    normalized_tags = normalize_tags(tags)
    if not normalized_tags:
        return ""

    return " ".join(
        f"<span class='tag-pill'>{escape(str(tag))}</span>"
        for tag in normalized_tags
    )


def render_origin(route: str | None, sources: list[dict[str, Any]], reasoning: str | None = None) -> None:
    label = route_origin_label(route, sources)
    st.markdown(
        f"<span class='origin-pill'>{escape(label)}</span>",
        unsafe_allow_html=True,
    )
    if reasoning:
        st.markdown(
            f"<div class='route-reason'>{escape(reasoning)}</div>",
            unsafe_allow_html=True,
        )


def render_empty_chat() -> None:
    suggestions = [
        "Summarize the indexed policy documents.",
        "Which uploaded documents mention onboarding?",
        "What changed in the latest document version?",
        "Search the web for current context if needed.",
    ]
    suggestion_html = "".join(
        f"<div class='suggestion'>{escape(suggestion)}</div>"
        for suggestion in suggestions
    )
    st.markdown(
        "\n".join(
            [
                "<div class='empty-chat'>",
                "<div class='empty-chat__title'>Start a grounded conversation</div>",
                (
                    "<div class='empty-chat__body'>Ask a question and the assistant will show "
                    "whether it used your documents, web search, or a direct response.</div>"
                ),
                f"<div class='suggestion-grid'>{suggestion_html}</div>",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_bar_list(
    rows: list[dict[str, Any]],
    label_key: str,
    value_key: str,
    empty: str,
    max_rows: int = 8,
) -> None:
    visible_rows = rows[:max_rows]
    if not visible_rows:
        st.caption(empty)
        return

    max_value = max(float(row.get(value_key) or 0) for row in visible_rows) or 1
    parts = []
    for row in visible_rows:
        label = compact_text(row.get(label_key), "Unknown")
        value = float(row.get(value_key) or 0)
        width = max(3, min(100, round((value / max_value) * 100)))
        value_text = str(int(value)) if value.is_integer() else f"{value:.2f}"
        parts.append(
            "\n".join(
                [
                    "<div class='bar-row'>",
                    "<div class='bar-row__meta'>",
                    f"<span class='bar-row__label'>{escape(label)}</span>",
                    f"<span class='bar-row__value'>{escape(value_text)}</span>",
                    "</div>",
                    "<div class='bar-track'>",
                    f"<div class='bar-fill' style='width:{width}%'></div>",
                    "</div>",
                    "</div>",
                ]
            )
        )

    st.markdown(
        f"<div class='bar-list'>{''.join(parts)}</div>",
        unsafe_allow_html=True,
    )


def render_sources(sources: list[dict[str, Any]]) -> None:
    if not sources:
        return

    with st.expander("Sources", expanded=False):
        for index, source in enumerate(sources, start=1):
            score = source.get("score")
            score_text = f"{score:.4f}" if isinstance(score, (float, int)) else "n/a"
            metadata = source.get("metadata") or {}
            url = metadata.get("url")
            title = source.get("source", "unknown")
            if url:
                st.markdown(f"**[{index}] [{title}]({url})**")
            else:
                st.markdown(f"**[{index}] {title}**")
            st.caption(f"Score: {score_text}")
            visible_metadata = {
                key: value
                for key, value in metadata.items()
                if key in {"filename", "page_number", "file_type", "title", "url"}
            }
            if visible_metadata:
                st.json(visible_metadata, expanded=False)


def infer_route_from_sources(sources: list[dict[str, Any]]) -> str:
    if any(
        (source.get("metadata") or {}).get("source_type") == "web"
        for source in sources
    ):
        return "web_search"
    if sources:
        return "retrieval"

    return "direct"


def route_origin_label(route: str | None, sources: list[dict[str, Any]] | None = None) -> str:
    normalized = route or infer_route_from_sources(sources or [])
    labels = {
        "web_search": "Searching the web",
        "retrieval": "Reading your documents",
        "direct": "Generating response",
    }

    return labels.get(normalized, "Generating response")


def add_message(
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
    contextualized_query: str | None = None,
    route: str | None = None,
    route_reasoning: str | None = None,
) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "sources": sources or [],
            "contextualized_query": contextualized_query,
            "route": route,
            "route_reasoning": route_reasoning,
        }
    )


def load_chat_sessions() -> list[dict[str, Any]]:
    return api_request("GET", "/chat/sessions", timeout=30).get("sessions", [])


def load_dashboard() -> dict[str, Any]:
    return api_request("GET", "/dashboard", timeout=60)


def load_ai_admin() -> dict[str, Any]:
    return api_request("GET", "/admin/ai", timeout=30)


def add_ai_key(payload: dict[str, Any]) -> dict[str, Any]:
    return api_request("POST", "/admin/ai/keys", payload=payload, timeout=60)


def delete_ai_key(key_id: str) -> dict[str, Any]:
    return api_request("DELETE", f"/admin/ai/keys/{key_id}", timeout=60)


def save_ai_settings(payload: dict[str, Any]) -> dict[str, Any]:
    return api_request("PUT", "/admin/ai/settings", payload=payload, timeout=60)


def load_provider_models(provider: str, key_id: str | None) -> list[str]:
    params = {"provider": provider}
    if key_id:
        params["key_id"] = key_id

    return api_request(
        "GET",
        "/admin/ai/models",
        params=params,
        timeout=60,
    ).get("models", [])


def load_prompts() -> list[dict[str, Any]]:
    return api_request("GET", "/admin/prompts", timeout=30).get("prompts", [])


def save_prompt(name: str, content: str, change_note: str | None) -> dict[str, Any]:
    return api_request(
        "PUT",
        f"/admin/prompts/{name}",
        payload={"content": content, "change_note": change_note},
        timeout=60,
    ).get("prompt", {})


def load_chat_session(session_id: str) -> None:
    interactions = api_request(
        "GET",
        f"/chat/sessions/{session_id}/interactions",
        timeout=30,
    ).get("interactions", [])
    st.session_state.api_session_id = session_id
    st.session_state.messages = []

    for interaction in interactions:
        add_message("user", interaction.get("query") or "")
        add_message(
            "assistant",
            interaction.get("answer") or "",
            sources=interaction.get("sources") or [],
            contextualized_query=interaction.get("contextualized_query"),
            route=interaction.get("route"),
            route_reasoning=interaction.get("route_reasoning"),
        )


def render_api_sidebar() -> str:
    st.sidebar.markdown(
        "<div class='sidebar-title'>MM RAG Workbench</div>"
        "<div class='sidebar-caption'>Documents, chat, and operations</div>",
        unsafe_allow_html=True,
    )
    with st.sidebar.expander("API connection", expanded=False):
        st.text_input("Base URL", key="api_base_url")
        if st.button("Health check", width="stretch"):
            try:
                health = api_request("GET", "/health", timeout=10)
                st.success(f"{health.get('service', 'API')}: {health.get('status')}")
            except ApiError as exc:
                st.error(str(exc))

    return st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Chat", "Documents", "Admin"],
        key="active_page",
    )


def _metric_value(value: Any) -> str | int | float:
    if isinstance(value, float):
        return f"{value:.2f}"

    return value if value not in (None, "") else 0


def _render_table(title: str, rows: list[dict[str, Any]], empty: str) -> None:
    render_section_heading(title)
    if rows:
        st.dataframe(
            rows,
            hide_index=True,
            width="stretch",
            height=min(420, 72 + len(rows) * 38),
        )
    else:
        st.caption(empty)


def _dashboard_table_rows(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    if kind == "top_documents":
        return [
            {
                "Document": compact_text(row.get("filename"), "Unknown"),
                "Version": compact_text(row.get("document_version"), "-"),
                "References": row.get("reference_count") or 0,
                "Queries": row.get("query_count") or 0,
                "Avg score": _metric_value(row.get("average_score") or 0),
                "Last referenced": display_datetime(row.get("last_referenced_at")),
            }
            for row in rows
        ]
    if kind == "queries":
        return [
            {
                "Query": compact_text(row.get("query")),
                "Route": route_origin_label(row.get("route"))
                if row.get("route")
                else "",
                "Contexts": row.get("context_count") or row.get("retrieved_chunk_count") or 0,
                "When": display_datetime(row.get("created_at")),
            }
            for row in rows
        ]
    if kind == "failures":
        return [
            {
                "Document": compact_text(row.get("filename"), "Unknown"),
                "Version": compact_text(row.get("document_version"), "-"),
                "Error": compact_text(row.get("last_error"), "No error details"),
                "Updated": display_datetime(row.get("updated_at")),
            }
            for row in rows
        ]
    if kind == "largest":
        return [
            {
                "Document": compact_text(row.get("filename"), "Unknown"),
                "Version": compact_text(row.get("document_version"), "-"),
                "Size MB": row.get("size_mb") or 0,
                "Status": compact_text(row.get("status"), "unknown").replace("_", " "),
            }
            for row in rows
        ]

    return rows


def render_dashboard() -> None:
    header_columns = st.columns([0.78, 0.22], vertical_alignment="center")
    with header_columns[0]:
        render_page_header(
            "Dashboard",
            "System health, document coverage, and retrieval usage at a glance.",
        )
    with header_columns[1]:
        if st.button("Refresh dashboard", width="stretch"):
            st.rerun()

    try:
        dashboard = load_dashboard()
    except ApiError as exc:
        st.error(str(exc))
        return

    totals = dashboard.get("totals") or {}
    status_rows = dashboard.get("document_status") or []
    tag_rows = dashboard.get("document_tags") or []
    version_rows = dashboard.get("document_versions") or []
    storage = dashboard.get("storage") or {}

    render_metric_grid(
        [
            {
                "label": "Documents uploaded",
                "value": _metric_value(totals.get("total_documents_uploaded")),
                "note": "Total registry entries",
            },
            {
                "label": "Documents indexed",
                "value": _metric_value(totals.get("total_documents_indexed")),
                "note": f"{_metric_value(totals.get('total_indexed_chunks'))} chunks indexed",
            },
            {
                "label": "Documents failed",
                "value": _metric_value(totals.get("documents_failed")),
                "note": "Needs attention",
            },
            {
                "label": "Retrieval score",
                "value": _metric_value(totals.get("average_retrieval_score")),
                "note": "Average across logged chunks",
            },
            {
                "label": "Chat sessions",
                "value": _metric_value(totals.get("total_chat_sessions")),
                "note": f"{_metric_value(totals.get('total_queries'))} total queries",
            },
            {
                "label": "Retrieved chunks",
                "value": _metric_value(totals.get("total_retrieved_chunks_logged")),
                "note": f"{_metric_value(totals.get('average_contexts_per_query'))} avg/query",
            },
            {
                "label": "Storage",
                "value": f"{_metric_value(storage.get('total_mb'))} MB",
                "note": "Total uploaded document size",
            },
            {
                "label": "Avg document",
                "value": f"{_metric_value(storage.get('average_document_mb'))} MB",
                "note": "Mean uploaded document size",
            },
        ]
    )

    render_section_heading(
        "Document Analytics",
        "Distribution by indexing status, tags, and document versions.",
    )
    chart_columns = st.columns(3)
    with chart_columns[0]:
        st.markdown("**Status**")
        render_bar_list(
            [
                {
                    "label": compact_text(row.get("label"), "unknown").replace("_", " "),
                    "count": row.get("count") or 0,
                }
                for row in status_rows
            ],
            "label",
            "count",
            "No document status data yet.",
        )

    with chart_columns[1]:
        st.markdown("**Tags**")
        render_bar_list(
            [
                {
                    "label": compact_text(row.get("tag"), "untagged"),
                    "count": row.get("count") or 0,
                }
                for row in tag_rows
            ],
            "label",
            "count",
            "No tag data yet.",
        )

    with chart_columns[2]:
        st.markdown("**Versions**")
        render_bar_list(
            [
                {
                    "label": compact_text(row.get("version"), "unversioned"),
                    "count": row.get("count") or 0,
                }
                for row in version_rows
            ],
            "label",
            "count",
            "No version data yet.",
        )

    _render_table(
        "Top Referenced Documents",
        _dashboard_table_rows(
            dashboard.get("top_referenced_documents") or [],
            "top_documents",
        ),
        "No retrieval usage has been logged yet. Ask questions in Chat to populate this.",
    )

    lower_columns = st.columns(2)
    with lower_columns[0]:
        _render_table(
            "Recent Queries",
            _dashboard_table_rows(dashboard.get("recent_queries") or [], "queries"),
            "No chat queries yet.",
        )
    with lower_columns[1]:
        _render_table(
            "Recent Failed Documents",
            _dashboard_table_rows(
                dashboard.get("recent_failed_documents") or [],
                "failures",
            ),
            "No failed documents.",
        )

    _render_table(
        "Largest Documents",
        _dashboard_table_rows(storage.get("largest_documents") or [], "largest"),
        "No uploaded documents yet.",
    )


def _key_display(key: dict[str, Any]) -> str:
    return f"{key.get('label')} ({key.get('masked_key')})"


def _provider_keys(keys: list[dict[str, Any]], provider: str) -> list[dict[str, Any]]:
    return [
        key
        for key in keys
        if key.get("provider") == provider and key.get("is_active", True)
    ]


def render_ai_settings_admin() -> None:
    try:
        state = load_ai_admin()
    except ApiError as exc:
        st.error(str(exc))
        return

    providers = state.get("providers") or ["groq"]
    defaults = state.get("default_base_urls") or {}
    settings = state.get("settings") or {}
    keys = state.get("keys") or []
    active_provider = settings.get("active_provider") or providers[0]

    render_section_heading(
        "Active Model",
        "Choose the provider, credential, and generation defaults used by the API.",
    )

    provider = st.selectbox(
        "LLM provider",
        providers,
        index=providers.index(active_provider) if active_provider in providers else 0,
    )
    provider_keys = _provider_keys(keys, provider)
    key_options = [""] + [key["id"] for key in provider_keys]
    key_lookup = {key["id"]: key for key in provider_keys}
    active_key_id = (
        settings.get("active_key_id")
        if provider == settings.get("active_provider")
        else None
    )
    selected_key_id = st.selectbox(
        "API key",
        key_options,
        index=key_options.index(active_key_id) if active_key_id in key_options else 0,
        format_func=lambda value: (
            _key_display(key_lookup[value])
            if value
            else "Environment fallback" if provider == "groq" else "No saved key selected"
        ),
    )

    model_key = f"admin_model_{provider}_{selected_key_id or 'fallback'}"
    if model_key not in st.session_state:
        st.session_state[model_key] = settings.get("active_model") or ""

    model_rows = st.session_state.get("admin_models", {}).get(model_key, [])
    if model_rows:
        selected_model = st.selectbox("Available models", model_rows)
        if st.button("Use selected model"):
            st.session_state[model_key] = selected_model
            st.rerun()

    model = st.text_input("Active model", key=model_key)
    settings_columns = st.columns([0.25, 0.25, 0.25, 0.25])
    temperature = settings_columns[0].number_input(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=float(settings.get("temperature") or 0),
        step=0.1,
    )
    max_tokens = settings_columns[1].number_input(
        "Max tokens",
        min_value=1,
        max_value=32000,
        value=int(settings.get("max_tokens") or 1024),
        step=128,
    )
    if settings_columns[2].button("List models", width="stretch"):
        try:
            models = load_provider_models(provider, selected_key_id or None)
            st.session_state.setdefault("admin_models", {})[model_key] = models
            if models:
                st.success(f"Loaded {len(models)} model(s).")
            else:
                st.warning("No models were returned.")
            st.rerun()
        except ApiError as exc:
            st.error(str(exc))

    if settings_columns[3].button("Save AI settings", type="primary", width="stretch"):
        try:
            save_ai_settings(
                {
                    "provider": provider,
                    "key_id": selected_key_id or None,
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": int(max_tokens),
                }
            )
            st.success("AI settings saved.")
        except ApiError as exc:
            st.error(str(exc))

    render_section_heading(
        "API Keys",
        "Add reusable provider keys. Values are stored masked after save.",
    )
    with st.form("add_ai_key"):
        key_columns = st.columns([0.18, 0.22, 0.3, 0.3])
        new_provider = key_columns[0].selectbox(
            "Provider",
            providers,
            key="new_key_provider",
        )
        label = key_columns[1].text_input("Label", placeholder="Production key")
        base_url = key_columns[2].text_input(
            "Base URL",
            value=defaults.get(new_provider) or "",
        )
        api_key = key_columns[3].text_input("API key", type="password")
        submitted = st.form_submit_button("Add API key", type="primary")
        if submitted:
            try:
                add_ai_key(
                    {
                        "provider": new_provider,
                        "label": label,
                        "base_url": base_url,
                        "api_key": api_key,
                    }
                )
                st.success("API key saved.")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

    if keys:
        st.dataframe(
            [
                {
                    "Provider": key.get("provider"),
                    "Label": key.get("label"),
                    "Key": key.get("masked_key"),
                    "Base URL": key.get("base_url") or "",
                }
                for key in keys
            ],
            hide_index=True,
            width="stretch",
            height=min(360, 72 + len(keys) * 38),
        )
        remove_options = [""] + [key["id"] for key in keys]
        remove_lookup = {key["id"]: key for key in keys}
        remove_columns = st.columns([0.74, 0.26])
        remove_key_id = remove_columns[0].selectbox(
            "Remove saved key",
            remove_options,
            format_func=lambda value: (
                _key_display(remove_lookup[value]) if value else "Select a key"
            ),
        )
        if remove_columns[1].button(
            "Remove key",
            disabled=not remove_key_id,
            width="stretch",
        ):
            try:
                delete_ai_key(remove_key_id)
                st.success("API key removed.")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    else:
        st.caption("No saved API keys yet.")


def render_prompts_admin() -> None:
    render_section_heading(
        "Prompt Library",
        "Edit runtime prompts and keep a versioned change trail.",
    )
    try:
        prompts = load_prompts()
    except ApiError as exc:
        st.error(str(exc))
        return

    if not prompts:
        st.caption("No prompts found.")
        return

    for index, prompt in enumerate(prompts):
        name = prompt.get("name")
        title = prompt.get("title") or name
        version = prompt.get("active_version")
        with st.expander(f"{title} v{version}", expanded=index == 0):
            st.caption(prompt.get("description") or "")
            st.caption(f"Prompt key: {name}")
            content = st.text_area(
                "Prompt content",
                value=prompt.get("content") or "",
                height=360,
                key=f"prompt_content_{name}_{version}",
            )
            note = st.text_input(
                "Change note",
                key=f"prompt_note_{name}",
                placeholder="What changed?",
            )
            if st.button("Save prompt", key=f"save_prompt_{name}", type="primary"):
                try:
                    updated = save_prompt(name, content, note)
                    st.success(
                        f"Saved {updated.get('title', title)} "
                        f"v{updated.get('active_version')}."
                    )
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))

            versions = prompt.get("versions") or []
            if versions:
                st.dataframe(
                    [
                        {
                            "Version": item.get("version"),
                            "Change note": item.get("change_note"),
                            "Created": display_datetime(item.get("created_at")),
                        }
                        for item in versions
                    ],
                    hide_index=True,
                    width="stretch",
                    height=min(320, 72 + len(versions) * 38),
                )


def render_admin() -> None:
    render_page_header(
        "Admin",
        "Manage model providers, credentials, and editable prompt versions.",
    )
    ai_tab, prompts_tab = st.tabs(["AI Settings", "Prompts"])
    with ai_tab:
        render_ai_settings_admin()
    with prompts_tab:
        render_prompts_admin()


def render_chat_sidebar() -> tuple[int, float]:
    st.sidebar.markdown(
        "<div class='sidebar-section-label'>Chats</div>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("New chat", width="stretch"):
        st.session_state.api_session_id = None
        st.session_state.messages = []
        st.rerun()

    try:
        sessions = load_chat_sessions()
    except ApiError as exc:
        sessions = []
        st.sidebar.error(str(exc))

    sorted_sessions = sorted(
        sessions,
        key=lambda item: item.get("updated_at") or item.get("created_at") or "",
        reverse=True,
    )
    for label, grouped in groupby(
        sorted_sessions,
        key=lambda item: date_label(item.get("updated_at") or item.get("created_at")),
    ):
        st.sidebar.caption(label)
        for session in grouped:
            title = session.get("title") or "Untitled chat"
            count = session.get("interaction_count") or 0
            if st.sidebar.button(
                f"{title} ({count})",
                key=f"session_{session['id']}",
                width="stretch",
            ):
                try:
                    load_chat_session(session["id"])
                    st.rerun()
                except ApiError as exc:
                    st.sidebar.error(str(exc))

    st.sidebar.markdown(
        "<div class='sidebar-section-label'>Retrieval</div>",
        unsafe_allow_html=True,
    )
    top_k = st.sidebar.number_input(
        "Top K",
        min_value=1,
        max_value=20,
        value=st.session_state.top_k,
        step=1,
    )
    score_threshold = st.sidebar.number_input(
        "Score threshold",
        min_value=0.0,
        max_value=1.0,
        value=st.session_state.score_threshold,
        step=0.05,
    )

    return int(top_k), float(score_threshold)


def render_chat(top_k: int, score_threshold: float) -> None:
    render_page_header(
        "Chat",
        "Ask questions and see whether the answer came from documents, web search, or direct generation.",
    )

    if not st.session_state.messages:
        render_empty_chat()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            contextualized_query = message.get("contextualized_query")
            route = message.get("route")
            if (
                message["role"] == "assistant"
                and contextualized_query
                and st.session_state.messages
            ):
                st.caption(f"Retrieved as: {contextualized_query}")
            if message["role"] == "assistant" and not message["content"].startswith("API error:"):
                reasoning = message.get("route_reasoning")
                render_origin(route, message.get("sources", []), reasoning)
            st.markdown(message["content"])
            render_sources(message.get("sources", []))

    if prompt := st.chat_input("Ask a question"):
        add_message("user", prompt)

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Generating response..."):
                try:
                    result = api_request(
                        "POST",
                        "/generate",
                        payload={
                            "query": prompt,
                            "top_k": top_k,
                            "score_threshold": score_threshold,
                            "session_id": st.session_state.api_session_id,
                        },
                        timeout=180,
                    )
                    st.session_state.api_session_id = result.get("session_id")
                    answer = result.get("answer") or "No answer was returned."
                    sources = result.get("sources") or []
                    contextualized_query = result.get("contextualized_query")
                    route = result.get("route")
                    route_reasoning = result.get("route_reasoning")
                    if contextualized_query and contextualized_query != prompt:
                        st.caption(f"Retrieved as: {contextualized_query}")
                    if route:
                        render_origin(route, sources, route_reasoning)
                    st.markdown(answer)
                    render_sources(sources)
                except ApiError as exc:
                    answer = f"API error: {exc}"
                    sources = []
                    contextualized_query = None
                    route = None
                    route_reasoning = None
                    st.error(answer)

        add_message(
            "assistant",
            answer,
            sources,
            contextualized_query,
            route=route,
            route_reasoning=route_reasoning,
        )


def load_documents(force: bool = False, sync: bool = False) -> list[dict[str, Any]]:
    if force or st.session_state.documents is None:
        if sync:
            response = api_request("POST", "/documents/sync", timeout=120)
        else:
            response = api_request("GET", "/documents", timeout=30)
        st.session_state.documents = response.get("documents", [])

    return st.session_state.documents


def selected_document_ids(documents: list[dict[str, Any]]) -> list[str]:
    selected = []
    for document in documents:
        doc_id = document.get("id")
        if doc_id and st.session_state.get(f"doc_select_{doc_id}", False):
            selected.append(doc_id)

    return selected


def document_row(document: dict[str, Any]) -> None:
    doc_id = document.get("id")
    columns = st.columns([0.06, 0.28, 0.1, 0.18, 0.12, 0.1, 0.16])
    columns[0].checkbox(
        "Select",
        key=f"doc_select_{doc_id}",
        label_visibility="collapsed",
    )
    filename = compact_text(document.get("filename"), "document")
    object_name = compact_text(document.get("object_name"))
    object_html = (
        f"<div class='row-muted'>{escape(object_name)}</div>"
        if object_name and object_name != filename
        else ""
    )
    columns[1].markdown(
        f"<div class='doc-name'>{escape(filename)}</div>{object_html}",
        unsafe_allow_html=True,
    )
    columns[2].write(compact_text(document.get("document_version"), "-"))
    columns[3].markdown(
        tag_pills(document.get("tags")) or "<span class='row-muted'>untagged</span>",
        unsafe_allow_html=True,
    )
    columns[4].markdown(
        status_pill(document.get("status")),
        unsafe_allow_html=True,
    )
    columns[5].write(document.get("chunk_count") or 0)
    error = document.get("last_error")
    updated = display_datetime(document.get("last_seen_at") or document.get("updated_at"))
    columns[6].markdown(
        escape(str(error)) if error else compact_text(updated, "-"),
        unsafe_allow_html=True,
    )


def render_document_group(title: str, documents: list[dict[str, Any]]) -> None:
    with st.expander(f"{title} ({len(documents)})", expanded=title == "Indexed"):
        if not documents:
            st.caption("No documents")
            return

        header = st.columns([0.06, 0.28, 0.1, 0.18, 0.12, 0.1, 0.16])
        header[1].caption("Filename")
        header[2].caption("Version")
        header[3].caption("Tags")
        header[4].caption("Status")
        header[5].caption("Chunks")
        header[6].caption("Updated / Error")

        for document in documents:
            document_row(document)


def run_document_action(path: str, document_ids: list[str], success: str) -> None:
    if not document_ids:
        st.warning("Select at least one document.")
        return

    try:
        with st.spinner("Working..."):
            result = api_request(
                "POST",
                path,
                payload={"document_ids": document_ids},
                timeout=900,
        )
        st.success(success.format(**result))
        for doc_id in document_ids:
            st.session_state[f"doc_select_{doc_id}"] = False
        load_documents(force=True)
    except ApiError as exc:
        st.error(str(exc))


def render_documents() -> None:
    render_page_header(
        "Documents",
        "Upload documents to MinIO, manage metadata, and control what is indexed in Qdrant.",
    )

    render_section_heading("Upload", "Add PDF, DOCX, PPT, PPTX, or text files and set searchable metadata before upload.")
    uploads = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "ppt", "pptx", "txt", "md"],
        accept_multiple_files=True,
    )
    upload_metadata = []
    if uploads:
        render_section_heading("Upload Metadata")
        for index, file in enumerate(uploads):
            columns = st.columns([0.5, 0.5])
            filename = columns[0].text_input(
                f"Filename for {file.name}",
                value=file.name,
                key=f"upload_filename_{index}_{file.name}",
            )
            tags = columns[1].text_input(
                "Tags",
                key=f"upload_tags_{index}_{file.name}",
                placeholder="e.g. HR, policy, onboarding",
            )
            upload_metadata.append(
                {
                    "filename": filename.strip(),
                    "tags": tags.strip(),
                }
            )

    missing_metadata = bool(uploads) and any(
        not item["filename"] or not item["tags"] for item in upload_metadata
    )
    if st.button("Upload to MinIO", type="primary", disabled=not uploads):
        if missing_metadata:
            st.warning("Add filename and tags for every selected document.")
            return
        try:
            with st.spinner("Uploading..."):
                result = upload_files(uploads, upload_metadata)
            uploaded = result.get("documents", [])
            skipped = result.get("skipped", [])
            if uploaded:
                st.success(f"Uploaded {len(uploaded)} document(s).")
            if skipped:
                for item in skipped:
                    existing_name = item.get("existing_filename") or "another document"
                    existing_version = item.get("existing_version") or "unknown"
                    st.warning(
                        f"{item.get('filename', 'Document')} already exists "
                        f"as {existing_name} (version {existing_version})."
                    )
            load_documents(force=True)
        except ApiError as exc:
            st.error(str(exc))

    try:
        documents = load_documents()
    except ApiError as exc:
        st.error(str(exc))
        return

    selected_ids = selected_document_ids(documents)
    indexed_count = len([doc for doc in documents if doc.get("status") == "indexed"])
    failed_count = len([doc for doc in documents if doc.get("status") == "failed"])
    render_section_heading("Library", "Review uploaded documents and run indexing actions.")
    render_metric_grid(
        [
            {"label": "Uploaded", "value": len(documents), "note": "Registry entries"},
            {"label": "Indexed", "value": indexed_count, "note": "Ready for retrieval"},
            {"label": "Failed", "value": failed_count, "note": "Needs attention"},
            {"label": "Selected", "value": len(selected_ids), "note": "Current action set"},
        ]
    )

    action_columns = st.columns([0.25, 0.25, 0.25, 0.25])
    with action_columns[0]:
        if st.button("Refresh documents", width="stretch"):
            try:
                load_documents(force=True, sync=True)
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))
    with action_columns[1]:
        if st.button("Index selected", width="stretch"):
            run_document_action(
                "/documents/index",
                selected_ids,
                "Indexed {indexed_documents} document(s), {indexed_chunks} chunk(s).",
            )
    with action_columns[2]:
        if st.button("Remove vectors", width="stretch"):
            run_document_action(
                "/documents/remove-vectors",
                selected_ids,
                "Removed {removed_vectors} vector(s) from Qdrant.",
            )
    with action_columns[3]:
        if st.button("Remove documents", width="stretch"):
            run_document_action(
                "/documents/remove",
                selected_ids,
                "Removed {removed_documents} document(s) and {removed_vectors} vector(s).",
            )

    grouped = {
        "Indexed": [doc for doc in documents if doc.get("status") == "indexed"],
        "Not indexed": [doc for doc in documents if doc.get("status") == "not_indexed"],
        "Failed": [doc for doc in documents if doc.get("status") == "failed"],
    }
    for title, rows in grouped.items():
        render_document_group(
            title,
            sorted(rows, key=lambda item: item.get("filename") or ""),
        )


def init_state() -> None:
    defaults = {
        "api_base_url": DEFAULT_API_BASE_URL,
        "messages": [],
        "documents": None,
        "api_session_id": None,
        "top_k": 4,
        "score_threshold": 0.0,
        "active_page": "Dashboard",
        "admin_models": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def main() -> None:
    st.set_page_config(page_title="RAG Workbench", layout="wide")
    inject_styles()
    init_state()

    page = render_api_sidebar()
    if page == "Dashboard":
        render_dashboard()
    elif page == "Chat":
        top_k, score_threshold = render_chat_sidebar()
        st.session_state.top_k = top_k
        st.session_state.score_threshold = score_threshold
        render_chat(top_k=top_k, score_threshold=score_threshold)
    elif page == "Admin":
        render_admin()
    else:
        render_documents()


if __name__ == "__main__":
    main()
