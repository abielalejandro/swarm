# decision-report-export Specification

## Purpose

Permitir que una persona no técnica revise una negociación exportando un reporte
legible y un anexo técnico desde el dashboard.

## Requirements

### Requirement: Exportar reporte HTML de decisión

El dashboard SHALL permitir descargar un reporte HTML autocontenido para una
sesión seleccionada.

#### Scenario: Descargar reporte HTML desde Sessions

- **GIVEN** una sesión seleccionada en la vista `Sessions`
- **WHEN** el usuario pulsa `Download decision report (HTML)`
- **THEN** el dashboard descarga un archivo `.html`
- **AND** el reporte incluye resumen ejecutivo, resultado y trazabilidad de rondas

### Requirement: Reporte legible para negocio

El reporte HTML SHALL presentar la negociación sin requerir conocimiento técnico
del sistema.

#### Scenario: Contenido del resumen ejecutivo

- **GIVEN** una sesión con datos disponibles
- **WHEN** se genera el reporte
- **THEN** incluye objetivo, estado, agentes participantes, rondas, fechas y conteos
- **AND** usa etiquetas legibles para estados conocidos

#### Scenario: Trazabilidad de rondas

- **GIVEN** una sesión con rondas registradas
- **WHEN** se genera el reporte
- **THEN** incluye propuestas y evaluaciones por ronda
- **AND** muestra consenso, tasa de aceptación y racionales visibles cuando existan

### Requirement: No exponer información sensible

El reporte HTML SHALL evitar exponer información interna o sensible del sistema.

#### Scenario: Exclusión de datos internos

- **GIVEN** una sesión con datos de negociación
- **WHEN** se genera el reporte HTML
- **THEN** no incluye agendas ocultas, prompts internos ni secretos operativos
- **AND** indica que el JSON crudo es el anexo para auditoría técnica

### Requirement: Exportar anexo técnico JSON

El dashboard SHALL permitir descargar los datos crudos usados para construir el
reporte.

#### Scenario: Descargar JSON técnico

- **GIVEN** una sesión seleccionada en la vista `Sessions`
- **WHEN** el usuario pulsa `Download raw data (JSON)`
- **THEN** el dashboard descarga un archivo `.json`
- **AND** el JSON incluye la sesión, rondas y resumen calculado
