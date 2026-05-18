try:
    from scripts._bootstrap import PROJECT_ROOT  # noqa: F401
except ModuleNotFoundError:
    from _bootstrap import PROJECT_ROOT  # noqa: F401

import uvicorn

from app.core.logging import get_logger, trace

logger = get_logger(__name__)


def main() -> None:
    trace("Uvicorn development server starting", logger)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
