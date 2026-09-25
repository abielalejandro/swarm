"""Check de auth: round-trip PASETO (válido/expirado/manipulado) y bcrypt.
Correr: python3 test_auth.py   (requiere pyseto y passlib; no toca Postgres)"""
import os
os.environ["PASETO_KEY"] = "clave-de-prueba-para-el-check-0123456789"

import auth

# --- PASETO: token válido devuelve el sub ---
tok = auth.issue_token("alice", ttl_seconds=60)
assert auth.read_token(tok) == "alice", "token válido"

# --- Token vacío/None -> None ---
assert auth.read_token(None) is None
assert auth.read_token("") is None

# --- Token expirado -> None ---
expired = auth.issue_token("bob", ttl_seconds=-1)
assert auth.read_token(expired) is None, "token expirado"

# --- Token manipulado -> None ---
assert auth.read_token(tok[:-3] + "xyz") is None, "token manipulado"

# --- Clave distinta no valida el token de otra clave ---
tok_alice = auth.issue_token("alice", ttl_seconds=60)
auth.PASETO_KEY = "otra-clave-totalmente-distinta-987654321"
assert auth.read_token(tok_alice) is None, "clave distinta"
auth.PASETO_KEY = "clave-de-prueba-para-el-check-0123456789"

# --- bcrypt: hash verifica correcto e incorrecto ---
from passlib.hash import bcrypt
h = bcrypt.hash("s3cr3t")
assert bcrypt.verify("s3cr3t", h) is True
assert bcrypt.verify("wrong", h) is False

# --- Cookie Secure dinámico: true/false fuerzan; auto usa el scheme ---
class _FakeReq:
    def __init__(self, scheme):
        self.url = type("U", (), {"scheme": scheme})()

auth.COOKIE_SECURE = "false"
assert auth._resolve_secure(_FakeReq("https")) is False, "false fuerza"
auth.COOKIE_SECURE = "true"
assert auth._resolve_secure(_FakeReq("http")) is True, "true fuerza"
auth.COOKIE_SECURE = "auto"
assert auth._resolve_secure(_FakeReq("https")) is True, "auto+https"
assert auth._resolve_secure(_FakeReq("http")) is False, "auto+http"
assert auth._resolve_secure(None) is False, "auto sin request"

print("OK: auth (PASETO v4.local + bcrypt + cookie secure dinámico)")
