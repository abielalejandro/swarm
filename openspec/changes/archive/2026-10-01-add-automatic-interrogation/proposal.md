## Why

El Psychologist ya puede interrogar agentes manualmente, pero el ciclo normal de
negociación no lo usa. Eso deja sin auditar los momentos donde más valor aporta:
cuando la negociación se estanca o cuando un agente rechaza propuestas de forma
repetida.

## What Changes

- El orquestador dispara interrogatorios automáticos bajo condiciones acotadas:
  - cuando una sesión entra en deadlock;
  - cuando un agente acumula rechazos repetidos dentro de una ronda.
- Los resultados se guardan en Redis asociados a la sesión y la ronda.
- El dashboard muestra las interrogaciones automáticas dentro del detalle de sesión.
- La funcionalidad queda controlada por variables de entorno y falla en modo
  fail-open: un error del Psychologist no detiene la negociación.

## Capabilities

- **New:** `automatic-interrogation` — integración automática del Psychologist en
  el ciclo de negociación para deadlocks y rechazo repetido.

## Impact

- Afecta: `orchestrator/round_manager.py`, `orchestrator/orchestrator.py`,
  `dashboard/app.py`, `.env.example`, `docker-compose.yml`.
- No cambia el contrato público de `POST /negotiate`.
- No cambia el servicio `psychologist`.
