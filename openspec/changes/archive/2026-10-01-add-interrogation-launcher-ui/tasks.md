## 1. API

- [x] 1.1 Proteger `POST /session/{session_id}/interrogate` con sesión de usuario.
- [x] 1.2 Agregar `POST /interrogate` para interrogar un agente sin sesión.
- [x] 1.3 Reutilizar `RoundManager.trigger_interrogation` para ambas rutas.

## 2. Dashboard

- [x] 2.1 Agregar la página "🧪 Interrogation" a la navegación.
- [x] 2.2 Crear formulario con modo, sesión opcional, agente y estilo.
- [x] 2.3 Validar que el usuario esté autenticado antes de ejecutar.
- [x] 2.4 Mostrar resultado con score, recomendación, preguntas/respuestas y flags.

## 3. Validación

- [x] 3.1 Ejecutar `py_compile` sobre dashboard y orchestrator.
- [x] 3.2 Ejecutar `openspec validate add-interrogation-launcher-ui --strict`.
