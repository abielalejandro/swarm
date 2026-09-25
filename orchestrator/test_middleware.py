"""Check de middleware: rate limit (ventana fija) e idempotencia con Redis en memoria.
Correr: python3 test_middleware.py"""
import sys, types

# Stub de starlette para importar el módulo sin instalarlo (en runtime viene con FastAPI).
_base = types.ModuleType("starlette.middleware.base")
_base.BaseHTTPMiddleware = object
_resp = types.ModuleType("starlette.responses")
_resp.JSONResponse = object
_mw = types.ModuleType("starlette.middleware")
sys.modules.setdefault("starlette", types.ModuleType("starlette"))
sys.modules.setdefault("starlette.middleware", _mw)
sys.modules.setdefault("starlette.middleware.base", _base)
sys.modules.setdefault("starlette.responses", _resp)

import middleware as mw


class FakeRedis:
    """Doble mínimo de Redis con INCR/EXPIRE/TTL/GET/SET (sin expiración real)."""
    def __init__(self):
        self.store = {}
        self.ttls = {}
    def incr(self, k):
        self.store[k] = int(self.store.get(k, 0)) + 1
        return self.store[k]
    def expire(self, k, s):
        self.ttls[k] = s
    def ttl(self, k):
        return self.ttls.get(k, -1)
    def get(self, k):
        return self.store.get(k)
    def set(self, k, v, ex=None):
        self.store[k] = v
        if ex:
            self.ttls[k] = ex


# --- Rate limit: permite hasta MAX, luego 429 ---
mw.RATE_LIMIT_MAX = 3
mw.RATE_LIMIT_WINDOW_SECONDS = 60
r = FakeRedis()
ip = "1.2.3.4"
results = [mw.check_rate_limit(r, ip)[0] for _ in range(4)]
assert results == [True, True, True, False], results
allowed, retry = mw.check_rate_limit(r, ip)
assert allowed is False and retry > 0, (allowed, retry)

# --- Fail-open: Redis roto -> permite ---
class Broken:
    def incr(self, k): raise RuntimeError("down")
assert mw.check_rate_limit(Broken(), ip) == (True, 0)

# --- Idempotencia: set/get round-trip; sin clave -> None ---
r2 = FakeRedis()
assert mw.idempotency_get(r2, "k1") is None
mw.idempotency_set(r2, "k1", {"session_id": "s1", "status": "created"})
assert mw.idempotency_get(r2, "k1") == {"session_id": "s1", "status": "created"}
assert mw.idempotency_get(r2, None) is None          # sin header -> no cache
mw.idempotency_set(r2, None, {"x": 1})               # no-op, no explota
assert mw.idempotency_get(Broken(), "k1") is None    # fail-open lectura

print("OK: middleware (rate limit + idempotencia)")
