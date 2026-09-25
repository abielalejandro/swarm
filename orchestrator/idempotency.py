"""Small Redis-backed helpers for Idempotency-Key responses."""

import json
import logging
import os

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_SECONDS = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "86400"))


def idempotency_get(redis_client, key):
    if not key:
        return None
    try:
        raw = redis_client.get(f"idempotency:{key}")
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Idempotency get skipped after Redis error: {e}")
        return None


def idempotency_set(redis_client, key, response):
    if not key:
        return
    try:
        redis_client.set(
            f"idempotency:{key}",
            json.dumps(response),
            ex=IDEMPOTENCY_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning(f"Idempotency set skipped after Redis error: {e}")
