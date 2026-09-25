"""Check Idempotency-Key helper behavior. Run: python3 test_idempotency.py"""

from idempotency import idempotency_get, idempotency_set


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.ttls = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            self.ttls[key] = ex


class BrokenRedis:
    def get(self, key):
        raise RuntimeError("down")

    def set(self, key, value, ex=None):
        raise RuntimeError("down")


r = FakeRedis()
assert idempotency_get(r, "k1") is None
idempotency_set(r, "k1", {"session_id": "s1", "status": "active"})
assert idempotency_get(r, "k1") == {"session_id": "s1", "status": "active"}

assert idempotency_get(r, None) is None
idempotency_set(r, None, {"x": 1})
assert idempotency_get(BrokenRedis(), "k1") is None
idempotency_set(BrokenRedis(), "k1", {"x": 1})

print("OK: idempotency")
