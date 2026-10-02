# Swarm v1.0

Swarm v1.0 es un demo funcional de **toma de decisiones por negociación multiagente**.

El sistema recibe un objetivo de negocio o técnico, convoca agentes con perspectivas distintas, ejecuta rondas de propuestas y evaluaciones, y termina con uno de estos resultados:

- `completed`: los agentes alcanzaron consenso y se genera un contrato final.
- `max_rounds_reached`: se agotaron las rondas configuradas sin consenso.
- `deadlocked`: el sistema detectó estancamiento.
- `cancelled`: la sesión fue cancelada manualmente.

No es LangGraph. La orquestación es propia, implementada con FastAPI, Redis, Docker Compose y servicios especializados.

## Para Qué Sirve

El proyecto permite simular decisiones complejas donde distintas áreas tienen incentivos, prioridades y riesgos distintos. Algunos ejemplos:

- Seleccionar proveedor cloud.
- Definir características de un producto.
- Priorizar una arquitectura técnica.
- Evaluar una campaña de marketing.
- Resolver un bug crítico con impacto operativo.
- Decidir una inversión o adquisición.
- Analizar una iniciativa desde seguridad, legal, producto, ventas, soporte y datos.

La idea no es que un LLM decida solo, sino que varios agentes negocien desde perspectivas diferentes y dejen trazabilidad de sus argumentos.

## Arquitectura

El sistema corre como un conjunto de servicios Docker:

| Servicio | Puerto | Rol |
| --- | ---: | --- |
| `orchestrator` | 8000 | API principal. Crea sesiones, coordina rondas y consulta estado. |
| `dashboard` | 8501 | UI Streamlit para login, lanzamiento de negociaciones, sesiones y reportes. |
| `guardian` | 8001 | Aplica reglas de gobernanza, penalizaciones y estado de agentes. |
| `psychologist` | 8002 | Interroga agentes y calcula señales de verdad/estado emocional. |
| `meta_psychologist` | 8003 | Audita la calidad/sesgo del psychologist. |
| `executor` | 8004 | Ejecuta/simula contratos finales como state machines. |
| `agent_*` | interno | Agentes negociadores por dominio. |
| `redis` | 6379 | Estado de sesiones, rondas, agendas y memoria operativa. |
| `postgres` | 5432 | Usuarios, auditoría y datos persistentes. |
| `qdrant` | 6333/6334 | Base vectorial preparada para memoria/embeddings. |

## Flujo de Negociación

1. Un usuario inicia sesión en el dashboard.
2. Crea una negociación desde **New Negotiation** indicando `goal`, `deadline`, `budget`, agentes participantes y `max_rounds`.
3. El orchestrator crea una sesión y convoca a los agentes.
4. En cada ronda, cada agente genera una propuesta y evalúa las propuestas de los demás.
5. Si la aceptación supera el umbral de consenso, la sesión queda `completed`.
6. Si no hay consenso, termina como `deadlocked` o `max_rounds_reached`.
7. Desde el dashboard se puede exportar un **Decision Report HTML** y un JSON técnico.

## Agentes Disponibles

| Agente | Perspectiva |
| --- | --- |
| `Engineering` | Calidad técnica, deuda técnica, tecnologías probadas. |
| `Finance` | ROI, presupuesto, costos previsibles. |
| `Security` | Seguridad, cumplimiento, auditoría y riesgo. |
| `DevOps` | Operación, automatización, confiabilidad y observabilidad. |
| `Legal` | Riesgo legal, regulaciones, contratos e IP. |
| `Systems` | Coherencia del ecosistema, integración y mantenibilidad. |
| `Product` | Valor de producto, roadmap, foco y resultados de usuario. |
| `CustomerUX` | Experiencia de usuario, adopción, accesibilidad y fricción. |
| `Marketing` | Posicionamiento, narrativa, diferenciación y go-to-market. |
| `Sales` | Revenue, pricing, objeciones comerciales y sales readiness. |
| `OperationsSupport` | Soporte, documentación, operación diaria y escalaciones. |
| `DataAnalytics` | Métricas, evidencia, KPIs, experimentación y calidad de datos. |

Las agendas se configuran en:

```text
agents/config/agent_agendas.yml
```

Ese archivo contiene la agenda pública (`stated_agenda`) y la agenda oculta (`hidden_agenda`) de cada agente. Para cambiar comportamiento de un agente, se edita el YAML y se reinicia el servicio del agente afectado. No hace falta tocar código Python.

## Seguridad

El sistema incluye seguridad básica para demo:

- Autenticación por usuario y contraseña.
- Usuarios almacenados en Postgres con password bcrypt.
- Sesión PASETO v4.local.
- Cookie de sesión segura, `HttpOnly`, `SameSite=Lax`.
- Persistencia de sesión del dashboard ante refresh.
- Endpoints de escritura protegidos.
- Rate limit con `slowapi`, por usuario autenticado o IP.
- Idempotencia en `POST /negotiate` vía header `Idempotency-Key`.

## Reportes

Desde **Sessions** en el dashboard se puede exportar:

- **Decision Report HTML**: reporte legible para personas no técnicas.
- **Raw JSON**: anexo técnico con la sesión, rondas, propuestas y evaluaciones.

El reporte HTML incluye resumen ejecutivo, objetivo, estado final, agentes participantes, rondas, propuestas, evaluaciones y contrato final si existe. Excluye agendas ocultas, prompts internos y secretos operativos.

## Configuración

Copiar `.env.example` a `.env` y ajustar los valores necesarios:

```bash
cp .env.example .env
```

Variables principales:

| Variable | Uso |
| --- | --- |
| `LLM_PROVIDER` | Proveedor LLM: `openai`, `deepseek`, `anthropic`, `groq`, `azure`, `ollama`, `lm_studio`, `custom`. |
| `LLM_MODEL` | Modelo a usar. |
| `LLM_API_KEY` | API key del proveedor. |
| `LLM_BASE_URL` | URL base para proveedores custom. |
| `POSTGRES_PASSWORD` | Password de Postgres. |
| `PASETO_KEY` | Clave simétrica para sesiones. Usar al menos 32 bytes. |
| `COOKIE_SECURE` | `true`, `false` o `auto`. En HTTP local usar `false`. |
| `SESSION_TTL_SECONDS` | Duración de sesión. |
| `ENABLE_EMOTIONAL_EMBEDDINGS` | `false` por defecto. Evita descargar modelos al arrancar. |
| `AUTO_INTERROGATION_ENABLED` | Activa/desactiva interrogatorios automáticos del Psychologist. |
| `AUTO_INTERROGATION_ON_DEADLOCK` | Interroga agentes cuando una sesión entra en deadlock. |
| `AUTO_INTERROGATION_ON_REPEATED_REJECTION` | Interroga agentes que rechazan propuestas repetidamente. |
| `AUTO_INTERROGATION_REJECTION_THRESHOLD` | Rechazos mínimos por ronda para disparar interrogación automática. |

## Crear Usuarios

Levantar Postgres y orchestrator:

```bash
docker compose up -d postgres orchestrator
```

Crear o actualizar un usuario sin imprimir la contraseña:

```bash
docker compose exec orchestrator python -c 'from getpass import getpass; from auth import upsert_user; u=input("Usuario: "); upsert_user(u, getpass("Contraseña: ")); print(f"Usuario {u!r} creado/actualizado.")'
```

## Levantar el Sistema

Construir y levantar todo:

```bash
docker compose build
docker compose up -d
```

URLs principales:

- Dashboard: http://localhost:8501
- Orchestrator API: http://localhost:8000/docs
- Guardian API: http://localhost:8001/docs
- Psychologist API: http://localhost:8002/docs
- Meta-Psychologist API: http://localhost:8003/docs
- Executor API: http://localhost:8004/docs

## Comandos Frecuentes

```bash
./scripts/status.sh
./scripts/monitor.sh
./scripts/view_all_sessions.sh
./scripts/view_resume.sh
./scripts/backup.sh
./scripts/restore.sh
docker compose down
```

## Rebuild Parcial

Si cambiás agendas YAML:

```bash
docker compose up -d agent_engineering agent_finance agent_security agent_devops agent_legal agent_systems agent_product agent_customerux agent_marketing agent_sales agent_operationssupport agent_dataanalytics
```

Si cambiás código de agentes:

```bash
docker compose build agent_engineering agent_finance agent_security agent_devops agent_legal agent_systems agent_product agent_customerux agent_marketing agent_sales agent_operationssupport agent_dataanalytics
docker compose up -d agent_engineering agent_finance agent_security agent_devops agent_legal agent_systems agent_product agent_customerux agent_marketing agent_sales agent_operationssupport agent_dataanalytics
```

Si cambiás dashboard:

```bash
docker compose build dashboard
docker compose up -d dashboard
```

Si cambiás orchestrator:

```bash
docker compose build orchestrator
docker compose up -d orchestrator
```

## API Principal

Crear una negociación:

```bash
curl -X POST http://localhost:8000/negotiate \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-001" \
  -d '{
    "goal": "Seleccionar proveedor de cloud para la empresa",
    "deadline": "2026-09-15",
    "budget": 200000,
    "agents": ["Engineering", "Finance", "Security", "DevOps", "Legal", "Systems"],
    "max_rounds": 7
  }'
```

Nota: el endpoint está protegido por sesión. Para uso manual, normalmente conviene lanzar negociaciones desde el dashboard.

Consultar sesión:

```bash
curl http://localhost:8000/session/<session_id>
```

Consultar rondas:

```bash
curl http://localhost:8000/session/<session_id>/rounds
```

Cancelar sesión:

```bash
curl -X POST http://localhost:8000/session/<session_id>/cancel
```

## Estados de Resultado

| Estado | Significado |
| --- | --- |
| `active` | La sesión está en curso. |
| `completed` | Hubo consenso y se generó contrato final. |
| `max_rounds_reached` | Se agotaron las rondas sin consenso. |
| `deadlocked` | La negociación se estancó. |
| `cancelled` | La sesión fue cancelada. |

`deadlocked` o `max_rounds_reached` no implican necesariamente un error técnico. Pueden ser resultados válidos cuando los agentes no logran acuerdo.

## OpenSpec

Las capacidades del proyecto están documentadas en `openspec/specs/`.

Validar specs:

```bash
openspec validate --specs --strict
```

Specs principales:

- `negotiation-orchestration`
- `negotiation-launcher-ui`
- `api-hardening`
- `user-auth`
- `decision-report-export`
- `emotional-embedding-startup`
- `agent-agenda-config`
- `systems-agent`
- `market-product-agents`
- `revenue-operations-data-agents`
- `automatic-interrogation`

## Notas Operativas

- `docker compose down` conserva volúmenes de Redis/Postgres/Qdrant por defecto.
- `docker compose down -v` elimina volúmenes y borra estado persistente.
- Los modelos emocionales no se cargan por defecto (`ENABLE_EMOTIONAL_EMBEDDINGS=false`).
- Si se habilitan embeddings, la cache Hugging Face usa el volumen `huggingface_cache`.
- Este proyecto es un demo/laboratorio de gobernanza multiagente, no una plataforma productiva lista para internet público.
