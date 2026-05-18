try:
    from scripts._bootstrap import PROJECT_ROOT  # noqa: F401
except ModuleNotFoundError:
    from _bootstrap import PROJECT_ROOT  # noqa: F401

from app.services.indexing import index_documents
from app.core.logging import get_logger, trace

logger = get_logger(__name__)


def main() -> None:
    trace("CLI indexing started", logger)
    index_documents(show_progress=True)
    trace("CLI indexing completed", logger)


if __name__ == "__main__":
    main()
