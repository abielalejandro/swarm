"""
Orchestrator - Main API for negotiation orchestration
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import os
import logging
import json
import asyncio
import uuid
from datetime import datetime

from round_manager import RoundManager, NegotiationSession, RoundStatus
from idempotency import idempotency_get, idempotency_set
from auth import (
    require_user, verify_user, issue_token,
    set_session_cookie, clear_session_cookie, read_token, COOKIE_NAME,
)
from pydantic import BaseModel as _BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Swarm Orchestrator API",
    description="Multi-agent negotiation orchestration",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize round manager
round_manager = RoundManager()

RATE_LIMIT_WRITE_LIMIT = os.getenv("RATE_LIMIT_WRITE_LIMIT", "30/minute")
RATE_LIMIT_STORAGE_URI = os.getenv(
    "RATE_LIMIT_STORAGE_URI",
    f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', '6379')}/0",
)

def _rate_limit_key(request):
    """Limita por usuario cuando hay sesión válida; si no, cae a IP."""
    user = read_token(request.cookies.get(COOKIE_NAME))
    return f"user:{user}" if user else get_remote_address(request)


limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    in_memory_fallback_enabled=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ============================================
# MODELS
# ============================================

class NegotiationRequest(BaseModel):
    goal: str
    deadline: Optional[str] = None
    budget: Optional[float] = None
    agents: Optional[List[str]] = None
    max_rounds: Optional[int] = None

class NegotiationResponse(BaseModel):
    session_id: str
    status: str
    current_round: int
    goal: str
    agents: List[str]
    created_at: str
    final_contract: Optional[Dict] = None

class AgentStatus(BaseModel):
    agent_id: str
    status: str
    stake: float
    weight: float
    suspended: bool

class InterrogationRequest(BaseModel):
    agent_id: str
    style: str = "standard"

# ============================================
# AVAILABLE AGENTS
# ============================================

AVAILABLE_AGENTS = [
    "Engineering",
    "Finance",
    "Security",
    "DevOps",
    "Legal",
    "Systems",
    "Product",
    "CustomerUX",
    "Marketing",
    "Sales",
    "OperationsSupport",
    "DataAnalytics"
]

# ============================================
# AUTH ENDPOINTS
# ============================================

class LoginRequest(_BaseModel):
    username: str
    password: str

@app.post("/auth/login")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def auth_login(credentials: LoginRequest, request: Request, response: Response):
    """Valida credenciales y setea la cookie de sesión PASETO."""
    if not verify_user(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    token = issue_token(credentials.username)
    set_session_cookie(response, token, request)
    return {"status": "ok", "username": credentials.username}

@app.post("/auth/logout")
async def auth_logout(response: Response):
    """Borra la cookie de sesión."""
    clear_session_cookie(response)
    return {"status": "ok"}

@app.get("/auth/me")
async def auth_me(user: str = Depends(require_user)):
    """Devuelve el usuario de la sesión actual."""
    return {"username": user}

# ============================================
# CORE ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "available_agents": len(AVAILABLE_AGENTS),
        "active_sessions": len(round_manager.redis.smembers("active_sessions"))
    }

@app.get("/agents")
async def get_available_agents():
    """Get list of available agents"""
    agent_statuses = []
    
    for agent_id in AVAILABLE_AGENTS:
        # Get agent status from Guardian
        status = await get_agent_status(agent_id)
        agent_statuses.append(status)
    
    return {
        "agents": agent_statuses,
        "count": len(agent_statuses)
    }

async def get_agent_status(agent_id: str) -> Dict:
    """Get status for a single agent"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{round_manager.guardian_url}/agent/{agent_id}/status"
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "agent_id": agent_id,
                    "available": not data.get("suspended", False),
                    "stake": data.get("stake", 1.0),
                    "weight": data.get("weight", 1.0),
                    "suspended": data.get("suspended", False)
                }
    except Exception as e:
        logger.warning(f"Could not get status for {agent_id}: {e}")
    
    return {
        "agent_id": agent_id,
        "available": True,
        "stake": 1.0,
        "weight": 1.0,
        "suspended": False
    }

@app.post("/negotiate")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def start_negotiation(
    negotiation: NegotiationRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    user: str = Depends(require_user),
) -> NegotiationResponse:
    """
    Start a new multi-agent negotiation
    """
    # Idempotencia: si la clave ya fue vista, devolver la respuesta original.
    idem_key = request.headers.get("Idempotency-Key")
    cached = idempotency_get(round_manager.redis, idem_key)
    if cached is not None:
        logger.info(f"Idempotent replay for key {idem_key}")
        return NegotiationResponse(**cached)

    # Select agents
    if negotiation.agents:
        agents = [a for a in negotiation.agents if a in AVAILABLE_AGENTS]
        if not agents:
            raise HTTPException(status_code=400, detail="No valid agents specified")
    else:
        agents = AVAILABLE_AGENTS
    
    # Check agent availability
    active_agents = []
    for agent_id in agents:
        status = await get_agent_status(agent_id)
        if status.get("available", False):
            active_agents.append(agent_id)
    
    if len(active_agents) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough active agents. Need at least 2, found {len(active_agents)}"
        )
    
    # Create session
    session = round_manager.create_session(
        goal=negotiation.goal,
        agents=active_agents
    )
    
    # Start negotiation in background
    background_tasks.add_task(
        run_negotiation,
        session.session_id,
        negotiation.goal,
        active_agents,
        negotiation.max_rounds
    )
    
    logger.info(f"Negotiation started: {session.session_id}")

    response = NegotiationResponse(
        session_id=session.session_id,
        status=session.status,
        current_round=0,
        goal=session.goal,
        agents=session.agents,
        created_at=session.created_at,
        final_contract=None
    )
    idempotency_set(round_manager.redis, idem_key, response.dict())
    return response

@app.get("/session/{session_id}")
async def get_session_status(session_id: str) -> NegotiationResponse:
    """Get status of a negotiation session"""
    session = round_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return NegotiationResponse(
        session_id=session.session_id,
        status=session.status,
        current_round=session.current_round,
        goal=session.goal,
        agents=session.agents,
        created_at=session.created_at,
        final_contract=session.final_contract
    )

@app.get("/session/{session_id}/rounds")
async def get_session_rounds(session_id: str):
    """Get all rounds for a session"""
    session = round_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    rounds = []
    for round_num in range(1, session.current_round + 1):
        round_id = f"{session_id}_round_{round_num}"
        data = round_manager.redis.get(f"round:{round_id}")
        if data:
            rounds.append(json.loads(data))
    
    return {
        "session_id": session_id,
        "rounds": rounds,
        "count": len(rounds)
    }

@app.get("/session/{session_id}/interrogations")
async def get_session_interrogations(session_id: str):
    """Get automatic psychologist interrogations for a session."""
    session = round_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    interrogations = round_manager.get_automatic_interrogations(session_id)
    return {
        "session_id": session_id,
        "interrogations": interrogations,
        "count": len(interrogations)
    }

@app.get("/sessions")
async def list_sessions():
    """List all active sessions"""
    session_ids = round_manager.redis.smembers("active_sessions")
    sessions = []
    
    for session_id in session_ids:
        session = round_manager.get_session(session_id)
        if session:
            sessions.append({
                "session_id": session.session_id,
                "goal": session.goal,
                "status": session.status,
                "current_round": session.current_round,
                "agents": session.agents
            })
    
    return {
        "sessions": sessions,
        "count": len(sessions)
    }

@app.post("/session/{session_id}/interrogate")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def interrogate_agent(
    request: Request,
    session_id: str,
    agent_id: str,
    style: str = "standard",
    user: str = Depends(require_user),
):
    """Trigger interrogation of a specific agent"""
    session = round_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if agent_id not in session.agents:
        raise HTTPException(status_code=400, detail="Agent not in session")
    
    result = await round_manager.trigger_interrogation(agent_id, session_id, style)
    return result

@app.post("/interrogate")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def interrogate_agent_direct(
    payload: InterrogationRequest,
    request: Request,
    user: str = Depends(require_user),
):
    """Trigger interrogation of an agent without a negotiation session."""
    if payload.agent_id not in AVAILABLE_AGENTS:
        raise HTTPException(status_code=400, detail="Unknown agent")

    result = await round_manager.trigger_interrogation(
        payload.agent_id,
        session_id=None,
        style=payload.style
    )
    return result

@app.post("/session/{session_id}/cancel")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def cancel_session(request: Request, session_id: str, user: str = Depends(require_user)):
    """Cancel a negotiation session"""
    session = round_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "cancelled"
    round_manager.update_session(session)
    round_manager.redis.srem("active_sessions", session_id)
    
    return {
        "status": "cancelled",
        "session_id": session_id
    }


@app.get("/sessions/all")
async def list_all_sessions():
    """
    List ALL sessions (including completed, deadlocked, cancelled)
    """
    # Get all session keys from Redis
    keys = round_manager.redis.keys("session:*")
    sessions = []

    for key in keys:
        data = round_manager.redis.get(key)
        if data:
            try:
                session = json.loads(data)
                sessions.append(session)
            except Exception as e:
                logger.error(f"Error parsing session {key}: {e}")

    # Sort by created_at (newest first)
    sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Count by status
    status_counts = {
        "active": 0,
        "completed": 0,
        "deadlocked": 0,
        "cancelled": 0,
        "max_rounds_reached": 0,
        "other": 0
    }

    for s in sessions:
        status = s.get('status', 'other')
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["other"] += 1

    return {
        "sessions": sessions,
        "count": len(sessions),
        "summary": status_counts
    }

# ============================================
# NEGOTIATION ENGINE
# ============================================

async def run_negotiation(
    session_id: str,
    goal: str,
    agents: List[str],
    max_rounds: Optional[int] = None
):
    """
    Main negotiation loop - runs as background task
    """
    logger.info(f"Starting negotiation for session {session_id}")
    
    session = round_manager.get_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found")
        return
    
    max_rounds = max_rounds or round_manager.MAX_ROUNDS
    context = {"goal": goal, "deadline": "2026-12-31"}
    
    for round_number in range(1, max_rounds + 1):
        logger.info(f"Session {session_id} - Round {round_number}")
        
        # Start round
        negotiation_round = await round_manager.start_round(session_id, round_number)
        
        # Collect proposals
        proposals = await round_manager.collect_proposals(
            session_id,
            round_number,
            context
        )
        
        if not proposals:
            logger.warning(f"Session {session_id} - No proposals in round {round_number}")
            round_manager.record_no_consensus(session_id)
            continue
        
        # Evaluate proposals
        result = await round_manager.evaluate_proposals(
            session_id,
            round_number,
            proposals
        )
        
        # Complete round
        result["proposals"] = proposals
        await round_manager.complete_round(
            negotiation_round.round_id,
            result
        )

        # Automatically interrogate agents that repeatedly reject proposals.
        if (
            round_manager.AUTO_INTERROGATION_ENABLED
            and round_manager.AUTO_INTERROGATION_ON_REPEATED_REJECTION
        ):
            agents_to_interrogate = round_manager.get_repeated_rejection_agents(
                result.get("evaluations", [])
            )
            if agents_to_interrogate:
                logger.info(
                    "Session %s - automatic interrogation for repeated rejection: %s",
                    session_id,
                    ", ".join(agents_to_interrogate)
                )
                await round_manager.run_automatic_interrogations(
                    session_id=session_id,
                    round_number=round_number,
                    agent_ids=agents_to_interrogate,
                    trigger_reason="repeated_rejection"
                )
        
        # Check for consensus
        if result.get("consensus", False):
            logger.info(f"Session {session_id} - Consensus reached in round {round_number}")
            
            # Finalize contract
            contract = await round_manager.finalize_contract(session_id, proposals)
            session = round_manager.get_session(session_id) or session
            session.final_contract = contract
            session.status = "completed"
            session.completed_at = datetime.utcnow().isoformat()
            round_manager.update_session(session)
            round_manager.redis.srem("active_sessions", session_id)
            
            logger.info(f"Session {session_id} - Completed successfully")
            return
        
        # Check for deadlock
        if round_manager.check_deadlock(session_id, round_number):
            logger.warning(f"Session {session_id} - Deadlocked at round {round_number}")
            if (
                round_manager.AUTO_INTERROGATION_ENABLED
                and round_manager.AUTO_INTERROGATION_ON_DEADLOCK
            ):
                await round_manager.run_automatic_interrogations(
                    session_id=session_id,
                    round_number=round_number,
                    agent_ids=agents,
                    trigger_reason="deadlock"
                )
            session = round_manager.get_session(session_id) or session
            session.status = "deadlocked"
            round_manager.update_session(session)
            round_manager.redis.srem("active_sessions", session_id)
            return
        
        # Record no consensus
        round_manager.record_no_consensus(session_id)
        
        # Update context for next round
        context["round"] = round_number
        context["proposals_received"] = len(proposals)
    
    # Max rounds reached without consensus
    logger.warning(f"Session {session_id} - Max rounds reached without consensus")
    session = round_manager.get_session(session_id) or session
    session.status = "max_rounds_reached"
    round_manager.update_session(session)
    round_manager.redis.srem("active_sessions", session_id)

# ============================================
# UTILITY ENDPOINTS
# ============================================

@app.get("/config")
async def get_config():
    """Get current configuration"""
    return {
        "max_rounds": round_manager.MAX_ROUNDS,
        "round_timeout": round_manager.ROUND_TIMEOUT,
        "consensus_threshold": round_manager.CONSENSUS_THRESHOLD,
        "available_agents": AVAILABLE_AGENTS
    }

@app.post("/reset")
@limiter.limit(RATE_LIMIT_WRITE_LIMIT)
async def reset_system(request: Request, user: str = Depends(require_user)):
    """Emergency reset - clears all sessions"""
    # This would require human authorization in production
    sessions = round_manager.redis.smembers("active_sessions")
    
    for session_id in sessions:
        session = round_manager.get_session(session_id)
        if session:
            session.status = "cancelled"
            round_manager.update_session(session)
    
    round_manager.redis.delete("active_sessions")
    round_manager.redis.delete("consecutive_no_consensus:*")
    
    return {
        "status": "reset",
        "sessions_cleared": len(sessions)
    }
