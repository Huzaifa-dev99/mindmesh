from hashlib import sha256
import re
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import requests

from app.core.config import (
    ADMIN_SECRET_KEY,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MAX_TOKENS,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
)
from app.core.database import connect, ensure_database
from app.core.logging import get_logger, log_timing, trace
from app.core.serialization import serialize_datetime

SUPPORTED_PROVIDERS = ("openai", "gemini", "groq", "vllm")
DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "groq": "https://api.groq.com/openai/v1",
    "vllm": "http://127.0.0.1:8001/v1",
}

logger = get_logger(__name__)

def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        allowed = ", ".join(SUPPORTED_PROVIDERS)
        raise ValueError(f"Unsupported provider {provider!r}. Use one of: {allowed}.")

    return normalized


def _normalize_base_url(provider: str, base_url: str) -> str:
    cleaned = (base_url or DEFAULT_BASE_URLS[provider]).strip().replace("\\", "/")
    original = cleaned
    if not cleaned:
        cleaned = DEFAULT_BASE_URLS[provider]

    if provider == "gemini":
        return cleaned.rstrip("/")

    while re.match(r"^https?://https?://", cleaned, flags=re.IGNORECASE):
        cleaned = re.sub(r"^https?://(https?://)", r"\1", cleaned, flags=re.IGNORECASE)

    if not re.match(r"^https?://", cleaned, flags=re.IGNORECASE):
        host_part = cleaned.split("/", 1)[0].lower()
        scheme = "http" if host_part.startswith(("127.", "localhost", "0.0.0.0", "::1")) else "https"
        cleaned = f"{scheme}://{cleaned}"

    parsed = urlsplit(cleaned)
    if not parsed.netloc:
        raise ValueError(f"Invalid base URL for {provider}: {base_url!r}")

    path = re.sub(r"/{2,}", "/", parsed.path or "").rstrip("/")
    for suffix in ("/chat/completions", "/completions", "/models"):
        if path.lower().endswith(suffix):
            path = path[: -len(suffix)].rstrip("/")
            break

    if provider == "groq":
        if not path.lower().endswith("/openai/v1"):
            path = f"{path}/openai/v1" if path else "/openai/v1"
    elif not path.lower().endswith("/v1"):
        path = f"{path}/v1" if path else "/v1"

    normalized = urlunsplit((parsed.scheme.lower(), parsed.netloc, path, "", "")).rstrip("/")
    if normalized != original:
        logger.debug(
            "ai provider base url normalized",
            extra={"event": {"provider": provider, "base_url": normalized}},
        )
    return normalized


def _cipher():
    if not ADMIN_SECRET_KEY:
        return None

    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError(
            "ADMIN_SECRET_KEY is configured but cryptography is not installed."
        ) from exc

    return Fernet(ADMIN_SECRET_KEY.encode("utf-8"))


def _encrypt_api_key(api_key: str) -> str:
    cleaned = api_key.strip()
    if not cleaned:
        raise ValueError("API key cannot be empty")

    cipher = _cipher()
    if not cipher:
        return f"plain:{cleaned}"

    encrypted = cipher.encrypt(cleaned.encode("utf-8")).decode("utf-8")
    return f"fernet:{encrypted}"


def _decrypt_api_key(value: str) -> str:
    if value.startswith("plain:"):
        return value.removeprefix("plain:")
    if value.startswith("fernet:"):
        cipher = _cipher()
        if not cipher:
            raise RuntimeError(
                "This API key was encrypted but ADMIN_SECRET_KEY is not configured."
            )
        decrypted = cipher.decrypt(value.removeprefix("fernet:").encode("utf-8"))
        return decrypted.decode("utf-8")

    return value


def _fingerprint(api_key: str) -> str:
    return sha256(api_key.encode("utf-8")).hexdigest()[:12]


def _masked_key(fingerprint: str) -> str:
    return f"stored key ...{fingerprint[-6:]}"


def _clear_llm_cache() -> None:
    try:
        from app.core.clients import get_llm

        get_llm.cache_clear()
        logger.info("llm cache cleared after ai settings change")
    except Exception:
        logger.warning("llm cache clear failed", exc_info=True)


def seed_ai_settings() -> None:
    ensure_database()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO rag.ai_settings (
                    id,
                    active_provider,
                    active_model,
                    temperature,
                    max_tokens
                )
                VALUES (TRUE, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                ("groq", GROQ_MODEL, GROQ_TEMPERATURE, GROQ_MAX_TOKENS),
            )
        conn.commit()
    logger.debug("ai settings seed checked")


def _row_to_key(row: dict) -> dict:
    base_url = row.get("base_url")
    if base_url:
        try:
            base_url = _normalize_base_url(row["provider"], base_url)
        except Exception:
            logger.debug("stored ai provider base url normalization failed", exc_info=True)

    return {
        "id": str(row["id"]),
        "provider": row["provider"],
        "label": row["label"],
        "masked_key": _masked_key(row["api_key_fingerprint"]),
        "base_url": base_url,
        "is_active": row["is_active"],
        "created_at": serialize_datetime(row["created_at"]),
        "updated_at": serialize_datetime(row["updated_at"]),
    }


def _setting_row(cursor) -> dict:
    cursor.execute("SELECT * FROM rag.ai_settings WHERE id = TRUE")
    row = cursor.fetchone()
    if row:
        return row

    seed_ai_settings()
    cursor.execute("SELECT * FROM rag.ai_settings WHERE id = TRUE")
    return cursor.fetchone()


def list_provider_keys(provider: str | None = None) -> list[dict]:
    trace("AI provider key listing started", logger)
    seed_ai_settings()
    with connect() as conn:
        with conn.cursor() as cursor:
            if provider:
                cursor.execute(
                    """
                    SELECT *
                    FROM rag.ai_provider_keys
                    WHERE provider = %s
                    ORDER BY created_at DESC
                    """,
                    (_normalize_provider(provider),),
                )
            else:
                cursor.execute(
                    """
                    SELECT *
                    FROM rag.ai_provider_keys
                    ORDER BY provider ASC, created_at DESC
                    """
                )
            keys = [_row_to_key(row) for row in cursor.fetchall()]
    logger.info(
        "ai provider key listing completed",
        extra={"event": {"provider": provider, "key_count": len(keys)}},
    )
    trace(f"AI provider key listing completed with {len(keys)} key(s)", logger)
    return keys


def get_ai_admin_state() -> dict:
    trace("AI admin state loading started", logger)
    seed_ai_settings()
    with connect() as conn:
        with conn.cursor() as cursor:
            settings = _setting_row(cursor)

    state = {
        "providers": list(SUPPORTED_PROVIDERS),
        "default_base_urls": DEFAULT_BASE_URLS,
        "settings": {
            "active_provider": settings["active_provider"],
            "active_key_id": (
                str(settings["active_key_id"]) if settings.get("active_key_id") else None
            ),
            "active_model": settings.get("active_model"),
            "temperature": settings["temperature"],
            "max_tokens": settings.get("max_tokens"),
            "uses_environment_fallback": settings.get("active_key_id") is None,
        },
        "keys": list_provider_keys(),
    }
    logger.info(
        "ai admin state loaded",
        extra={
            "event": {
                "active_provider": state["settings"]["active_provider"],
                "uses_environment_fallback": state["settings"]["uses_environment_fallback"],
                "key_count": len(state["keys"]),
            }
        },
    )
    trace("AI admin state loading completed", logger)
    return state


def add_provider_key(
    *,
    provider: str,
    label: str,
    api_key: str,
    base_url: str | None = None,
) -> dict:
    trace("AI provider key creation started", logger)
    provider = _normalize_provider(provider)
    label = label.strip() or f"{provider.title()} key"
    cleaned_base_url = _normalize_base_url(provider, base_url or DEFAULT_BASE_URLS[provider])
    cleaned_key = api_key.strip()
    key_id = uuid4()

    seed_ai_settings()
    with log_timing(logger, "ai_provider_key_create", provider=provider):
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO rag.ai_provider_keys (
                        id,
                        provider,
                        label,
                        api_key_encrypted,
                        api_key_fingerprint,
                        base_url
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        key_id,
                        provider,
                        label,
                        _encrypt_api_key(cleaned_key),
                        _fingerprint(cleaned_key),
                        cleaned_base_url,
                    ),
                )
                row = cursor.fetchone()
            conn.commit()

    result = _row_to_key(row)
    logger.info(
        "ai provider key created",
        extra={"event": {"provider": provider, "key_id": result["id"], "base_url": cleaned_base_url}},
    )
    trace("AI provider key creation completed", logger)
    return result


def delete_provider_key(key_id: str | UUID) -> dict:
    trace("AI provider key deletion started", logger)
    seed_ai_settings()
    parsed_id = UUID(str(key_id))
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.ai_settings
                SET active_key_id = NULL,
                    updated_at = NOW()
                WHERE active_key_id = %s
                """,
                (parsed_id,),
            )
            cursor.execute(
                """
                DELETE FROM rag.ai_provider_keys
                WHERE id = %s
                RETURNING *
                """,
                (parsed_id,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError("API key was not found")
        conn.commit()

    _clear_llm_cache()
    result = _row_to_key(row)
    logger.info("ai provider key deleted", extra={"event": {"provider": result["provider"], "key_id": result["id"]}})
    trace("AI provider key deletion completed", logger)
    return result


def update_ai_settings(
    *,
    provider: str,
    key_id: str | UUID | None,
    model: str,
    temperature: float,
    max_tokens: int | None,
) -> dict:
    trace("AI settings update started", logger)
    provider = _normalize_provider(provider)
    model = model.strip()
    if not model:
        raise ValueError("Model cannot be empty")

    parsed_key_id = UUID(str(key_id)) if key_id else None

    seed_ai_settings()
    with connect() as conn:
        with conn.cursor() as cursor:
            if parsed_key_id:
                cursor.execute(
                    """
                    SELECT provider
                    FROM rag.ai_provider_keys
                    WHERE id = %s
                      AND is_active = TRUE
                    """,
                    (parsed_key_id,),
                )
                key = cursor.fetchone()
                if not key:
                    raise ValueError("API key was not found")
                if key["provider"] != provider:
                    raise ValueError("Selected key does not belong to this provider")

            cursor.execute(
                """
                INSERT INTO rag.ai_settings (
                    id,
                    active_provider,
                    active_key_id,
                    active_model,
                    temperature,
                    max_tokens,
                    updated_at
                )
                VALUES (TRUE, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    active_provider = EXCLUDED.active_provider,
                    active_key_id = EXCLUDED.active_key_id,
                    active_model = EXCLUDED.active_model,
                    temperature = EXCLUDED.temperature,
                    max_tokens = EXCLUDED.max_tokens,
                    updated_at = NOW()
                """,
                (provider, parsed_key_id, model, temperature, max_tokens),
            )
        conn.commit()

    _clear_llm_cache()
    settings = get_ai_admin_state()["settings"]
    logger.info(
        "ai settings updated",
        extra={
            "event": {
                "provider": settings["active_provider"],
                "model": settings["active_model"],
                "has_key": bool(settings["active_key_id"]),
            }
        },
    )
    trace("AI settings update completed", logger)
    return settings


def _load_key_secret(key_id: str | UUID) -> dict:
    parsed_id = UUID(str(key_id))
    seed_ai_settings()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM rag.ai_provider_keys
                WHERE id = %s
                  AND is_active = TRUE
                """,
                (parsed_id,),
            )
            row = cursor.fetchone()

    if not row:
        raise ValueError("API key was not found")

    logger.debug("ai provider key secret loaded", extra={"event": {"provider": row["provider"], "key_id": str(row["id"])}})
    return {
        **_row_to_key(row),
        "api_key": _decrypt_api_key(row["api_key_encrypted"]),
    }


def get_active_llm_config() -> dict:
    seed_ai_settings()
    with connect() as conn:
        with conn.cursor() as cursor:
            settings = _setting_row(cursor)

    provider = settings["active_provider"]
    key_id = settings.get("active_key_id")
    if key_id:
        key = _load_key_secret(key_id)
        api_key = key["api_key"]
        base_url = key.get("base_url") or DEFAULT_BASE_URLS[provider]
    elif provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("No Groq API key is configured. Set GROQ_API_KEY or save a provider key.")
        api_key = GROQ_API_KEY
        base_url = GROQ_BASE_URL
    else:
        raise ValueError(
            f"No active API key is configured for provider {provider!r}."
        )

    config = {
        "provider": provider,
        "api_key": api_key,
        "base_url": _normalize_base_url(provider, base_url or DEFAULT_BASE_URLS[provider]),
        "model": settings.get("active_model") or GROQ_MODEL,
        "temperature": float(settings.get("temperature") or 0),
        "max_tokens": settings.get("max_tokens") or GROQ_MAX_TOKENS,
    }
    logger.info(
        "active llm config resolved",
        extra={"event": {"provider": config["provider"], "model": config["model"], "base_url": config["base_url"]}},
    )
    return config


def active_model_name() -> str:
    try:
        config = get_active_llm_config()
    except Exception:
        logger.debug("active model name fallback used", exc_info=True)
        return GROQ_MODEL

    return f"{config['provider']}:{config['model']}"


def _openai_compatible_models_url(provider: str, base_url: str) -> str:
    return f"{_normalize_base_url(provider, base_url)}/models"


def _response_error(response: requests.Response) -> ValueError:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text

    message = str(payload).replace("\n", " ")[:500]
    return ValueError(
        f"Model listing failed with HTTP {response.status_code}: {message}"
    )


def _openai_compatible_models(provider: str, api_key: str, base_url: str) -> list[str]:
    url = _openai_compatible_models_url(provider, base_url)
    logger.info("openai-compatible model listing request started", extra={"event": {"provider": provider, "url": url}})
    with log_timing(logger, "openai_compatible_model_listing", provider=provider):
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
    if not response.ok:
        logger.error(
            "openai-compatible model listing failed",
            extra={"event": {"provider": provider, "status_code": response.status_code, "url": url}},
        )
        raise _response_error(response)

    payload = response.json()
    models = [
        item.get("id")
        for item in payload.get("data", [])
        if item.get("id")
    ]

    if provider == "groq":
        models.sort()

    logger.info(
        "openai-compatible model listing completed",
        extra={"event": {"provider": provider, "model_count": len(models)}},
    )
    return models


def _gemini_models(api_key: str, base_url: str) -> list[str]:
    url = f"{base_url.rstrip('/')}/models"
    logger.info("gemini model listing request started", extra={"event": {"url": url}})
    with log_timing(logger, "gemini_model_listing"):
        response = requests.get(
            url,
            params={"key": api_key},
            timeout=30,
        )
    if not response.ok:
        logger.error(
            "gemini model listing failed",
            extra={"event": {"status_code": response.status_code, "url": url}},
        )
        raise _response_error(response)

    payload = response.json()
    models = []
    for item in payload.get("models", []):
        name = item.get("name")
        if not name:
            continue
        methods = item.get("supportedGenerationMethods") or []
        if methods and "generateContent" not in methods:
            continue
        models.append(name.removeprefix("models/"))

    models = sorted(models)
    logger.info("gemini model listing completed", extra={"event": {"model_count": len(models)}})
    return models


def list_provider_models(provider: str, key_id: str | UUID | None = None) -> list[str]:
    trace("AI model listing started", logger)
    provider = _normalize_provider(provider)
    if key_id:
        key = _load_key_secret(key_id)
        if key["provider"] != provider:
            raise ValueError("Selected key does not belong to this provider")
        api_key = key["api_key"]
        base_url = key.get("base_url") or DEFAULT_BASE_URLS[provider]
    elif provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("No Groq API key is configured. Set GROQ_API_KEY or select a saved key.")
        api_key = GROQ_API_KEY
        base_url = GROQ_BASE_URL
    else:
        raise ValueError("Select a saved API key before listing models")

    if provider == "gemini":
        models = _gemini_models(api_key, base_url)
    else:
        models = _openai_compatible_models(provider, api_key, base_url)

    logger.info(
        "ai model listing completed",
        extra={"event": {"provider": provider, "model_count": len(models)}},
    )
    trace(f"AI model listing completed with {len(models)} model(s)", logger)
    return models
