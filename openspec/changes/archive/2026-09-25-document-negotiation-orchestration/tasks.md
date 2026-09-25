## 1. Verificación del contrato documentado

- [x] 1.1 Confirmar el modelo de request/response de `POST /negotiate` contra `orchestrator/orchestrator.py`
- [x] 1.2 Confirmar agentes por defecto (`AVAILABLE_AGENTS`) y su selección
- [x] 1.3 Confirmar estados de ronda/propuesta (`RoundStatus`, `ProposalStatus`) en `round_manager.py`
- [x] 1.4 Confirmar parámetros de configuración por env (umbral `0.6`, `MAX_ROUNDS` `20`, `ROUND_TIMEOUT` `60`)

## 2. Spec de la capability

- [x] 2.1 Redactar `specs/negotiation-orchestration/spec.md` con requisitos SHALL y escenarios given-when-then
- [x] 2.2 Cubrir inicio, consenso, deadlock, cancelación y consulta de estado

## 3. Validación

- [x] 3.1 `openspec validate document-negotiation-orchestration --strict` sin errores
- [x] 3.2 Revisión de Romerd antes de archivar el change hacia `openspec/specs/`
