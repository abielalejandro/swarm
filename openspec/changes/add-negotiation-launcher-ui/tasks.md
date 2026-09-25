## 1. Página y navegación

- [x] 1.1 Añadir "🚀 New Negotiation" a la lista del `st.radio` de navegación en `dashboard/app.py`.
- [x] 1.2 Crear el bloque `if page == "🚀 New Negotiation":` con título y caption.

## 2. Formulario

- [x] 2.1 Formulario (`st.form`) con: `goal` (text_area, requerido), `deadline` (date/text opcional), `budget` (number opcional), `agents` (multiselect desde `GET /agents` o lista por defecto), `max_rounds` (number opcional).
- [x] 2.2 Botón de envío deshabilitado o con error si `goal` está vacío.

## 3. Ejecución y resultado

- [x] 3.1 Al enviar, construir el JSON omitiendo campos vacíos y hacer `POST` a `{ORCHESTRATOR_URL}/negotiate` vía httpx.
- [x] 3.2 Mostrar `session_id` y `status` devueltos; enlace/acceso para ver la sesión en la página de Sessions.
- [x] 3.3 Manejar error de la API (status != 2xx o excepción de red) mostrando el mensaje sin romper la página.

## 4. Validación

- [x] 4.1 `openspec validate add-negotiation-launcher-ui --strict`.
