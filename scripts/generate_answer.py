try:
    from scripts._bootstrap import PROJECT_ROOT  # noqa: F401
except ModuleNotFoundError:
    from _bootstrap import PROJECT_ROOT  # noqa: F401

from app.services.generation import answer_question
from app.core.logging import get_logger, trace

logger = get_logger(__name__)


def main() -> None:
    query = input("Ask a question: ").strip()
    trace("CLI answer generation started", logger)
    result = answer_question(query)

    trace("Answer:", logger)
    trace(result.answer, logger)

    if result.sources:
        trace("Sources:", logger)
        for index, source in enumerate(result.sources, start=1):
            trace(f"[{index}] {source['source']} score={source['score']}", logger)
    trace("CLI answer generation completed", logger)


if __name__ == "__main__":
    main()
