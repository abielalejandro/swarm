## Why

El orquestador expone endpoints de escritura sin autenticación: cualquiera con acceso
de red puede lanzar negociaciones, cancelarlas o resetear el sistema. Se necesita
identidad por usuario para saber quién actúa y poder cerrar el acceso.

## What Changes

- **Login por usuario/contraseña** contra una tabla `users` en el PostgreSQL existente
  (DB `swarm_audit`); contraseñas hasheadas con **bcrypt** (`passlib`).
- **Sesión con token PASETO v4.local** (cifrado+firmado con clave simétrica por env),
  entregado en una **cookie segura** (`HttpOnly`, `Secure`, `SameSite=Lax`, con expiración).
- Endpoints de auth: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- **Protección** de los endpoints de escritura (`POST /negotiate`, `/session/{id}/cancel`,
  `/reset`) vía dependencia que valida la cookie; sin sesión válida → `401`. Los GET
  quedan abiertos (el dashboard hace polling de solo lectura).
- **Alta de usuarios por seed/script** (`orchestrator/seed_user.py`), sin registro público.
- Dependencias nuevas en el orquestador: `pyseto`, `passlib[bcrypt]`, `psycopg2-binary`.

## Capabilities

- **New:** `user-auth` — autenticación por usuario con sesión PASETO en cookie segura.

## Impact

- Afecta: `orchestrator/orchestrator.py` (endpoints de auth + dependencia en writes),
  nuevos `orchestrator/auth.py` y `orchestrator/seed_user.py`,
  `orchestrator/requirements.txt`, `.env.example` (claves nuevas), y `docker-compose.yml`
  (env del orquestador). Documentación operativa en el README.
- No cambia el contrato de `/negotiate` salvo el requisito de sesión.
- Degradación: sin la tabla `users` o sin `PASETO_KEY`, el login falla de forma clara;
  el servicio no expone writes sin auth configurada.
