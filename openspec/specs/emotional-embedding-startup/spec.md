# emotional-embedding-startup Specification

## Purpose

Controlar el costo de arranque de los modelos emocionales y evitar descargas
repetidas cuando los embeddings estén habilitados.

## Requirements

### Requirement: Embeddings emocionales deshabilitados por defecto

Los servicios que dependen de modelos `SentenceTransformer` SHALL evitar cargar
modelos emocionales durante el arranque cuando `ENABLE_EMOTIONAL_EMBEDDINGS` no
esté habilitado.

#### Scenario: Arranque por defecto sin descarga de modelo

- **GIVEN** `ENABLE_EMOTIONAL_EMBEDDINGS=false` o no definido
- **WHEN** arrancan los agentes y el psychologist
- **THEN** no cargan `all-MiniLM-L6-v2` durante el import o la inicialización
- **AND** las rutas existentes siguen disponibles con estado emocional por defecto

### Requirement: Carga diferida del modelo

El motor de embeddings SHALL cargar `all-MiniLM-L6-v2` solo cuando los embeddings
estén explícitamente habilitados y una operación requiera generar embeddings.

#### Scenario: Embeddings habilitados

- **GIVEN** `ENABLE_EMOTIONAL_EMBEDDINGS=true`
- **WHEN** una operación solicita una firma emocional basada en embeddings
- **THEN** el modelo se carga en ese momento
- **AND** se reutiliza para operaciones posteriores del mismo proceso

### Requirement: Cache persistente de Hugging Face

Los servicios que pueden cargar modelos emocionales SHALL compartir una cache
persistente de Hugging Face mediante un volumen Docker.

#### Scenario: Reinicio con embeddings habilitados

- **GIVEN** los embeddings emocionales están habilitados
- **AND** el modelo ya fue descargado una vez
- **WHEN** los contenedores se recrean con `docker compose down` y `up`
- **THEN** los servicios reutilizan la cache `huggingface_cache`
- **AND** evitan descargar nuevamente el modelo desde cero
