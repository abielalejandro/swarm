# market-product-agents Specification

## Purpose

Agregar voces de producto, usuario y mercado a las negociaciones para balancear
las perspectivas técnicas, legales, financieras y operativas existentes.

## Requirements

### Requirement: Agente Product disponible

El sistema SHALL exponer `Product` como agente seleccionable y participante de
negociaciones.

#### Scenario: Product participa en una negociación

- **GIVEN** una negociación incluye `Product`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_product`
- **AND** el agente usa una agenda orientada a valor de producto, roadmap y foco

### Requirement: Agente CustomerUX disponible

El sistema SHALL exponer `CustomerUX` como agente seleccionable y participante
de negociaciones.

#### Scenario: CustomerUX participa en una negociación

- **GIVEN** una negociación incluye `CustomerUX`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_customerux`
- **AND** el agente usa una agenda orientada a experiencia de usuario, adopción y usabilidad

### Requirement: Agente Marketing disponible

El sistema SHALL exponer `Marketing` como agente seleccionable y participante de
negociaciones.

#### Scenario: Marketing participa en una negociación

- **GIVEN** una negociación incluye `Marketing`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_marketing`
- **AND** el agente usa una agenda orientada a posicionamiento, narrativa y go-to-market

### Requirement: Dashboard permite seleccionar agentes de negocio

El dashboard SHALL permitir seleccionar `Product`, `CustomerUX` y `Marketing`
al crear una negociación.

#### Scenario: Fallback del selector de agentes

- **GIVEN** el dashboard no puede obtener agentes desde el orquestador
- **WHEN** usa su lista fallback
- **THEN** la lista incluye `Product`, `CustomerUX` y `Marketing`
