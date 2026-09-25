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
from datetime import datetime, timedelta
import asyncio

def safe_date(value):
    """Devuelve una fecha segura o 'N/A'"""
    if not value:
        return "N/A"
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    return str(value)[:10] if value else "N/A"
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

# ============================================
# HELPER FUNCTIONS
# ============================================

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
    
    # Navigation
    page = st.radio(
        "Navigation",
        ["🏠 Overview", "📈 Sessions", "🤖 Agents", "🧠 Emotional State", "📜 Audit Log", "⚖️ Constitution"]
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

                        # Ver contrato
                        contract = session_data.get("final_contract")
                        if contract:
                            st.subheader("📄 Contrato Final")
                            st.json(contract)

                        # Ver rondas
                        rounds_data = get_session_rounds(selected)
                        rounds = rounds_data.get("rounds", [])
                        if rounds:
                            st.subheader("🔄 Rondas")
                            for r in rounds[-5:]:
                                with st.expander(f"Ronda {r.get('round_number', 'N/A')}"):
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
# FOOTER
# ============================================

st.divider()
st.caption("🐝 Swarm v1.0 - Constitutional AI Negotiation System")