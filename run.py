from __future__ import annotations

import argparse
import hashlib
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
from pathlib import Path

from app.core.logging import get_logger, log_timing, trace

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_MARKER = VENV_DIR / ".requirements.sha256"
ENV_FILE = PROJECT_ROOT / ".env"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_PACKAGE_JSON = FRONTEND_DIR / "package.json"
FRONTEND_PACKAGE_LOCK = FRONTEND_DIR / "package-lock.json"
FRONTEND_NODE_MODULES = FRONTEND_DIR / "node_modules"
FRONTEND_REQUIREMENTS_MARKER = FRONTEND_NODE_MODULES / ".mindmesh.deps.sha256"

logger = get_logger(__name__)


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"

    return VENV_DIR / "bin" / "python"


def _run(
    command: list[str],
    env: dict[str, str] | None = None,
    cwd: Path = PROJECT_ROOT,
) -> None:
    logger.info(
        "runner subprocess started",
        extra={"event": {"command": command, "cwd": str(cwd)}},
    )
    with log_timing(logger, "runner_subprocess"):
        subprocess.run(command, cwd=cwd, env=env, check=True)


def _requirements_hash() -> str:
    if not REQUIREMENTS_FILE.exists():
        return ""

    return hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()


def _frontend_requirements_hash() -> str:
    digest = hashlib.sha256()
    for path in (FRONTEND_PACKAGE_JSON, FRONTEND_PACKAGE_LOCK):
        if path.exists():
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())

    return digest.hexdigest()


def _npm_command() -> str:
    if os.name == "nt":
        return "npm.cmd"

    return "npm"


def _dotenv_value(name: str) -> str | None:
    if not ENV_FILE.exists():
        return None

    prefix = f"{name}="
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or not stripped.startswith(prefix):
            continue

        return stripped.removeprefix(prefix).strip().strip("'\"")

    return None


def _setting(name: str, default: str) -> str:
    return os.getenv(name) or _dotenv_value(name) or default


def ensure_virtualenv() -> Path:
    python = _venv_python()
    if python.exists():
        logger.debug("virtual environment already exists", extra={"event": {"python": str(python)}})
        return python

    trace("Creating virtual environment in .venv", logger)
    venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    return python


def ensure_requirements(python: Path) -> None:
    if not REQUIREMENTS_FILE.exists():
        return

    current_hash = _requirements_hash()
    previous_hash = (
        REQUIREMENTS_MARKER.read_text(encoding="utf-8").strip()
        if REQUIREMENTS_MARKER.exists()
        else ""
    )

    if current_hash == previous_hash:
        logger.debug("requirements are already installed")
        return

    trace("Installing project requirements", logger)
    _run([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)])
    REQUIREMENTS_MARKER.write_text(current_hash, encoding="utf-8")
    logger.info("requirements marker updated", extra={"event": {"path": str(REQUIREMENTS_MARKER)}})


def ensure_frontend_requirements() -> None:
    if not FRONTEND_PACKAGE_JSON.exists():
        raise RuntimeError("React frontend package.json was not found.")

    current_hash = _frontend_requirements_hash()
    previous_hash = (
        FRONTEND_REQUIREMENTS_MARKER.read_text(encoding="utf-8").strip()
        if FRONTEND_REQUIREMENTS_MARKER.exists()
        else ""
    )

    if FRONTEND_NODE_MODULES.exists() and current_hash == previous_hash:
        logger.debug("frontend requirements are already installed")
        return

    trace("Installing React frontend requirements", logger)
    _run([_npm_command(), "install"], cwd=FRONTEND_DIR)
    FRONTEND_REQUIREMENTS_MARKER.write_text(current_hash, encoding="utf-8")
    logger.info(
        "frontend requirements marker updated",
        extra={"event": {"path": str(FRONTEND_REQUIREMENTS_MARKER)}},
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MM POC RAG project.")
    parser.add_argument("--host", default=_setting("APP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(_setting("APP_PORT", "8000")))
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Start the FastAPI backend and Streamlit frontend together.",
    )
    parser.add_argument(
        "--fe",
        action="store_true",
        help="Start the FastAPI backend and React frontend together.",
    )
    parser.add_argument(
        "--ui-host",
        default=_setting("STREAMLIT_HOST", "127.0.0.1"),
        help="Host for the Streamlit frontend.",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        default=int(_setting("STREAMLIT_PORT", "8501")),
        help="Port for the Streamlit frontend.",
    )
    parser.add_argument(
        "--fe-host",
        default=_setting("FRONTEND_HOST", "127.0.0.1"),
        help="Host for the React frontend.",
    )
    parser.add_argument(
        "--fe-port",
        type=int,
        default=int(_setting("FRONTEND_PORT", "5173")),
        help="Port for the React frontend.",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Start without uvicorn reload mode.",
    )
    parser.add_argument(
        "--strict-port",
        action="store_true",
        help="Fail instead of using the next available port.",
    )
    parser.add_argument(
        "--startup-timeout",
        type=int,
        default=int(_setting("API_STARTUP_TIMEOUT_SECONDS", "120")),
        help="Seconds to wait for the API to become ready before starting a UI.",
    )
    return parser.parse_args()


def _socket_family(host: str) -> socket.AddressFamily:
    if ":" in host:
        return socket.AF_INET6

    return socket.AF_INET


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(_socket_family(host), socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False

    return True


def find_available_port(host: str, preferred_port: int, strict: bool) -> int:
    if _can_bind(host, preferred_port):
        return preferred_port

    if strict:
        raise RuntimeError(f"Port {preferred_port} is not available on {host}.")

    for port in range(preferred_port + 1, preferred_port + 101):
        if _can_bind(host, port):
            trace(f"Port {preferred_port} is unavailable. Using port {port} instead", logger)
            return port

    raise RuntimeError(
        f"No available port found on {host} from {preferred_port} to {preferred_port + 100}."
    )


def _api_command(
    python: Path,
    host: str,
    port: int,
    reload_enabled: bool,
) -> list[str]:
    command = [
        str(python),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload_enabled:
        command.append("--reload")

    return command


def _docs_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _wait_for_api(
    api_base_url: str,
    *,
    process: subprocess.Popen | None = None,
    timeout_seconds: int = 120,
) -> None:
    trace("Waiting for API readiness", logger)
    deadline = time.time() + timeout_seconds
    url = f"{api_base_url}/health"

    while time.time() < deadline:
        if process and process.poll() is not None:
            raise RuntimeError(
                f"API process exited before readiness with code {process.returncode}. "
                "Check logs/errors.log for startup failures."
            )

        try:
            with urllib.request.urlopen(url, timeout=2):
                trace("API readiness check completed", logger)
                return
        except urllib.error.URLError:
            logger.debug("api readiness check retrying", extra={"event": {"url": url}})
            time.sleep(0.5)

    raise RuntimeError(
        f"API did not become ready at {url} within {timeout_seconds} seconds. "
        "Check logs/errors.log for startup failures."
    )


def run_api(python: Path, args: argparse.Namespace, port: int) -> None:
    command = _api_command(
        python=python,
        host=args.host,
        port=port,
        reload_enabled=not args.no_reload,
    )
    trace(f"Starting API at http://{_docs_host(args.host)}:{port}/docs", logger)
    _run(command)


def run_with_ui(python: Path, args: argparse.Namespace, api_port: int) -> None:
    api_host = _docs_host(args.host)
    ui_port = find_available_port(args.ui_host, args.ui_port, args.strict_port)
    api_base_url = f"http://{api_host}:{api_port}/api/v1"
    env = os.environ.copy()
    env["STREAMLIT_API_BASE_URL"] = api_base_url

    api_process = subprocess.Popen(
        _api_command(
            python=python,
            host=args.host,
            port=api_port,
            reload_enabled=False,
        ),
        cwd=PROJECT_ROOT,
        env=env,
    )

    try:
        _wait_for_api(
            api_base_url,
            process=api_process,
            timeout_seconds=args.startup_timeout,
        )
        trace(f"Starting Streamlit at http://{_docs_host(args.ui_host)}:{ui_port}", logger)
        trace(f"Streamlit API base URL: {api_base_url}", logger)
        _run(
            [
                str(python),
                "-m",
                "streamlit",
                "run",
                str(PROJECT_ROOT / "legacy" / "streamlit_app.py"),
                "--server.address",
                args.ui_host,
                "--server.port",
                str(ui_port),
            ],
            env=env,
        )
    finally:
        trace("Stopping API process", logger)
        api_process.terminate()
        try:
            api_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("api process did not stop gracefully; killing process")
            api_process.kill()


def run_with_frontend(python: Path, args: argparse.Namespace, api_port: int) -> None:
    ensure_frontend_requirements()

    api_host = _docs_host(args.host)
    fe_port = find_available_port(args.fe_host, args.fe_port, args.strict_port)
    api_origin = f"http://{api_host}:{api_port}"
    api_base_url = f"{api_origin}/api/v1"
    env = os.environ.copy()
    env["VITE_API_BASE_URL"] = "/api/v1"
    env["VITE_API_PROXY_TARGET"] = api_origin

    api_process = subprocess.Popen(
        _api_command(
            python=python,
            host=args.host,
            port=api_port,
            reload_enabled=False,
        ),
        cwd=PROJECT_ROOT,
        env=env,
    )

    try:
        _wait_for_api(
            api_base_url,
            process=api_process,
            timeout_seconds=args.startup_timeout,
        )
        trace(f"Starting React frontend at http://{_docs_host(args.fe_host)}:{fe_port}", logger)
        trace(f"React frontend API proxy target: {api_origin}", logger)
        _run(
            [
                _npm_command(),
                "run",
                "dev",
                "--",
                "--host",
                args.fe_host,
                "--port",
                str(fe_port),
            ],
            cwd=FRONTEND_DIR,
            env=env,
        )
    finally:
        trace("Stopping API process", logger)
        api_process.terminate()
        try:
            api_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("api process did not stop gracefully; killing process")
            api_process.kill()


def main() -> None:
    trace("Project runner started", logger)
    args = parse_args()
    if args.ui and args.fe:
        raise RuntimeError("Choose either --ui for Streamlit or --fe for React, not both.")

    python = ensure_virtualenv()
    ensure_requirements(python)

    port = find_available_port(args.host, args.port, args.strict_port)
    if args.ui:
        run_with_ui(python, args, api_port=port)
        return
    if args.fe:
        run_with_frontend(python, args, api_port=port)
        return

    run_api(python, args, port=port)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode)
    except RuntimeError as exc:
        logger.exception("project runner failed")
        trace(f"ERROR: {exc}", logger)
        sys.exit(1)
