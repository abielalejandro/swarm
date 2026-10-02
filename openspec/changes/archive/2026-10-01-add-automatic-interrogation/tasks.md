## 1. Configuración

- [x] 1.1 Agregar flags/env para habilitar interrogación automática.
- [x] 1.2 Definir umbral de rechazos repetidos configurable.

## 2. Orquestación

- [x] 2.1 Detectar agentes con rechazos repetidos después de evaluar propuestas.
- [x] 2.2 Interrogar automáticamente esos agentes y persistir resultados.
- [x] 2.3 Interrogar automáticamente agentes de una sesión al detectar deadlock.
- [x] 2.4 Mantener comportamiento fail-open si el Psychologist falla.

## 3. Dashboard

- [x] 3.1 Mostrar interrogaciones automáticas en el detalle de sesión.
- [x] 3.2 Incluir razón, ronda, agente, score, recomendación y flags.

## 4. Validación

- [x] 4.1 Ejecutar `py_compile` sobre dashboard y orchestrator.
- [x] 4.2 Ejecutar `openspec validate add-automatic-interrogation --strict`.
