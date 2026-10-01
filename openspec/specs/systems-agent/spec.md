# systems-agent Specification

## Purpose

Agregar un agente de Sistemas para evaluar decisiones desde la perspectiva de
integración, mantenibilidad y coherencia del paisaje tecnológico.

## Requirements

### Requirement: Agente Systems disponible

El sistema SHALL exponer `Systems` como agente seleccionable y participante de
negociaciones.

#### Scenario: Systems aparece en agentes disponibles

- **GIVEN** el orquestador está levantado
- **WHEN** un cliente consulta los agentes disponibles
- **THEN** `Systems` aparece junto a Engineering, Finance, Security, DevOps y Legal

#### Scenario: Systems participa en una negociación

- **GIVEN** una negociación incluye `Systems` en la lista de agentes
- **WHEN** el orquestador ejecuta las rondas
- **THEN** llama al servicio `agent_systems`
- **AND** recibe propuestas/evaluaciones del agente de Sistemas

### Requirement: Agenda de Sistemas

El agente `Systems` SHALL tener una agenda propia orientada a arquitectura de
sistemas, integración, mantenibilidad y operación.

#### Scenario: Systems carga su agenda desde YAML

- **GIVEN** `agents/config/agent_agendas.yml` contiene una entrada `Systems`
- **WHEN** el agente `Systems` arranca
- **THEN** carga su agenda pública y oculta desde esa entrada

### Requirement: Dashboard permite seleccionar Systems

El dashboard SHALL permitir incluir `Systems` al crear una negociación.

#### Scenario: Selector de agentes

- **GIVEN** el dashboard no puede obtener agentes desde el orquestador
- **WHEN** usa su lista fallback
- **THEN** la lista incluye `Systems`
