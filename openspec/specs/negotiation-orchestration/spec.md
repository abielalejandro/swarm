# negotiation-orchestration Specification

## Purpose
TBD - created by archiving change document-negotiation-orchestration. Update Purpose after archive.
## Requirements
### Requirement: Iniciar una sesión de negociación
El sistema SHALL exponer `POST /negotiate` que, dado un `goal` no vacío y opcionalmente `deadline`, `budget`, `agents` y `max_rounds`, cree una sesión de negociación con un `session_id` único, la registre como activa en Redis y seleccione los agentes participantes. Cuando `agents` no se provee, el sistema SHALL usar el conjunto por defecto: Engineering, Finance, Security, DevOps y Legal. La respuesta SHALL incluir `session_id`, `status`, `current_round`, `goal`, `agents` y `created_at`.

#### Scenario: Inicio con objetivo válido
- **WHEN** el cliente envía `POST /negotiate` con un `goal` no vacío
- **THEN** el sistema crea una sesión con `session_id` único, la marca activa y responde con el estado inicial y la lista de agentes seleccionados

#### Scenario: Inicio sin lista de agentes
- **WHEN** el cliente envía `POST /negotiate` sin el campo `agents`
- **THEN** el sistema selecciona los cinco agentes por defecto (Engineering, Finance, Security, DevOps, Legal)

#### Scenario: Límite de rondas explícito
- **WHEN** el cliente envía `max_rounds` en la petición
- **THEN** el sistema usa ese valor como tope de rondas para la sesión, sin exceder `MAX_ROUNDS_PER_NEGOTIATION`

### Requirement: Ejecutar rondas hasta consenso
El sistema SHALL ejecutar la negociación en rondas sucesivas, recogiendo propuestas de los agentes en cada ronda. Una ronda SHALL alcanzar consenso cuando el nivel de acuerdo entre agentes iguala o supera `CONSENSUS_THRESHOLD` (por defecto `0.6`). Al alcanzar consenso, el sistema SHALL marcar la sesión como `completed`, fijar `completed_at` y exponer un `final_contract`.

#### Scenario: Consenso alcanzado
- **WHEN** una ronda alcanza o supera el umbral de consenso
- **THEN** el sistema finaliza la sesión como `completed` y expone el `final_contract` resultante

#### Scenario: Timeout de ronda
- **WHEN** una ronda excede `ROUND_TIMEOUT_SECONDS`
- **THEN** el sistema cierra esa ronda y continúa con la siguiente, sin superar el límite de rondas de la sesión

### Requirement: Cerrar sin consenso (deadlock)
El sistema SHALL detener la negociación cuando se agota el límite de rondas de la sesión sin alcanzar el umbral de consenso, marcando la última ronda como `deadlocked` y cerrando la sesión sin `final_contract`.

#### Scenario: Se agotan las rondas sin acuerdo
- **WHEN** se completa la última ronda permitida sin alcanzar el umbral de consenso
- **THEN** el sistema marca la ronda como `deadlocked` y cierra la sesión sin `final_contract`

### Requirement: Cancelar una sesión en curso
El sistema SHALL exponer `POST /session/{session_id}/cancel` que detenga las rondas pendientes de una sesión activa y la marque como cancelada.

#### Scenario: Cancelación de sesión activa
- **WHEN** el cliente envía `POST /session/{session_id}/cancel` sobre una sesión en curso
- **THEN** el sistema detiene la negociación y marca la sesión como cancelada

#### Scenario: Cancelación de sesión inexistente
- **WHEN** el cliente cancela un `session_id` que no existe
- **THEN** el sistema responde con un error indicando que la sesión no fue encontrada

### Requirement: Consultar estado de sesión y rondas
El sistema SHALL exponer `GET /session/{session_id}` y `GET /session/{session_id}/rounds` para consultar, respectivamente, el estado actual de una sesión (estado, ronda vigente, agentes, `final_contract` si existe) y el historial de rondas con sus propuestas y estado.

#### Scenario: Consulta de sesión existente
- **WHEN** el cliente consulta `GET /session/{session_id}` de una sesión existente
- **THEN** el sistema retorna su estado actual, la ronda vigente y, si aplica, el `final_contract`

#### Scenario: Consulta de historial de rondas
- **WHEN** el cliente consulta `GET /session/{session_id}/rounds`
- **THEN** el sistema retorna la lista de rondas con su número, estado, propuestas y marca de consenso

