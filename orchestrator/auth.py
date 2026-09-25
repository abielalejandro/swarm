"""
Autenticación por usuario: verificación bcrypt contra Postgres y sesión PASETO v4.local
en cookie segura.

Imports de pyseto/psycopg2 son diferidos para que el módulo (y su check) carguen sin
esas libs en entornos de desarrollo; en runtime vienen en requirements.
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Config por env
PASETO_KEY = os.getenv("PASETO_KEY", "")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "28800"))  # 8h
COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "swarm_session")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"


# ---------- PASETO ----------

def _paseto_key():
    import pyseto
    if not PASETO_KEY:
        raise RuntimeError("PASETO_KEY no configurada")
    # v4.local requiere 32 bytes de clave simétrica.
    raw = PASETO_KEY.encode("utf-8")[:32].ljust(32, b"0")
    return pyseto.Key.new(version=4, purpose="local", key=raw)


def issue_token(username, ttl_seconds=None):
    """Emite un PASETO v4.local con subject y expiración (ISO-8601 UTC)."""
    import pyseto
    ttl = SESSION_TTL_SECONDS if ttl_seconds is None else ttl_seconds
    exp = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    payload = {"sub": username, "exp": exp.isoformat()}
    token = pyseto.encode(_paseto_key(), json.dumps(payload).encode("utf-8"))
    return token.decode("utf-8") if isinstance(token, bytes) else token


def read_token(token):
    """Valida el PASETO y devuelve el username, o None si es inválido/expirado."""
    if not token:
        return None
    import pyseto
    try:
        decoded = pyseto.decode(_paseto_key(), token)
        payload = json.loads(decoded.payload)
        exp = datetime.fromisoformat(payload["exp"])
        if exp < datetime.now(timezone.utc):
            return None
        return payload.get("sub")
    except Exception as e:
        logger.warning(f"PASETO inválido: {e}")
        return None


# ---------- Postgres / usuarios ----------

def _pg_connect():
    import psycopg2
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "swarm_audit"),
        user=os.getenv("POSTGRES_USER", "swarm"),
        password=os.getenv("POSTGRES_PASSWORD", "swarm_secret"),
    )


def ensure_users_table():
    """Crea la tabla users si no existe."""
    conn = _pg_connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
    finally:
        conn.close()


def verify_user(username, password):
    """True si el usuario existe y la contraseña coincide con el hash bcrypt."""
    from passlib.hash import bcrypt
    conn = _pg_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return False
    try:
        return bcrypt.verify(password, row[0])
    except Exception:
        return False


def upsert_user(username, password):
    """Crea o actualiza un usuario con contraseña hasheada (para el seed)."""
    from passlib.hash import bcrypt
    ensure_users_table()
    pw_hash = bcrypt.hash(password)
    conn = _pg_connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash) VALUES (%s, %s)
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
                """,
                (username, pw_hash),
            )
    finally:
        conn.close()


# ---------- Cookie / dependencia FastAPI ----------

def set_session_cookie(response, token):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )


def clear_session_cookie(response):
    response.delete_cookie(key=COOKIE_NAME)


def require_user(request):
    """Dependencia FastAPI: exige cookie de sesión válida; devuelve el username o 401."""
    from fastapi import HTTPException
    token = request.cookies.get(COOKIE_NAME)
    username = read_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="No autenticado")
    return username
