## 1. Módulo de auth

- [x] 1.1 `orchestrator/auth.py`: conexión a Postgres, `verify_user(username, password)` con bcrypt, emisión/validación de token PASETO v4.local (claim de subject + expiración).
- [x] 1.2 Helper de cookie: nombre, `HttpOnly`, `Secure`, `SameSite=Lax`, `max_age`.
- [x] 1.3 Dependencia `require_user(request)` que lee la cookie, valida el PASETO y devuelve el usuario; `401` si falta o es inválido/expirado.
- [x] 1.4 Config por env: `PASETO_KEY`, `SESSION_TTL_SECONDS`, `COOKIE_SECURE`, credenciales Postgres.

## 2. Endpoints en orchestrator

- [x] 2.1 `POST /auth/login`: valida credenciales, setea la cookie con el PASETO.
- [x] 2.2 `POST /auth/logout`: borra la cookie.
- [x] 2.3 `GET /auth/me`: devuelve el usuario de la sesión actual.
- [x] 2.4 Proteger `POST /negotiate`, `/session/{id}/cancel`, `/reset` con `Depends(require_user)`.

## 3. Usuarios y esquema

- [x] 3.1 Crear tabla `users` (id, username único, password_hash, created_at) si no existe.
- [x] 3.2 `orchestrator/seed_user.py`: crea/actualiza un usuario desde variables de entorno.

## 4. Cliente (dashboard)

- [x] 4.1 Página/formulario de login que hace `POST /auth/login` con cookies habilitadas y reusa el cliente httpx con `cookies`.

## 5. Config y deps

- [x] 5.1 Agregar `pyseto`, `passlib[bcrypt]`, `psycopg2-binary` a `orchestrator/requirements.txt`.
- [x] 5.2 `.env.example` y env del orquestador en `docker-compose.yml` con las claves nuevas.

## 6. Verificación

- [x] 6.1 Check runnable: round-trip de emisión/validación PASETO (válido, expirado, manipulado) y verificación de contraseña bcrypt.
- [x] 6.2 `py_compile` de los módulos tocados.
- [x] 6.3 `openspec validate add-user-auth --strict`.
