"""
API hardening: rate limiting (ventana fija por IP) e idempotencia sobre Redis.

Reutiliza el cliente Redis existente (round_manager.redis, decode_responses=True).
Degrada de forma segura: si Redis falla, permite la petición y loguea un warning.
"""

import os
import json
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "30"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))


def _client_ip(request):
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(redis_client, ip):
    """
    Ventana fija: INCR de un contador por IP+ventana con EXPIRE en el primer hit.
    Devuelve (allowed: bool, retry_after: int). Fail-open si Redis no responde.
    ponytail: ventana fija (no sliding window); permite hasta 2x en el borde entre
    ventanas. Suficiente como freno de abuso; para precisión, migrar a sliding log.
    """
    try:
        window = RATE_LIMIT_WINDOW_SECONDS
        # Bucket alineado a la ventana para que el TTL y el conteo coincidan.
        import time
        bucket = int(time.time()) // window
        key = f"ratelimit:{ip}:{bucket}"
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, window)
        if count > RATE_LIMIT_MAX:
            ttl = redis_client.ttl(key)
            return False, (ttl if ttl and ttl > 0 else window)
        return True, 0
    except Exception as e:
        logger.warning(f"Rate limit check failed-open (Redis error): {e}")
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Aplica rate limiting solo a métodos de escritura (POST/PUT/PATCH/DELETE)."""

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app, redis_client):
        super().__init__(app)
        self.redis = redis_client

    async def dispatch(self, request, call_next):
        if request.method in self.WRITE_METHODS:
            allowed, retry_after = check_rate_limit(self.redis, _client_ip(request))
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)


def idempotency_get(redis_client, key):
    """Devuelve la respuesta cacheada (dict) para la clave, o None. Fail-open."""
    if not key:
        return None
    try:
        raw = redis_client.get(f"idempotency:{key}")
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Idempotency get failed-open (Redis error): {e}")
        return None


def idempotency_set(redis_client, key, response):
    """Cachea la respuesta (dict serializable) bajo la clave, con TTL. Fail-open."""
    if not key:
        return
    try:
        redis_client.set(
            f"idempotency:{key}",
            json.dumps(response),
            ex=IDEMPOTENCY_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning(f"Idempotency set failed-open (Redis error): {e}")
