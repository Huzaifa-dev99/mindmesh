import base64
import hashlib
import hmac
import re
import secrets

from psycopg import Connection

from app.core.database import connect, ensure_database
from app.core.logging import get_logger, trace
from app.core.serialization import serialize_datetime

logger = get_logger(__name__)

DEFAULT_PROFILE = {
    "name": "Local user",
    "avatar": "https://api.dicebear.com/9.x/shapes/svg?seed=mindmesh&backgroundColor=16091f",
}
PIN_ITERATIONS = 210000
PIN_PATTERN = re.compile(r"^\d{4}$")


def _validate_pin(pin: str) -> str:
    value = str(pin or "").strip()
    if not PIN_PATTERN.fullmatch(value):
        raise ValueError("PIN must be exactly 4 digits.")
    return value


def _new_salt() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(24)).decode("ascii")


def _pin_hash(pin: str, salt: str, iterations: int) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        salt.encode("ascii"),
        iterations,
    )
    return base64.urlsafe_b64encode(digest).decode("ascii")


def _row_to_state(row: dict) -> dict:
    return {
        "profile": {
            "name": row["name"],
            "avatar": row["avatar_url"],
        },
        "has_pin": bool(row.get("pin_hash")),
        "created_at": serialize_datetime(row.get("created_at")),
        "updated_at": serialize_datetime(row.get("updated_at")),
    }


def _ensure_user(conn: Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO rag.users (id, name, avatar_url)
            VALUES (TRUE, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (DEFAULT_PROFILE["name"], DEFAULT_PROFILE["avatar"]),
        )


def seed_user(conn: Connection | None = None) -> None:
    if conn is None:
        ensure_database()
        with connect() as db_conn:
            _ensure_user(db_conn)
            db_conn.commit()
    else:
        _ensure_user(conn)
    logger.debug("user seed checked")


def get_user_state() -> dict:
    trace("User state loading started", logger)
    seed_user()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM rag.users WHERE id = TRUE")
            state = _row_to_state(cursor.fetchone())

    trace("User state loading completed", logger)
    return state


def set_user_pin(pin: str) -> dict:
    trace("User PIN update started", logger)
    value = _validate_pin(pin)
    salt = _new_salt()
    pin_hash = _pin_hash(value, salt, PIN_ITERATIONS)

    seed_user()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.users
                SET pin_hash = %s,
                    pin_salt = %s,
                    pin_iterations = %s,
                    updated_at = NOW()
                WHERE id = TRUE
                RETURNING *
                """,
                (pin_hash, salt, PIN_ITERATIONS),
            )
            state = _row_to_state(cursor.fetchone())
        conn.commit()

    logger.info("user pin updated")
    trace("User PIN update completed", logger)
    return state


def verify_user_pin(pin: str) -> dict:
    trace("User PIN verification started", logger)
    value = _validate_pin(pin)
    seed_user()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM rag.users WHERE id = TRUE")
            row = cursor.fetchone()

    if not row or not row.get("pin_hash") or not row.get("pin_salt"):
        raise ValueError("No PIN has been configured.")

    expected = _pin_hash(value, row["pin_salt"], int(row["pin_iterations"] or PIN_ITERATIONS))
    if not hmac.compare_digest(expected, row["pin_hash"]):
        raise ValueError("Incorrect PIN.")

    logger.info("user pin verified")
    trace("User PIN verification completed", logger)
    return _row_to_state(row)


def update_user_profile(*, name: str, avatar: str) -> dict:
    trace("User profile update started", logger)
    cleaned_name = str(name or "").strip()
    cleaned_avatar = str(avatar or "").strip()
    if not cleaned_name:
        raise ValueError("Name cannot be empty.")
    if not cleaned_avatar:
        raise ValueError("Avatar URL cannot be empty.")

    seed_user()
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE rag.users
                SET name = %s,
                    avatar_url = %s,
                    updated_at = NOW()
                WHERE id = TRUE
                RETURNING *
                """,
                (cleaned_name, cleaned_avatar),
            )
            state = _row_to_state(cursor.fetchone())
        conn.commit()

    logger.info("user profile updated")
    trace("User profile update completed", logger)
    return state
