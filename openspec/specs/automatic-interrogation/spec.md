# automatic-interrogation Specification

## Purpose
TBD - created by archiving change add-automatic-interrogation. Update Purpose after archive.
## Requirements
### Requirement: Configurar interrogación automática

El orquestador SHALL permitir habilitar o deshabilitar la interrogación automática
del Psychologist mediante configuración de entorno.

#### Scenario: Funcionalidad deshabilitada

- **GIVEN** `AUTO_INTERROGATION_ENABLED=false`
- **WHEN** una negociación entra en deadlock o hay rechazos repetidos
- **THEN** el orquestador no dispara interrogatorios automáticos

#### Scenario: Funcionalidad habilitada

- **GIVEN** `AUTO_INTERROGATION_ENABLED=true`
- **WHEN** ocurre una condición configurada de interrogación
- **THEN** el orquestador intenta interrogar a los agentes correspondientes

### Requirement: Interrogar por rechazo repetido

El orquestador SHALL interrogar automáticamente a un agente cuando acumule rechazos
repetidos en una ronda según el umbral configurado.

#### Scenario: Agente supera el umbral de rechazos

- **GIVEN** `AUTO_INTERROGATION_ON_REPEATED_REJECTION=true`
- **AND** el umbral configurado es 2
- **WHEN** un agente emite 2 o más evaluaciones con `decision=reject` en una ronda
- **THEN** el orquestador interroga a ese agente con razón `repeated_rejection`
- **AND** guarda el resultado asociado a la sesión y ronda

#### Scenario: Agente no supera el umbral

- **GIVEN** el umbral configurado es 2
- **WHEN** un agente emite menos de 2 rechazos en una ronda
- **THEN** el orquestador no interroga automáticamente a ese agente por rechazos

### Requirement: Interrogar por deadlock

El orquestador SHALL interrogar automáticamente a los agentes participantes cuando
la sesión se marque como `deadlocked`.

#### Scenario: Deadlock detectado

- **GIVEN** `AUTO_INTERROGATION_ON_DEADLOCK=true`
- **WHEN** `check_deadlock` detecta deadlock para una sesión
- **THEN** el orquestador interroga a los agentes de esa sesión
- **AND** guarda cada resultado con razón `deadlock`

### Requirement: Persistir evidencia de interrogación

El orquestador SHALL guardar los resultados de interrogación automática para consulta
posterior por sesión.

#### Scenario: Resultado persistido

- **GIVEN** una interrogación automática finaliza
- **WHEN** el resultado se guarda
- **THEN** queda disponible con `agent_id`, `session_id`, `round_number`,
  `trigger_reason`, `style`, `truth_score`, `recommendation`, `deception_flags` y
  `created_at`

### Requirement: Mostrar interrogaciones automáticas

El dashboard SHALL mostrar las interrogaciones automáticas en el detalle de una
sesión.

#### Scenario: Sesión con interrogaciones automáticas

- **GIVEN** una sesión tiene resultados de interrogación automática
- **WHEN** el usuario abre el detalle de esa sesión
- **THEN** ve una sección con agente, ronda, razón, score, recomendación y flags

#### Scenario: Sesión sin interrogaciones automáticas

- **GIVEN** una sesión no tiene interrogaciones automáticas
- **WHEN** el usuario abre el detalle de esa sesión
- **THEN** el dashboard indica que no hay interrogaciones automáticas registradas

### Requirement: Fallar abierto

La interrogación automática SHALL NOT impedir que la negociación continúe o cierre
si el servicio Psychologist no responde o responde con error.

#### Scenario: Psychologist no disponible

- **GIVEN** ocurre una condición de interrogación automática
- **AND** el servicio Psychologist falla
- **WHEN** el orquestador intenta interrogar
- **THEN** registra el error como resultado de interrogación
- **AND** continúa el flujo de negociación

