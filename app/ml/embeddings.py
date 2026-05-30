from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import EMBEDDING_MODEL_NAME, EMBEDDING_MODEL_PATH
from app.core.logging import get_logger, log_timing, trace

logger = get_logger(__name__)

MODEL_ALLOW_PATTERNS = (
    "*.json",
    "*.txt",
    "*.safetensors",
    "1_Pooling/*",
)


def _ensure_embedding_model() -> str:
    trace("Embedding model availability check started", logger)
    EMBEDDING_MODEL_PATH.mkdir(parents=True, exist_ok=True)

    required_paths = (
        EMBEDDING_MODEL_PATH / "config.json",
        EMBEDDING_MODEL_PATH / "modules.json",
        EMBEDDING_MODEL_PATH / "1_Pooling" / "config.json",
    )
    has_weights = any(
        (EMBEDDING_MODEL_PATH / filename).exists()
        for filename in ("model.safetensors", "pytorch_model.bin")
    )
    has_tokenizer = any(
        (EMBEDDING_MODEL_PATH / filename).exists()
        for filename in ("tokenizer.json", "vocab.txt")
    )

    if not all(path.exists() for path in required_paths) or not has_weights or not has_tokenizer:
        logger.warning(
            "embedding model files missing; downloading snapshot",
            extra={"event": {"model": EMBEDDING_MODEL_NAME, "path": str(EMBEDDING_MODEL_PATH)}},
        )
        trace("Embedding model download started", logger)
        with log_timing(logger, "embedding_model_download", model=EMBEDDING_MODEL_NAME):
            snapshot_download(
                repo_id=EMBEDDING_MODEL_NAME,
                local_dir=str(EMBEDDING_MODEL_PATH),
                allow_patterns=MODEL_ALLOW_PATTERNS,
            )

    logger.info(
        "embedding model ready",
        extra={"event": {"model": EMBEDDING_MODEL_NAME, "path": str(EMBEDDING_MODEL_PATH)}},
    )
    trace("Embedding model availability check completed", logger)
    return str(EMBEDDING_MODEL_PATH)


trace("Embedding client initialization started", logger)
embeddings = HuggingFaceEmbeddings(model_name=_ensure_embedding_model())
trace("Embedding client initialization completed", logger)
