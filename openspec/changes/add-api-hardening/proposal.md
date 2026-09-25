## Why

El orquestador expone endpoints de escritura (`POST /negotiate`, `/session/{id}/cancel`,
`/reset`) sin protección: hoy solo hay CORS abierto. Una negociación arranca trabajo
pesado (rondas, llamadas LLM). Un doble-click en el dashboard o un reintento de red
crea sesiones duplicadas, y no hay límite de tasa que frene ráfagas o abuso.

## What Changes

- **Rate limiting** en los endpoints de escritura del orquestador: ventana fija por IP
  usando el Redis ya existente (`INCR`+`EXPIRE`); al exceder, responde `429` con
  `Retry-After`. Configurable por env; no aplica a GET (el dashboard hace polling).
- **Idempotencia** en `POST /negotiate`: si el cliente envía el header `Idempotency-Key`,
  la respuesta se cachea en Redis con TTL y una repetición con la misma clave devuelve
  la respuesta original sin crear otra sesión. Sin el header, comportamiento actual.
- Módulo compartido `orchestrator/middleware.py` reutilizando `round_manager.redis`.
- El dashboard ("🚀 New Negotiation") envía un `Idempotency-Key` por envío de formulario.

## Capabilities

- **New:** `api-hardening` — rate limiting e idempotencia para los endpoints de
  escritura del orquestador.

## Impact

- Afecta: `orchestrator/orchestrator.py` (registrar middleware + idempotencia en
  `/negotiate`), nuevo `orchestrator/middleware.py`, `dashboard/app.py` (enviar header).
- No cambia el contrato de respuesta ni la orquestación. Degrada de forma segura si
  Redis no responde (permite la petición; no bloquea el servicio).
