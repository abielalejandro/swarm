## 1. Módulo compartido

- [x] 1.1 Crear `orchestrator/middleware.py` con un rate limiter (ventana fija por IP sobre Redis) y un helper de idempotencia (get/set de respuesta cacheada por `Idempotency-Key`).
- [x] 1.2 Parámetros por env: `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW_SECONDS`, `IDEMPOTENCY_TTL_SECONDS`.
- [x] 1.3 Degradación segura: si Redis falla, permitir la petición (log de warning).

## 2. Integración en orchestrator

- [x] 2.1 Registrar el rate limiter como middleware, activo solo en métodos de escritura (POST).
- [x] 2.2 En `POST /negotiate`, devolver la respuesta cacheada si el `Idempotency-Key` ya existe; si no, ejecutar y cachear.

## 3. Cliente (dashboard)

- [x] 3.1 La página "🚀 New Negotiation" genera y envía un `Idempotency-Key` (uuid) por envío.

## 4. Verificación

- [x] 4.1 Check runnable del rate limiter y de la clave de idempotencia con un doble de Redis en memoria.
- [x] 4.2 `py_compile` de los módulos tocados.
- [x] 4.3 `openspec validate add-api-hardening --strict`.
