## Why

Hoy, para probar la funcionalidad de negociación hay que llamar `POST /negotiate`
manualmente con `curl` (ver `NegociationExample.txt`). El dashboard Streamlit ya
monitorea sesiones, agentes y estado emocional, pero no permite **iniciar** una
negociación desde la UI. Un humano no técnico no puede lanzar una decisión sin
armar JSON a mano.

## What Changes

- Nueva página en el dashboard Streamlit ("🚀 New Negotiation") con un formulario
  para los campos que exige `POST /negotiate`: `goal` (requerido), `deadline`,
  `budget`, `agents` (multiselect sobre los agentes disponibles), `max_rounds`.
- Al enviar, el formulario hace `POST` al orquestador (`ORCHESTRATOR_URL`) y muestra
  el `session_id` y estado devueltos, con un acceso directo para seguir la sesión.
- Validación en la UI: `goal` no vacío antes de permitir el envío; errores de la API
  se muestran sin romper la página.

## Capabilities

- **New:** `negotiation-launcher-ui` — pantalla para componer y ejecutar una
  solicitud de negociación desde el dashboard.

## Impact

- Afecta: `dashboard/app.py` (nueva página en el `st.radio` de navegación).
- No cambia el contrato de la API ni la orquestación existente.
