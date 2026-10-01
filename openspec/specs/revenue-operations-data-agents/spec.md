# revenue-operations-data-agents Specification

## Purpose

Agregar voces de ingresos, operación diaria y analítica para completar la
evaluación de decisiones más allá de producto, mercado y tecnología.

## Requirements

### Requirement: Agente Sales disponible

El sistema SHALL exponer `Sales` como agente seleccionable y participante de
negociaciones.

#### Scenario: Sales participa en una negociación

- **GIVEN** una negociación incluye `Sales`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_sales`
- **AND** el agente usa una agenda orientada a revenue, objeciones de clientes y sales readiness

### Requirement: Agente OperationsSupport disponible

El sistema SHALL exponer `OperationsSupport` como agente seleccionable y
participante de negociaciones.

#### Scenario: OperationsSupport participa en una negociación

- **GIVEN** una negociación incluye `OperationsSupport`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_operationssupport`
- **AND** el agente usa una agenda orientada a soporte, documentación y operación diaria

### Requirement: Agente DataAnalytics disponible

El sistema SHALL exponer `DataAnalytics` como agente seleccionable y participante
de negociaciones.

#### Scenario: DataAnalytics participa en una negociación

- **GIVEN** una negociación incluye `DataAnalytics`
- **WHEN** el orquestador ejecuta rondas
- **THEN** llama al servicio `agent_dataanalytics`
- **AND** el agente usa una agenda orientada a métricas, evidencia, KPIs y experimentación

### Requirement: Dashboard permite seleccionar agentes complementarios

El dashboard SHALL permitir seleccionar `Sales`, `OperationsSupport` y
`DataAnalytics` al crear una negociación.

#### Scenario: Fallback del selector de agentes

- **GIVEN** el dashboard no puede obtener agentes desde el orquestador
- **WHEN** usa su lista fallback
- **THEN** la lista incluye `Sales`, `OperationsSupport` y `DataAnalytics`
