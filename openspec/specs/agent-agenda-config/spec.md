# agent-agenda-config Specification

## Purpose

Permitir modificar las agendas públicas y ocultas de los agentes sin editar
código Python.

## Requirements

### Requirement: Agendas configurables por YAML

Los agentes SHALL cargar su agenda desde un archivo YAML editable cuando esté
disponible.

#### Scenario: Agente carga agenda desde YAML

- **GIVEN** `AGENT_AGENDA_FILE` apunta a un archivo YAML existente
- **AND** el archivo contiene una entrada para el dominio del agente
- **WHEN** el agente arranca
- **THEN** carga `stated_agenda` y `hidden_agenda` desde el YAML
- **AND** publica esa agenda en Redis para el resto del sistema

#### Scenario: Edición sin tocar código

- **GIVEN** una agenda existente en `agents/config/agent_agendas.yml`
- **WHEN** se cambia el archivo YAML y se reinicia el servicio del agente
- **THEN** el agente usa la nueva agenda sin modificar código Python

### Requirement: Fallback compatible

Los agentes SHALL conservar un fallback si el archivo YAML falta o no contiene
su dominio.

#### Scenario: YAML faltante o incompleto

- **GIVEN** `AGENT_AGENDA_FILE` no existe o no contiene el dominio del agente
- **WHEN** el agente arranca
- **THEN** usa la agenda existente en Redis o la agenda por defecto hardcodeada
- **AND** el servicio sigue arrancando
