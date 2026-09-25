## Why

Swarm v1.0 es un sistema multiagente de toma de decisiones que ya está implementado (FastAPI + Redis + Docker Compose), pero no tenía control de versiones ni especificación. Este change documenta, como spec nativa de OpenSpec, el comportamiento **actual** del núcleo de orquestación (`orchestrator` + `round_manager`), para tener una base verificable antes de futuros cambios. No introduce comportamiento nuevo: describe lo que el código ya hace.

## What Changes

- **Nueva capability `negotiation-orchestration`:** formaliza el contrato de la API de orquestación y el ciclo de vida de una negociación.
- Documenta el endpoint `POST /negotiate` (inicio de sesión), la ejecución por rondas hasta consenso o `max_rounds`, la producción de `final_contract`, el estado de deadlock, la cancelación y las consultas de estado.
- Fija los agentes por defecto (Engineering, Finance, Security, DevOps, Legal), los estados de sesión/ronda/propuesta y los parámetros de configuración (umbral de consenso `0.6`, `MAX_ROUNDS_PER_NEGOTIATION` `20`, `ROUND_TIMEOUT_SECONDS` `60`).

## Capabilities

### New Capabilities
- `negotiation-orchestration`: API REST y ciclo de vida para iniciar, ejecutar por rondas, consultar y cancelar negociaciones multiagente orientadas a decisión, con Redis como estado compartido.

### Modified Capabilities
<!-- Ninguna: es la primera spec del proyecto. -->

## Impact

- **Código:** ninguno. Documentación de comportamiento existente en `orchestrator/orchestrator.py` y `orchestrator/round_manager.py`.
- **Fuera de alcance:** Guardian (reglas inmutables/penalizaciones), Psychologist/Meta-Psychologist (interrogatorio y auditoría), Executor (ansible/terraform) y Dashboard — cada uno merece su propia capability en changes posteriores.
- **Riesgos conocidos (documentados, no resueltos aquí):** la API no tiene autenticación y CORS está abierto (`allow_origins=["*"]`); el estado de sesión vive en Redis sin persistencia garantizada.
