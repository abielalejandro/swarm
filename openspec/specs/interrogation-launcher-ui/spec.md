# interrogation-launcher-ui Specification

## Purpose
TBD - created by archiving change add-interrogation-launcher-ui. Update Purpose after archive.
## Requirements
### Requirement: Ejecutar interrogatorios desde el dashboard

El dashboard SHALL ofrecer una pantalla para disparar interrogatorios del servicio
Psychologist sin requerir que el usuario arme solicitudes manuales.

#### Scenario: Página visible en navegación

- **GIVEN** un usuario abre el dashboard
- **WHEN** ve la navegación lateral
- **THEN** encuentra una opción "🧪 Interrogation"

#### Scenario: Formulario de interrogatorio

- **GIVEN** un usuario abre la página "🧪 Interrogation"
- **WHEN** se renderiza el formulario
- **THEN** puede elegir modo, agente y estilo de interrogatorio

### Requirement: Interrogar dentro de una sesión

El dashboard SHALL permitir interrogar un agente dentro de una sesión existente,
validando que el agente pertenezca a esa sesión.

#### Scenario: Interrogatorio asociado a sesión

- **GIVEN** existe una sesión con el agente `Engineering`
- **WHEN** el usuario elige modo "Session", selecciona la sesión, el agente y envía
- **THEN** el dashboard llama `POST /session/{session_id}/interrogate`
- **AND** muestra el resultado del Psychologist

#### Scenario: Agente fuera de la sesión

- **GIVEN** existe una sesión que no contiene el agente seleccionado
- **WHEN** el usuario intenta interrogar ese agente en modo "Session"
- **THEN** el orquestador responde un error de validación
- **AND** el dashboard muestra el error sin romper la página

### Requirement: Interrogar sin negociación

El orquestador SHALL exponer una ruta protegida para interrogar un agente sin
asociarlo a una sesión de negociación.

#### Scenario: Interrogatorio directo

- **GIVEN** un usuario autenticado selecciona un agente
- **WHEN** envía el formulario en modo "Direct"
- **THEN** el dashboard llama `POST /interrogate`
- **AND** el orquestador delega al Psychologist sin requerir `session_id`

### Requirement: Proteger los interrogatorios

Las rutas de interrogatorio del orquestador SHALL requerir una sesión de usuario
válida y SHALL estar sujetas al rate limiter de escrituras.

#### Scenario: Usuario autenticado

- **GIVEN** un usuario con sesión válida
- **WHEN** ejecuta un interrogatorio
- **THEN** el orquestador procesa la solicitud

#### Scenario: Usuario no autenticado

- **GIVEN** un cliente sin sesión válida
- **WHEN** llama una ruta de interrogatorio
- **THEN** el orquestador responde `401`
