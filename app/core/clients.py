from collections.abc import Callable
from functools import lru_cache
import logging
from typing import Any

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.core.config import (
    CONTENT_PAYLOAD_KEY,
    EMBEDDING_DIMENSION,
    METADATA_PAYLOAD_KEY,
    QDRANT_COLLECTION_NAME,
    QDRANT_DISTANCE,
    QDRANT_RECREATE_COLLECTION,
    QDRANT_URL,
)
from app.core.logging import get_logger, log_timing, trace

logger = get_logger(__name__)


class LazyResource:
    def __init__(self, factory: Callable[[], Any]):
        self._factory = factory

    def __getattr__(self, name: str) -> Any:
        return getattr(self._factory(), name)


def _qdrant_distance() -> Distance:
    try:
        return getattr(Distance, QDRANT_DISTANCE.upper())
    except AttributeError as exc:
        allowed = ", ".join(item.name.lower() for item in Distance)
        raise ValueError(
            f"Unsupported QDRANT_DISTANCE={QDRANT_DISTANCE!r}. Use one of: {allowed}."
        ) from exc


@lru_cache(maxsize=1)
def get_qdrant_vector_store() -> QdrantVectorStore:
    from app.ml.embeddings import embeddings

    trace("Qdrant vector store initialization started", logger)
    with log_timing(logger, "qdrant_vector_store_init", collection=QDRANT_COLLECTION_NAME):
        client = QdrantClient(url=QDRANT_URL)
        distance = _qdrant_distance()
        collection_exists = client.collection_exists(collection_name=QDRANT_COLLECTION_NAME)

        if QDRANT_RECREATE_COLLECTION and collection_exists:
            logger.warning(
                "qdrant collection recreate requested",
                extra={"event": {"collection": QDRANT_COLLECTION_NAME}},
            )
            trace("Qdrant collection recreate requested", logger, logging.WARNING)
            client.delete_collection(collection_name=QDRANT_COLLECTION_NAME)
            collection_exists = False

        if not collection_exists:
            logger.info(
                "qdrant collection creating",
                extra={"event": {"collection": QDRANT_COLLECTION_NAME, "dimension": EMBEDDING_DIMENSION}},
            )
            client.create_collection(
                collection_name=QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIMENSION, distance=distance),
            )

        store = QdrantVectorStore(
            client=client,
            collection_name=QDRANT_COLLECTION_NAME,
            embedding=embeddings,
            content_payload_key=CONTENT_PAYLOAD_KEY,
            metadata_payload_key=METADATA_PAYLOAD_KEY,
            distance=distance,
        )

    trace("Qdrant vector store initialization completed", logger)
    return store


def _groq_sdk_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    suffix = "/openai/v1"
    if base_url.endswith(suffix):
        return base_url[: -len(suffix)]

    return base_url


def _create_llm(config: dict):
    provider = config["provider"]
    logger.info(
        "llm initialization started",
        extra={"event": {"provider": provider, "model": config.get("model"), "base_url": config.get("base_url")}},
    )
    trace(f"LLM initialization started for {provider}", logger)

    if provider == "groq":
        from langchain_groq import ChatGroq

        llm_instance = ChatGroq(
            api_key=config["api_key"],
            model=config["model"],
            base_url=_groq_sdk_base_url(config["base_url"]),
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )
    elif provider in {"openai", "vllm"}:
        from langchain_openai import ChatOpenAI

        llm_instance = ChatOpenAI(
            api_key=config["api_key"],
            model=config["model"],
            base_url=config["base_url"],
            max_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm_instance = ChatGoogleGenerativeAI(
            google_api_key=config["api_key"],
            model=config["model"],
            max_output_tokens=config["max_tokens"],
            temperature=config["temperature"],
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    logger.info("llm initialization completed", extra={"event": {"provider": provider, "model": config["model"]}})
    trace(f"LLM initialization completed for {provider}", logger)
    return llm_instance


@lru_cache(maxsize=1)
def get_llm():
    from app.services.ai_settings import get_active_llm_config

    config = get_active_llm_config()
    return _create_llm(config)


def get_llm_for_model(model: str | None = None):
    if not model or not model.strip():
        return get_llm()

    from app.services.ai_settings import get_active_llm_config

    config = get_active_llm_config()
    config["model"] = model.strip()
    return _create_llm(config)


qdrant_vs = LazyResource(get_qdrant_vector_store)
llm = LazyResource(get_llm)
