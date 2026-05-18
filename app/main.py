from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request

from app.api.v1.routes import router
from app.core.config import API_V1_PREFIX, APP_NAME
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger, log_timing, trace
from app.services.document_registry import migrate_json_registry
from app.services.ai_settings import seed_ai_settings
from app.services.prompts import seed_default_prompts

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    trace("API startup started", logger)
    with log_timing(logger, "api_startup"):
        init_db()
        seed_ai_settings()
        seed_default_prompts()
        migrated = migrate_json_registry()
        logger.info("legacy registry migration checked", extra={"event": {"migrated": migrated}})
    trace("API startup completed", logger)
    yield
    trace("API shutdown started", logger)
    logger.info("api shutdown completed")

app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    trace(f"API request {request.method} {path}", logger)
    logger.info(
        "api request started",
        extra={"event": {"method": request.method, "path": path}},
    )
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "api request failed",
            extra={"event": {"method": request.method, "path": path, "elapsed_ms": elapsed_ms}},
        )
        trace(f"API request failed {request.method} {path}", logger)
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "api request completed",
        extra={
            "event": {
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
            }
        },
    )
    trace(f"API response {request.method} {path} {response.status_code}", logger)
    return response


app.include_router(router, prefix=API_V1_PREFIX)
