# api-hardening Specification

## Purpose
TBD - created by archiving change add-api-hardening. Update Purpose after archive.
## Requirements
### Requirement: Limitar la tasa de peticiones de escritura

El orquestador SHALL limitar la cantidad de peticiones de escritura por IP dentro de
una ventana configurable, respondiendo `429 Too Many Requests` al exceder el límite.

#### Scenario: Dentro del límite

- **GIVEN** un límite de N peticiones por ventana
- **WHEN** un cliente hace hasta N peticiones POST dentro de la ventana
- **THEN** todas se procesan normalmente

#### Scenario: Excede el límite

- **GIVEN** un cliente que ya alcanzó N peticiones POST en la ventana
- **WHEN** hace una petición POST adicional en la misma ventana
- **THEN** el orquestador responde `429` con un header `Retry-After`
- **AND** no ejecuta la acción solicitada

#### Scenario: No afecta lecturas

- **GIVEN** el dashboard consulta endpoints GET periódicamente
- **WHEN** hace peticiones GET
- **THEN** el rate limiter de escritura no las bloquea

#### Scenario: Backend Redis del limiter no disponible

- **GIVEN** el backend Redis configurado para el rate limiter no responde
- **WHEN** llega una petición de escritura
- **THEN** el orquestador continúa aplicando el rate limit con fallback en memoria
- **AND** no interrumpe el servicio por la caída de Redis

### Requirement: Idempotencia en el inicio de negociación

`POST /negotiate` SHALL aceptar un header opcional `Idempotency-Key` y, cuando esté
presente, garantizar que una clave repetida devuelva la respuesta original sin crear
una nueva sesión.

#### Scenario: Primera petición con clave

- **GIVEN** una petición `POST /negotiate` con `Idempotency-Key: k1`
- **WHEN** se procesa por primera vez
- **THEN** se crea la sesión y la respuesta se cachea asociada a `k1`

#### Scenario: Repetición con la misma clave

- **GIVEN** una petición previa con `Idempotency-Key: k1` ya cacheada
- **WHEN** llega otra petición con `Idempotency-Key: k1`
- **THEN** el orquestador devuelve la respuesta cacheada
- **AND** no crea una nueva sesión

#### Scenario: Sin clave de idempotencia

- **GIVEN** una petición `POST /negotiate` sin header `Idempotency-Key`
- **WHEN** se procesa
- **THEN** se comporta como hoy: crea una sesión nueva en cada llamada

