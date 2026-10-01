## Why

El servicio Psychologist ya puede interrogar agentes, pero la funcionalidad no es
accesible para un usuario desde el dashboard. Hoy requiere invocar endpoints a mano
y, desde el orquestador, solo existe una ruta asociada a una sesión.

Un usuario necesita disparar interrogatorios tanto en contexto de una negociación
existente como fuera de una negociación, para explorar el perfil de un agente o
auditar su comportamiento sin crear una sesión artificial.

## What Changes

- Nueva pantalla en el dashboard Streamlit para ejecutar interrogatorios.
- El usuario puede elegir entre:
  - interrogar un agente dentro de una sesión existente;
  - interrogar un agente directamente, sin sesión.
- El formulario permite elegir agente y estilo de interrogatorio.
- El resultado muestra `truth_score`, recomendación, preguntas, respuestas y flags.
- El orquestador expone una ruta directa `POST /interrogate` y protege las rutas de
  interrogación con sesión de usuario.

## Capabilities

- **New:** `interrogation-launcher-ui` — pantalla y API para lanzar interrogatorios
  del Psychologist desde el dashboard, con o sin sesión de negociación.

## Impact

- Afecta: `dashboard/app.py`, `orchestrator/orchestrator.py`,
  `orchestrator/round_manager.py`.
- No cambia el contrato interno del servicio `psychologist`.
