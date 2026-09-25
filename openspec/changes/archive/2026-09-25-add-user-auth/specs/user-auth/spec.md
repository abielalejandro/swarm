## ADDED Requirements

### Requirement: Autenticación por usuario y contraseña

El orquestador SHALL autenticar usuarios contra una tabla `users` en PostgreSQL,
verificando la contraseña contra un hash bcrypt almacenado.

#### Scenario: Credenciales válidas

- **GIVEN** un usuario existente con contraseña correcta
- **WHEN** hace `POST /auth/login` con su usuario y contraseña
- **THEN** el orquestador responde `200` y establece una cookie de sesión

#### Scenario: Credenciales inválidas

- **GIVEN** un usuario inexistente o una contraseña incorrecta
- **WHEN** hace `POST /auth/login`
- **THEN** el orquestador responde `401` y no establece cookie

### Requirement: Sesión con token PASETO en cookie segura

La sesión SHALL representarse como un token PASETO v4.local entregado en una cookie
con los atributos `HttpOnly`, `Secure` y `SameSite=Lax`, con expiración.

#### Scenario: Cookie de sesión emitida en login

- **GIVEN** un login exitoso
- **WHEN** se responde al cliente
- **THEN** la cookie contiene un token PASETO v4.local con el usuario y una expiración
- **AND** la cookie es `HttpOnly`, `Secure` y `SameSite=Lax`

#### Scenario: Logout invalida la sesión del cliente

- **GIVEN** un cliente con cookie de sesión
- **WHEN** hace `POST /auth/logout`
- **THEN** el orquestador borra la cookie de sesión

#### Scenario: Consultar el usuario actual

- **GIVEN** un cliente con cookie de sesión válida
- **WHEN** hace `GET /auth/me`
- **THEN** el orquestador devuelve el usuario asociado a la sesión

### Requirement: Proteger endpoints de escritura

Los endpoints de escritura del orquestador (`POST /negotiate`,
`POST /session/{id}/cancel`, `POST /reset`) SHALL requerir una sesión válida.

#### Scenario: Petición autenticada

- **GIVEN** un cliente con cookie de sesión válida
- **WHEN** hace `POST /negotiate`
- **THEN** la petición se procesa normalmente

#### Scenario: Petición sin sesión

- **GIVEN** un cliente sin cookie o con token inválido/expirado
- **WHEN** hace `POST /negotiate`
- **THEN** el orquestador responde `401` y no crea la negociación

#### Scenario: Lecturas no requieren sesión

- **GIVEN** el dashboard consulta endpoints GET
- **WHEN** hace peticiones GET sin sesión
- **THEN** el orquestador las responde normalmente

### Requirement: Alta de usuarios controlada

El sistema SHALL permitir crear usuarios mediante un script de seed y NO SHALL exponer
un registro público.

#### Scenario: Crear usuario por seed

- **GIVEN** credenciales de un usuario provistas por variables de entorno
- **WHEN** se ejecuta el script de seed
- **THEN** el usuario queda almacenado con su contraseña hasheada con bcrypt

#### Scenario: Sin registro público

- **GIVEN** la API de auth expuesta
- **WHEN** un cliente busca un endpoint de registro
- **THEN** no existe un endpoint público de auto-registro
