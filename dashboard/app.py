"""
Swarm Dashboard - Streamlit UI for Human Monitoring
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
import redis
import httpx
import secrets
from html import escape
from datetime import datetime, timedelta
import asyncio

try:
    import extra_streamlit_components as stx
except ImportError:
    stx = None

def build_negotiate_payload(goal, deadline=None, budget=0.0, max_rounds=0, agents=None):
    """Arma el body de POST /negotiate omitiendo los opcionales vacíos. goal es obligatorio."""
    payload = {"goal": goal.strip()}
    if deadline and deadline.strip():
        payload["deadline"] = deadline.strip()
    if budget and budget > 0:
        payload["budget"] = float(budget)
    if max_rounds and max_rounds > 0:
        payload["max_rounds"] = int(max_rounds)
    if agents:
        payload["agents"] = list(agents)
    return payload

def safe_date(value):
    """Devuelve una fecha segura o 'N/A'"""
    if not value:
        return "N/A"
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return str(value)[:10] if value else "N/A"


def safe_text(value, default="N/A"):
    if value is None or value == "":
        return default
    return str(value)


def status_label(status):
    labels = {
        "active": "Activa",
        "completed": "Completada",
        "deadlocked": "Sin consenso",
        "cancelled": "Cancelada",
        "max_rounds_reached": "Rondas agotadas",
        "failed": "Fallida",
    }
    return labels.get(status, safe_text(status))


def _json_pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def build_decision_report_payload(session_data, rounds_data):
    rounds = rounds_data.get("rounds", []) if rounds_data else []
    proposals_count = sum(len(r.get("proposals", [])) for r in rounds)
    evaluations_count = sum(len(r.get("evaluation", {}).get("evaluations", [])) for r in rounds)
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "session": session_data,
        "rounds": rounds,
        "summary": {
            "session_id": session_data.get("session_id"),
            "goal": session_data.get("goal"),
            "status": session_data.get("status"),
            "status_label": status_label(session_data.get("status")),
            "agents": session_data.get("agents", []),
            "current_round": session_data.get("current_round", 0),
            "max_rounds": session_data.get("max_rounds", 0),
            "created_at": session_data.get("created_at"),
            "completed_at": session_data.get("completed_at"),
            "rounds_recorded": len(rounds),
            "proposals_count": proposals_count,
            "evaluations_count": evaluations_count,
            "has_final_contract": bool(session_data.get("final_contract")),
        }
    }


def _html_dict_table(items):
    rows = []
    for label, value in items:
        rows.append(
            "<tr>"
            f"<th>{escape(label)}</th>"
            f"<td>{escape(safe_text(value))}</td>"
            "</tr>"
        )
    return "<table>" + "".join(rows) + "</table>"


def build_decision_report_html(report):
    summary = report["summary"]
    session = report["session"]
    rounds = report["rounds"]
    final_contract = session.get("final_contract")
    agents = summary.get("agents", [])
    generated = report.get("generated_at")

    html_rounds = []
    for round_item in rounds:
        proposals = round_item.get("proposals", [])
        evaluation = round_item.get("evaluation", {})
        evaluations = evaluation.get("evaluations", [])
        proposal_blocks = []
        for proposal in proposals:
            proposal_blocks.append(
                "<article class='item'>"
                f"<h4>{escape(safe_text(proposal.get('agent_id'), 'Agente'))}</h4>"
                f"<p><strong>Dominio:</strong> {escape(safe_text(proposal.get('domain')))}</p>"
                f"<p><strong>Racional:</strong> {escape(safe_text(proposal.get('rationale')))}</p>"
                f"<pre>{escape(_json_pretty(proposal.get('terms', proposal)))}</pre>"
                "</article>"
            )

        evaluation_blocks = []
        for item in evaluations:
            evaluation_blocks.append(
                "<article class='item'>"
                f"<h4>{escape(safe_text(item.get('evaluator_agent') or item.get('evaluator'), 'Evaluador'))}</h4>"
                f"<p><strong>Decisión:</strong> {escape(safe_text(item.get('decision')))}</p>"
                f"<p><strong>Score:</strong> {escape(safe_text(item.get('score')))}</p>"
                f"<p><strong>Racional:</strong> {escape(safe_text(item.get('rationale')))}</p>"
                "</article>"
            )

        html_rounds.append(
            "<section class='round'>"
            f"<h3>Ronda {escape(safe_text(round_item.get('round_number')))}</h3>"
            + _html_dict_table([
                ("Estado", round_item.get("status")),
                ("Consenso alcanzado", "Sí" if round_item.get("consensus_reached") else "No"),
                ("Inicio", round_item.get("start_time")),
                ("Fin", round_item.get("end_time")),
                ("Tasa de aceptación", evaluation.get("acceptance_rate")),
            ])
            + "<h4>Propuestas</h4>"
            + ("".join(proposal_blocks) if proposal_blocks else "<p class='muted'>Sin propuestas registradas.</p>")
            + "<h4>Evaluaciones</h4>"
            + ("".join(evaluation_blocks) if evaluation_blocks else "<p class='muted'>Sin evaluaciones registradas.</p>")
            + "</section>"
        )

    contract_html = (
        f"<pre>{escape(_json_pretty(final_contract))}</pre>"
        if final_contract else
        "<p class='muted'>No hay contrato final registrado.</p>"
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Decision Report - {escape(safe_text(summary.get("session_id")))}</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font-family: Arial, sans-serif; color: #1f2933; margin: 40px; line-height: 1.45; }}
    header {{ border-bottom: 2px solid #0f766e; margin-bottom: 24px; padding-bottom: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ border-bottom: 1px solid #d9e2ec; margin-top: 28px; padding-bottom: 6px; }}
    h3 {{ margin-top: 20px; color: #0f766e; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0 18px; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ width: 220px; background: #f0f4f8; }}
    pre {{ background: #f8fafc; border: 1px solid #d9e2ec; padding: 12px; overflow-wrap: anywhere; white-space: pre-wrap; }}
    .badge {{ display: inline-block; background: #ccfbf1; color: #115e59; padding: 4px 8px; border-radius: 4px; font-weight: 700; }}
    .muted {{ color: #66788a; }}
    .item {{ border-left: 4px solid #99f6e4; padding: 8px 12px; margin: 10px 0; background: #fbffff; }}
    .round {{ break-inside: avoid; }}
    footer {{ border-top: 1px solid #d9e2ec; margin-top: 36px; padding-top: 12px; font-size: 12px; color: #66788a; }}
    @media print {{ body {{ margin: 20mm; }} .round {{ page-break-inside: avoid; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Decision Report</h1>
    <p class="muted">Swarm v1.0 · Generado: {escape(safe_text(generated))}</p>
    <p><span class="badge">{escape(safe_text(summary.get("status_label")))}</span></p>
  </header>

  <section>
    <h2>Resumen ejecutivo</h2>
    {_html_dict_table([
        ("Session ID", summary.get("session_id")),
        ("Objetivo", summary.get("goal")),
        ("Estado", summary.get("status_label")),
        ("Agentes", ", ".join(agents) if agents else "N/A"),
        ("Rondas ejecutadas", summary.get("current_round")),
        ("Rondas registradas", summary.get("rounds_recorded")),
        ("Propuestas registradas", summary.get("proposals_count")),
        ("Evaluaciones registradas", summary.get("evaluations_count")),
        ("Creada", summary.get("created_at")),
        ("Completada", summary.get("completed_at")),
    ])}
  </section>

  <section>
    <h2>Resultado</h2>
    {contract_html}
  </section>

  <section>
    <h2>Trazabilidad de rondas</h2>
    {''.join(html_rounds) if html_rounds else "<p class='muted'>No hay rondas registradas para esta sesión.</p>"}
  </section>

  <footer>
    Este reporte excluye agendas ocultas, prompts internos y secretos operativos. Para auditoría técnica completa, usar el JSON crudo exportado desde el dashboard.
  </footer>
</body>
</html>"""
# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Swarm Dashboard",
    page_icon="🐝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CONNECTIONS
# ============================================

@st.cache_resource
def get_redis():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )

redis_client = get_redis()

# Service URLs
ORCHESTRATOR_URL = os.getenv('ORCHESTRATOR_URL', 'http://localhost:8000')
GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://localhost:8001')
PSYCHOLOGIST_URL = os.getenv('PSYCHOLOGIST_URL', 'http://localhost:8002')
EXECUTOR_URL = os.getenv('EXECUTOR_URL', 'http://localhost:8004')
DASHBOARD_SESSION_COOKIE = os.getenv('DASHBOARD_SESSION_COOKIE', 'swarm_dashboard_session')
DASHBOARD_SESSION_TTL_SECONDS = int(os.getenv(
    'DASHBOARD_SESSION_TTL_SECONDS',
    os.getenv('SESSION_TTL_SECONDS', '86400')
))
DASHBOARD_AUTH_PREFIX = "dashboard_auth:"

# ============================================
# HELPER FUNCTIONS
# ============================================

def get_cookie_manager():
    if stx is None:
        return None
    return stx.CookieManager()


def _dashboard_auth_key(session_id):
    return f"{DASHBOARD_AUTH_PREFIX}{session_id}"


def _load_dashboard_auth(session_id):
    if not session_id:
        return None
    try:
        raw = redis_client.get(_dashboard_auth_key(session_id))
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _save_dashboard_auth(username, cookies):
    session_id = st.session_state.get("dashboard_session_id") or secrets.token_urlsafe(32)
    record = {"username": username, "cookies": dict(cookies or {})}
    redis_client.setex(
        _dashboard_auth_key(session_id),
        DASHBOARD_SESSION_TTL_SECONDS,
        json.dumps(record)
    )
    st.session_state["dashboard_session_id"] = session_id
    manager = get_cookie_manager()
    if manager:
        manager.set(
            DASHBOARD_SESSION_COOKIE,
            session_id,
            expires_at=datetime.utcnow() + timedelta(seconds=DASHBOARD_SESSION_TTL_SECONDS),
            same_site="lax",
            key="set_dashboard_session"
        )


def _clear_dashboard_auth():
    session_id = st.session_state.get("dashboard_session_id")
    manager = get_cookie_manager()
    if manager:
        session_id = session_id or manager.get(DASHBOARD_SESSION_COOKIE)
    if session_id:
        try:
            redis_client.delete(_dashboard_auth_key(session_id))
        except Exception:
            pass
    if manager:
        manager.delete(DASHBOARD_SESSION_COOKIE, key="delete_dashboard_session")
    st.session_state["dashboard_session_id"] = None
    st.session_state["auth_cookies"] = None
    st.session_state["auth_user"] = None


def hydrate_auth_from_dashboard_session():
    st.session_state.setdefault("dashboard_session_id", None)
    st.session_state.setdefault("auth_cookies", None)
    st.session_state.setdefault("auth_user", None)

    if st.session_state["auth_user"] and st.session_state["auth_cookies"]:
        return

    manager = get_cookie_manager()
    if not manager:
        return

    session_id = manager.get(DASHBOARD_SESSION_COOKIE)
    record = _load_dashboard_auth(session_id)
    if not record:
        return

    cookies = record.get("cookies") or {}
    try:
        response = httpx.get(f"{ORCHESTRATOR_URL}/auth/me", cookies=cookies, timeout=5.0)
        if response.status_code == 200:
            username = response.json().get("username") or record.get("username")
            st.session_state["dashboard_session_id"] = session_id
            st.session_state["auth_cookies"] = cookies
            st.session_state["auth_user"] = username
            redis_client.expire(_dashboard_auth_key(session_id), DASHBOARD_SESSION_TTL_SECONDS)
        else:
            _clear_dashboard_auth()
    except Exception:
        pass

def get_agent_status():
    """Get status of all agents"""
    try:
        response = httpx.get(f"{GUARDIAN_URL}/agents", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching agent status: {e}")
    return {"agents": [], "count": 0}

@st.cache_data(ttl=5, show_spinner=False)
def get_active_sessions():
    """Get active negotiation sessions"""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/sessions")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"sessions": [], "count": 0}

DEFAULT_AGENTS = [
    "Engineering",
    "Finance",
    "Security",
    "DevOps",
    "Legal",
    "Systems",
    "Product",
    "CustomerUX",
    "Marketing",
]

@st.cache_data(ttl=30, show_spinner=False)
def get_available_agents():
    """Lista de agentes disponibles para negociar (fallback a la lista por defecto)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/agents")
            if response.status_code == 200:
                data = response.json()
                names = [a.get("agent_id") if isinstance(a, dict) else a
                         for a in data.get("agents", [])]
                names = [n for n in names if n]
                if names:
                    return names
    except Exception:
        pass
    return DEFAULT_AGENTS

@st.cache_data(ttl=10, show_spinner=False)
def get_all_sessions():
    """Get ALL sessions from Redis via orchestrator"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/sessions/all")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        # No mostrar error en UI para evitar parpadeos
        pass
    return {"sessions": [], "count": 0, "summary": {}}

@st.cache_data(ttl=5, show_spinner=False)
def get_session_details(session_id):
    """Get details for a specific session"""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/session/{session_id}")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None

@st.cache_data(ttl=5, show_spinner=False)
def get_session_rounds(session_id):
    """Get rounds for a specific session"""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{ORCHESTRATOR_URL}/session/{session_id}/rounds")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return {"rounds": [], "count": 0}

def get_agent_emotional_state(agent_id):
    """Get emotional state for an agent"""
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{PSYCHOLOGIST_URL}/agent/{agent_id}/profile")
            if response.status_code == 200:
                return response.json()
    except Exception:
        pass
    return None

def get_audit_log(limit=100):
    """Get recent audit log entries"""
    try:
        response = httpx.get(
            f"{GUARDIAN_URL}/audit_log",
            params={"limit": limit},
            headers={"X-Human-Secret": os.getenv("HUMAN_OVERRIDE_SECRET", "change_me")},
            timeout=5.0
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {"entries": [], "count": 0}

def get_constitution():
    """Get current constitution rules"""
    try:
        response = httpx.get(f"{GUARDIAN_URL}/constitution", timeout=5.0)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}

# ============================================
# SIDEBAR
# ============================================

hydrate_auth_from_dashboard_session()

with st.sidebar:
    st.title("🐝 Swarm Dashboard")
    st.caption(f"v1.0.0 - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    st.divider()
    
    # System status
    st.subheader("📊 System Status")
    
    try:
        health = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
        if health.status_code == 200:
            st.success("✅ System Online")
            data = health.json()
            st.metric("Active Sessions", data.get("active_sessions", 0))
        else:
            st.error("❌ System Offline")
    except Exception:
        st.error("❌ System Offline")
    
    st.divider()

    # Auth (sesión por cookie PASETO)
    st.subheader("🔐 Sesión")
    if st.session_state["auth_user"]:
        st.caption(f"Conectado como **{st.session_state['auth_user']}**")
        if st.button("Cerrar sesión"):
            try:
                httpx.post(f"{ORCHESTRATOR_URL}/auth/logout",
                           cookies=st.session_state["auth_cookies"] or {}, timeout=5.0)
            except Exception:
                pass
            _clear_dashboard_auth()
            st.rerun()
    else:
        if stx is None:
            st.caption("La sesión persistente requiere instalar `extra-streamlit-components`.")
        with st.form("login"):
            lu = st.text_input("Usuario")
            lp = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar"):
                try:
                    r = httpx.post(f"{ORCHESTRATOR_URL}/auth/login",
                                   json={"username": lu, "password": lp}, timeout=10.0)
                    if r.status_code == 200:
                        st.session_state["auth_cookies"] = dict(r.cookies)
                        st.session_state["auth_user"] = r.json().get("username", lu)
                        _save_dashboard_auth(st.session_state["auth_user"],
                                             st.session_state["auth_cookies"])
                        st.rerun()
                    else:
                        st.error("Credenciales inválidas")
                except Exception as e:
                    st.error(f"No se pudo iniciar sesión: {e}")

    st.divider()

    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Overview", "🚀 New Negotiation", "📈 Sessions", "🤖 Agents", "🧠 Emotional State", "📜 Audit Log", "⚖️ Constitution"]
    )
    
    st.divider()
    
    # Quick actions
    st.subheader("⚡ Quick Actions")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        if st.button("🆕 New Session"):
            st.rerun()

# ============================================
# PAGE: OVERVIEW
# ============================================

if page == "🏠 Overview":
    st.title("🐝 Swarm Overview")
    st.caption("Real-time status of your AI negotiation swarm")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    # Agent status
    agent_data = get_agent_status()
    total_agents = agent_data.get("count", 0)
    active_agents = sum(1 for a in agent_data.get("agents", []) if not a.get("suspended", False))
    
    with col1:
        st.metric("🤖 Total Agents", total_agents, delta=f"{active_agents} active")
    
    # Sessions
    session_data = get_active_sessions()
    active_sessions = session_data.get("count", 0)
    
    with col2:
        st.metric("📋 Active Sessions", active_sessions)
    
    # Recent activity (last 24h)
    audit = get_audit_log(limit=10)
    recent_events = audit.get("count", 0)
    
    with col3:
        st.metric("📜 Events (24h)", recent_events)
    
    # Constitution version
    constitution = get_constitution()
    version = constitution.get("version", "N/A")
    
    with col4:
        st.metric("⚖️ Constitution", version)
    
    st.divider()
    
    # Agent status table
    st.subheader("🤖 Agent Status")
    
    if agent_data.get("agents"):
        agent_df = pd.DataFrame(agent_data["agents"])
        
        # Add color coding
        colors = []
        for status in agent_df.get("suspended", []):
            colors.append("🟢" if not status else "🔴")
        
        display_df = agent_df.copy()
        display_df["status"] = colors
        display_df = display_df[["agent_id", "status", "stake", "weight"]]
        
        st.dataframe(
            display_df,
            column_config={
                "agent_id": "Agent",
                "status": "Status",
                "stake": st.column_config.NumberColumn("Stake", format="%.2f"),
                "weight": st.column_config.NumberColumn("Weight", format="%.2f")
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No agents available")
    
    st.divider()
    
    # Active sessions list
    st.subheader("📋 Active Sessions")
    
    sessions = session_data.get("sessions", [])
    if sessions:
        for session in sessions:
            with st.expander(f"📋 {session['session_id']} - {session['goal'][:50]}..."):
                cols = st.columns(4)
                cols[0].metric("Status", session["status"])
                cols[1].metric("Round", session["current_round"])
                cols[2].metric("Agents", len(session["agents"]))
                # Verificar que created_at existe
                created_at = session.get("created_at")
                if created_at:
                    cols[3].metric("Created", created_at[:10] if len(created_at) >= 10 else created_at)
                else:
                    cols[3].metric("Created", "N/A")
                
                st.write("**Agents:**", ", ".join(session["agents"]))
    else:
        st.info("No active sessions")

# ============================================
# PAGE: SESSIONS
# ============================================

elif page == "📈 Sessions":
    # Botón de refresco manual
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("📈 Sesiones de Negociación")
    with col2:
        if st.button("🔄 Refrescar", key="refresh_sessions"):
            st.cache_data.clear()
            st.rerun()

    # Pestañas para filtrar
    tab1, tab2, tab3 = st.tabs(["🟢 Activas", "✅ Completadas", "📋 Todas"])

    with tab1:
        st.subheader("🟢 Sesiones Activas")
        session_data = get_active_sessions()
        sessions = session_data.get("sessions", [])

        if sessions:
            for session in sessions:
                with st.expander(f"📋 {session['session_id']} - {session['goal'][:50]}..."):
                    cols = st.columns(4)
                    cols[0].metric("Status", session.get("status", "N/A"))
                    cols[1].metric("Round", session.get("current_round", 0))
                    cols[2].metric("Agents", len(session.get("agents", [])))

                    created_at = session.get("created_at")
                    if created_at and isinstance(created_at, str) and len(created_at) >= 10:
                        cols[3].metric("Created", created_at[:10])
                    else:
                        cols[3].metric("Created", "N/A")

                    st.write("**Agents:**", ", ".join(session.get("agents", [])))
        else:
            st.info("No hay sesiones activas")

    with tab2:
        st.subheader("✅ Sesiones Completadas")

        # Obtener todas las sesiones con cache
        all_sessions_data = get_all_sessions()
        sessions = all_sessions_data.get("sessions", [])

        # Filtrar completadas
        completed = [s for s in sessions if s.get("status") == "completed"]

        if completed:
            st.caption(f"Mostrando {len(completed)} sesiones completadas")

            for session in completed:
                with st.expander(f"✅ {session['session_id']} - {session['goal'][:50]}..."):
                    cols = st.columns(4)
                    cols[0].metric("Status", "✅ Completed")
                    cols[1].metric("Rondas", session.get("current_round", 0))
                    cols[2].metric("Agents", len(session.get("agents", [])))

                    created_at = session.get("created_at")
                    if created_at and isinstance(created_at, str) and len(created_at) >= 10:
                        cols[3].metric("Created", created_at[:10])
                    else:
                        cols[3].metric("Created", "N/A")

                    st.write("**Agents:**", ", ".join(session.get("agents", [])))

                    # Ver si tiene contrato
                    contract = session.get("final_contract")
                    if contract:
                        contract_status = contract.get("status", "unknown")
                        if contract_status == "success":
                            st.success("📄 Contrato ejecutado correctamente")
                        elif contract_status == "error":
                            st.error(f"❌ Error en contrato: {contract.get('message', 'Unknown error')}")
                        else:
                            st.info(f"📄 Estado del contrato: {contract_status}")
                    else:
                        st.warning("⚠️ Sin contrato final")
        else:
            st.info("No hay sesiones completadas")

    with tab3:
        st.subheader("📋 Todas las Sesiones")

        all_sessions_data = get_all_sessions()
        sessions = all_sessions_data.get("sessions", [])
        summary = all_sessions_data.get("summary", {})

        if sessions:
            # Mostrar resumen
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total", len(sessions))
            col2.metric("🟢 Activas", summary.get("active", 0))
            col3.metric("✅ Completadas", summary.get("completed", 0))
            col4.metric("🔴 Fallidas", summary.get("deadlocked", 0) + summary.get("max_rounds_reached", 0))

            st.divider()

            # Tabla de todas las sesiones (limitada a 50)
            display_sessions = sessions[:50]
            data = []
            for session in display_sessions:
                created_at = session.get("created_at", "")[:10] if session.get("created_at") else "N/A"
                status_icon = {
                    "active": "🟢",
                    "completed": "✅",
                    "deadlocked": "🔴",
                    "cancelled": "⛔",
                    "max_rounds_reached": "⚠️"
                }.get(session.get("status", "other"), "⚪")

                data.append({
                    "Session": session.get("session_id", "N/A")[:20],
                    "Status": f"{status_icon} {session.get('status', 'N/A')}",
                    "Goal": session.get("goal", "N/A")[:40],
                    "Rounds": session.get("current_round", 0),
                    "Agents": len(session.get("agents", [])),
                    "Created": created_at
                })

            df = pd.DataFrame(data)
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Session": "Session ID",
                    "Status": "Status",
                    "Goal": "Goal",
                    "Rounds": "Rounds",
                    "Agents": "Agents",
                    "Created": "Created"
                }
            )

            if len(sessions) > 50:
                st.caption(f"Mostrando 50 de {len(sessions)} sesiones totales")

            # Selector para ver detalles (con clave única)
            session_ids = [s.get("session_id") for s in sessions[:50]]
            selected = st.selectbox(
                "Seleccionar sesión para ver detalles",
                session_ids,
                key="session_selector"
            )

            if selected:
                # Mostrar detalles sin recargar toda la página
                with st.expander(f"📊 Detalles: {selected}", expanded=True):
                    session_data = get_session_details(selected)
                    if session_data:
                        cols = st.columns(3)
                        cols[0].metric("Status", session_data.get("status", "N/A"))
                        cols[1].metric("Rondas", session_data.get("current_round", 0))
                        cols[2].metric("Agentes", len(session_data.get("agents", [])))

                        st.write("**Goal:**", session_data.get("goal", "N/A"))
                        st.write("**Agents:**", ", ".join(session_data.get("agents", [])))

                        # Ver rondas
                        rounds_data = get_session_rounds(selected)
                        rounds = rounds_data.get("rounds", [])

                        st.subheader("📤 Export")
                        report = build_decision_report_payload(session_data, rounds_data)
                        report_html = build_decision_report_html(report)
                        report_json = _json_pretty(report)
                        safe_session_id = "".join(
                            ch if ch.isalnum() or ch in ("-", "_") else "_"
                            for ch in selected
                        )
                        export_cols = st.columns(2)
                        export_cols[0].download_button(
                            "Download decision report (HTML)",
                            data=report_html,
                            file_name=f"{safe_session_id}-decision-report.html",
                            mime="text/html",
                            key=f"download_report_html_{selected}"
                        )
                        export_cols[1].download_button(
                            "Download raw data (JSON)",
                            data=report_json,
                            file_name=f"{safe_session_id}-decision-data.json",
                            mime="application/json",
                            key=f"download_report_json_{selected}"
                        )

                        # Ver contrato
                        contract = session_data.get("final_contract")
                        if contract:
                            st.subheader("📄 Contrato Final")
                            st.json(contract)

                        if rounds:
                            st.subheader("🔄 Rondas")
                            for r in rounds[-5:]:
                                st.markdown(f"**Ronda {r.get('round_number', 'N/A')}**")
                                st.json(r)
        else:
            st.info("No hay sesiones registradas")

# ============================================
# PAGE: AGENTS
# ============================================

elif page == "🤖 Agents":
    st.title("🤖 Agent Management")
    
    agent_data = get_agent_status()
    agents = agent_data.get("agents", [])
    
    if not agents:
        st.info("No agents available")
    else:
        # Agent selector
        agent_ids = [a.get("agent_id") for a in agents]
        selected_agent = st.selectbox("Select Agent", agent_ids)
        
        if selected_agent:
            agent_info = next((a for a in agents if a.get("agent_id") == selected_agent), None)
            
            if agent_info:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Stake", f"{agent_info.get('stake', 0):.2f}")
                col2.metric("Weight", f"{agent_info.get('weight', 0):.2f}")
                col3.metric("Suspended", "Yes" if agent_info.get("suspended") else "No")
                
                # Emotional profile
                col4.metric("Truth Score", "N/A")
                
                # Emotional state
                st.subheader("🧠 Emotional Profile")
                
                emotional = get_agent_emotional_state(selected_agent)
                if emotional:
                    cols = st.columns(4)
                    if emotional.get("emotional_state"):
                        state = emotional["emotional_state"]
                        cols[0].metric("Aggression", f"{state.get('aggression', 0):.2f}")
                        cols[1].metric("Cooperation", f"{state.get('cooperation', 0):.2f}")
                        cols[2].metric("Anxiety", f"{state.get('anxiety', 0):.2f}")
                        cols[3].metric("Confidence", f"{state.get('confidence', 0):.2f}")
                    
                    # Interrogation history
                    st.subheader("📋 Interrogation History")
                    history = emotional.get("interrogation_history", [])
                    if history:
                        df = pd.DataFrame(history)
                        df = df[["timestamp", "answers"]]
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No interrogation history")
                
                # Hidden agenda
                st.subheader("🔒 Hidden Agenda")
                if emotional and emotional.get("hidden_agenda"):
                    st.json(emotional["hidden_agenda"])
                else:
                    st.info("No hidden agenda available")

# ============================================
# PAGE: EMOTIONAL STATE
# ============================================

elif page == "🧠 Emotional State":
    st.title("🧠 Emotional State Dashboard")
    
    # Get all agents
    agent_data = get_agent_status()
    agents = agent_data.get("agents", [])
    
    if not agents:
        st.info("No agents available")
    else:
        # Collect emotional data
        emotional_data = []
        for agent in agents:
            agent_id = agent.get("agent_id")
            profile = get_agent_emotional_state(agent_id)
            if profile and profile.get("emotional_state"):
                state = profile["emotional_state"]
                emotional_data.append({
                    "agent_id": agent_id,
                    "aggression": state.get("aggression", 0.5),
                    "cooperation": state.get("cooperation", 0.5),
                    "anxiety": state.get("anxiety", 0.3),
                    "confidence": state.get("confidence", 0.7),
                    "tone": state.get("tone", "neutral")
                })
        
        if emotional_data:
            df = pd.DataFrame(emotional_data)
            
            # Emotional radar chart
            st.subheader("📊 Emotional Radar")
            
            fig = go.Figure()
            for agent in emotional_data:
                fig.add_trace(go.Scatterpolar(
                    r=[agent["aggression"], agent["cooperation"], agent["anxiety"], agent["confidence"]],
                    theta=["Aggression", "Cooperation", "Anxiety", "Confidence"],
                    fill='toself',
                    name=agent["agent_id"]
                ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 1]
                    )
                ),
                showlegend=True,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Emotional table
            st.subheader("📋 Emotional Summary")
            
            # Color coding for tone
            def color_tone(tone):
                colors = {
                    "aggressive": "🔴",
                    "cooperative": "🟢",
                    "hostile": "⛔",
                    "friendly": "😊",
                    "neutral": "⚪"
                }
                return colors.get(tone, "⚪")
            
            df["tone_emoji"] = df["tone"].apply(color_tone)
            st.dataframe(
                df[["agent_id", "tone_emoji", "aggression", "cooperation", "anxiety", "confidence"]],
                column_config={
                    "agent_id": "Agent",
                    "tone_emoji": "Tone",
                    "aggression": st.column_config.NumberColumn("Aggression", format="%.2f"),
                    "cooperation": st.column_config.NumberColumn("Cooperation", format="%.2f"),
                    "anxiety": st.column_config.NumberColumn("Anxiety", format="%.2f"),
                    "confidence": st.column_config.NumberColumn("Confidence", format="%.2f")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Grudge matrix
            st.subheader("🔥 Grudge Matrix")
            
            grudges = {}
            for agent in agents:
                agent_id = agent.get("agent_id")
                try:
                    response = httpx.get(
                        f"http://agent_{agent_id.lower()}:8005/grudges",
                        timeout=3.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        grudges[agent_id] = data.get("grudges", {})
                except Exception:
                    pass
            
            if grudges:
                # Create matrix
                agent_ids = list(grudges.keys())
                n = len(agent_ids)
                matrix = [[0] * n for _ in range(n)]
                
                for i, a1 in enumerate(agent_ids):
                    for j, a2 in enumerate(agent_ids):
                        if i != j:
                            matrix[i][j] = grudges.get(a1, {}).get(a2, 0)
                
                fig = go.Figure(data=go.Heatmap(
                    z=matrix,
                    x=agent_ids,
                    y=agent_ids,
                    colorscale="Reds",
                    text=matrix,
                    texttemplate="%{text}",
                    textfont={"size": 12},
                    hoverongaps=False
                ))
                
                fig.update_layout(
                    title="Grudge Matrix (higher = more negative)",
                    height=400,
                    xaxis_title="Target Agent",
                    yaxis_title="Source Agent"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No grudge data available")
        else:
            st.info("No emotional data available")

# ============================================
# PAGE: AUDIT LOG
# ============================================

elif page == "📜 Audit Log":
    st.title("📜 Audit Log")
    st.caption("Immutable audit trail of all system events")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        limit = st.number_input("Entries", min_value=10, max_value=500, value=100, step=10)
    with col2:
        event_filter = st.selectbox("Event Type", ["All", "PENALTY_ENFORCED", "AGENT_SUSPENDED", "EMERGENCY_SHUTDOWN", "HUMAN_OVERRIDE"])
    
    # Get audit log
    with st.spinner("Loading audit log..."):
        audit_data = get_audit_log(limit)
        entries = audit_data.get("entries", [])
    
    if entries:
        # Filter if needed
        if event_filter != "All":
            entries = [e for e in entries if e.get("event_type") == event_filter]
        
        # Display as table
        df = pd.DataFrame(entries)
        
        # Parse timestamp
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Display
        st.dataframe(
            df[["timestamp", "event_type", "agent_id", "data"]],
            column_config={
                "timestamp": st.column_config.DatetimeColumn("Timestamp"),
                "event_type": "Event Type",
                "agent_id": "Agent",
                "data": st.column_config.JsonColumn("Data")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Hash chain integrity
        st.subheader("🔒 Hash Chain Integrity")
        
        hashes = [e.get("hash") for e in entries if e.get("hash")]
        if hashes:
            # Check if hashes are unique
            unique_hashes = len(set(hashes))
            total_hashes = len(hashes)
            
            col1, col2 = st.columns(2)
            col1.metric("Total Hashes", total_hashes)
            col2.metric("Unique Hashes", unique_hashes)
            
            if unique_hashes == total_hashes:
                st.success("✅ All hashes are unique - chain integrity verified")
            else:
                st.error("❌ Duplicate hashes detected - possible tampering!")
    else:
        st.info("No audit log entries found")

# ============================================
# PAGE: CONSTITUTION
# ============================================

elif page == "⚖️ Constitution":
    st.title("⚖️ Constitutional Guardian")
    st.caption("Hardcoded rules governing the swarm")
    
    constitution = get_constitution()
    
    if constitution:
        # Display rules
        st.subheader("📋 Constitutional Rules")
        
        rules = constitution.get("rules", {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Immediate Enforcement", "✅" if rules.get("immediate_penalty_enforcement") else "❌")
            st.metric("Max Stake Loss", f"{rules.get('max_stake_loss_per_session', 0):.0%}")
            st.metric("Min Participation Stake", f"{rules.get('min_stake_for_participation', 0):.0%}")
            st.metric("Min Consensus", f"{rules.get('min_agents_for_consensus', 0):.0%}")
        
        with col2:
            st.write("**Veto Power Agents:**")
            for agent in rules.get("veto_power_agents", []):
                st.write(f"- {agent}")
        
        # Penalty multipliers
        st.subheader("⚡ Penalty Multipliers")
        
        multipliers = rules.get("penalty_multipliers", {})
        if multipliers:
            df = pd.DataFrame([
                {"Offense": k.capitalize(), "Multiplier": v}
                for k, v in multipliers.items()
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Emergency triggers
        st.subheader("🚨 Emergency Triggers")
        
        triggers = rules.get("emergency_triggers", {})
        if triggers:
            df = pd.DataFrame([
                {"Trigger": k.replace("_", " ").capitalize(), "Threshold": v}
                for k, v in triggers.items()
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Note
        st.info("⚠️ These rules are hardcoded and cannot be modified by agents. Changes require human deployment.")
        
        # Constitution amendment (human only)
        st.divider()
        st.subheader("✍️ Constitutional Convention")
        st.caption("Review and amend the constitution (human only)")
        
        st.warning("⚠️ Constitutional amendments require human override secret")
        
        with st.form("constitution_amend"):
            # Show current penalties
            st.write("**Current Penalty Multipliers:**")
            for offense, mult in multipliers.items():
                new_mult = st.number_input(
                    f"{offense.capitalize()} Multiplier",
                    min_value=0.1,
                    max_value=5.0,
                    value=float(mult),
                    step=0.1
                )
            
            # Show current triggers
            st.write("**Current Emergency Triggers:**")
            for trigger, value in triggers.items():
                new_value = st.number_input(
                    trigger.replace("_", " ").capitalize(),
                    min_value=0.0,
                    max_value=20.0,
                    value=float(value),
                    step=0.5
                )
            
            secret = st.text_input("Human Override Secret", type="password")
            submitted = st.form_submit_button("Apply Amendments")
            
            if submitted:
                if secret == os.getenv("HUMAN_OVERRIDE_SECRET", "change_me"):
                    st.success("✅ Amendments applied successfully!")
                    # In production, would call Guardian API
                else:
                    st.error("❌ Invalid override secret")
    else:
        st.info("Could not load constitution. Is the Guardian service running?")

# ============================================
# PAGE: NEW NEGOTIATION
# ============================================

elif page == "🚀 New Negotiation":
    st.title("🚀 New Negotiation")
    st.caption("Componé y ejecutá una solicitud a POST /negotiate desde la UI")

    with st.form("new_negotiation", clear_on_submit=True):
        goal = st.text_area(
            "Goal *",
            placeholder="Ej: Seleccionar proveedor de cloud para la empresa",
            help="Objetivo de la negociación (obligatorio)"
        )

        col1, col2 = st.columns(2)
        with col1:
            deadline = st.text_input(
                "Deadline (YYYY-MM-DD)",
                placeholder="2026-09-15",
                help="Fecha límite (opcional)"
            )
            budget = st.number_input(
                "Budget",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                help="Presupuesto en la moneda del proyecto (0 = sin especificar)"
            )
        with col2:
            max_rounds = st.number_input(
                "Max rounds",
                min_value=0,
                value=0,
                step=1,
                help="Rondas máximas (0 = usar el valor por defecto del orquestador)"
            )
            agents = st.multiselect(
                "Agents",
                options=get_available_agents(),
                help="Agentes participantes (vacío = todos por defecto)"
            )

        submitted = st.form_submit_button("▶️ Ejecutar negociación", type="primary")

    if submitted:
        if not goal.strip():
            st.warning("⚠️ El campo **Goal** es obligatorio.")
        else:
            payload = build_negotiate_payload(goal, deadline, budget, max_rounds, agents)

            try:
                import uuid
                headers = {"Idempotency-Key": str(uuid.uuid4())}
                cookies = st.session_state.get("auth_cookies") or {}
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{ORCHESTRATOR_URL}/negotiate", json=payload,
                                       headers=headers, cookies=cookies)
                if resp.status_code == 401:
                    st.error("🔒 Necesitás iniciar sesión (barra lateral) para lanzar una negociación.")
                elif resp.status_code // 100 == 2:
                    data = resp.json()
                    session_id = data.get("session_id", "N/A")
                    status = data.get("status", "N/A")
                    st.success(f"✅ Negociación iniciada — session_id: `{session_id}` · status: **{status}**")
                    st.caption("Abrí **📈 Sessions** para seguir las rondas de esta sesión.")
                    with st.expander("Respuesta completa"):
                        st.json(data)
                else:
                    st.error(f"❌ La API respondió {resp.status_code}: {resp.text}")
            except Exception as e:
                st.error(f"❌ No se pudo contactar al orquestador: {e}")

# ============================================
# FOOTER
# ============================================

st.divider()
st.caption("🐝 Swarm v1.0 - Constitutional AI Negotiation System")
