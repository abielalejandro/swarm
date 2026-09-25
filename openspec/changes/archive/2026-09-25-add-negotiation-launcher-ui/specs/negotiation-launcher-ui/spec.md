## ADDED Requirements

### Requirement: Componer una solicitud de negociación

El dashboard SHALL ofrecer una página con un formulario que permita capturar los
campos de `POST /negotiate`: `goal` (obligatorio) y, opcionalmente, `deadline`,
`budget`, `agents` y `max_rounds`.

#### Scenario: Formulario con campos de la API

- **GIVEN** un usuario abre la página "🚀 New Negotiation"
- **WHEN** se renderiza el formulario
- **THEN** ve un campo de texto para `goal`, y campos opcionales para `deadline`,
  `budget`, `max_rounds`, y un selector múltiple de `agents` con los agentes
  disponibles (Engineering, Finance, Security, DevOps, Legal)

#### Scenario: Agentes desde la API

- **GIVEN** el orquestador expone `GET /agents`
- **WHEN** se carga la página
- **THEN** el selector de `agents` se puebla con esos agentes
- **AND** si la consulta falla, usa la lista por defecto sin romper la página

### Requirement: Validar el objetivo antes de enviar

El dashboard SHALL impedir el envío de una negociación sin `goal`.

#### Scenario: goal vacío

- **GIVEN** el campo `goal` está vacío
- **WHEN** el usuario intenta enviar el formulario
- **THEN** el dashboard muestra un aviso de que `goal` es obligatorio
- **AND** no envía la solicitud al orquestador

### Requirement: Ejecutar la negociación

El dashboard SHALL enviar `POST {ORCHESTRATOR_URL}/negotiate` con los campos
provistos, omitiendo los opcionales que estén vacíos.

#### Scenario: Envío exitoso

- **GIVEN** un `goal` "Seleccionar proveedor de cloud para la empresa", `budget`
  200000, `deadline` "2026-09-15" y `max_rounds` 7
- **WHEN** el usuario envía el formulario
- **THEN** el dashboard hace `POST /negotiate` con ese JSON
- **AND** muestra el `session_id` y el `status` devueltos por la API

#### Scenario: Omitir campos opcionales vacíos

- **GIVEN** solo se completa `goal`
- **WHEN** el usuario envía el formulario
- **THEN** el cuerpo enviado contiene únicamente `goal`, sin claves opcionales vacías

### Requirement: Mostrar errores de la API

El dashboard SHALL mostrar los errores de la solicitud sin interrumpir la página.

#### Scenario: La API responde con error

- **GIVEN** el orquestador responde con un código distinto de 2xx o hay un fallo de red
- **WHEN** el usuario envía el formulario
- **THEN** el dashboard muestra un mensaje de error legible
- **AND** el formulario permanece disponible para reintentar
