## 1. Rate limiting e idempotencia

- [x] 1.1 Agregar `slowapi` como rate limiter del orquestador, usando almacenamiento Redis configurable y fallback en memoria.
- [x] 1.2 Crear `orchestrator/idempotency.py` con get/set de respuesta cacheada por `Idempotency-Key`.
- [x] 1.3 Parámetros por env: `RATE_LIMIT_WRITE_LIMIT`, `RATE_LIMIT_STORAGE_URI`, `IDEMPOTENCY_TTL_SECONDS`.

## 2. Integración en orchestrator

- [x] 2.1 Registrar el limiter y aplicarlo a endpoints POST del orquestador.
- [x] 2.2 En `POST /negotiate`, devolver la respuesta cacheada si el `Idempotency-Key` ya existe; si no, ejecutar y cachear.

## 3. Cliente (dashboard)

- [x] 3.1 La página "🚀 New Negotiation" genera y envía un `Idempotency-Key` (uuid) por envío.

## 4. Verificación

- [x] 4.1 Check runnable de la clave de idempotencia con un doble de Redis en memoria.
- [x] 4.2 `py_compile` de los módulos tocados.
- [x] 4.3 `openspec validate add-api-hardening --strict`.
