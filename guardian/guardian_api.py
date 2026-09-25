"""
Guardian API - REST Interface for Constitutional Enforcement
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import os
import json
import logging

from constitution import ConstitutionalGuardian

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Constitutional Guardian API",
    description="Hardcoded constitutional enforcement for AI swarm",
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

# Initialize Guardian
guardian = ConstitutionalGuardian()

# ============================================
# MODELS
# ============================================

class PenaltyRequest(BaseModel):
    agent_id: str
    offense_type: str
    offense_data: Dict

class OverrideRequest(BaseModel):
    agent_id: str
    new_stake: float
    reactivate: bool = False

class AgendaDeployRequest(BaseModel):
    agent_id: str
    agenda: Dict
    signature: str

# ============================================
# ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return guardian.health_check()


@app.post("/enforce_penalty")
async def enforce_penalty(request: PenaltyRequest):
    """Apply a penalty to an agent"""
    result = guardian.enforce_penalty(
        request.agent_id,
        request.offense_type,
        request.offense_data
    )
    return result


@app.get("/agent/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get current status of an agent"""
    stake = guardian.redis.get(f"stake:{agent_id}") or "1.0"
    weight = guardian.redis.get(f"weight:{agent_id}") or "1.0"
    suspended = guardian.is_agent_suspended(agent_id)
    truth_score = guardian.redis.get(f"agent:{agent_id}:truth_score") or "0.5"
    
    return {
        "agent_id": agent_id,
        "stake": float(stake),
        "weight": float(weight),
        "suspended": suspended,
        "truth_score": float(truth_score),
        "system_state": guardian.redis.get("system_state") or "ACTIVE"
    }


@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    agent_ids = guardian._get_all_agent_ids()
    agents = []
    
    for agent_id in agent_ids:
        stake = guardian.redis.get(f"stake:{agent_id}") or "1.0"
        weight = guardian.redis.get(f"weight:{agent_id}") or "1.0"
        suspended = guardian.is_agent_suspended(agent_id)
        
        agents.append({
            "agent_id": agent_id,
            "stake": float(stake),
            "weight": float(weight),
            "suspended": suspended
        })
    
    return {"agents": agents, "count": len(agents)}


@app.post("/override")
async def human_override(
    request: OverrideRequest,
    x_human_secret: str = Header(...)
):
    """
    Human override endpoint - bypasses all automatic enforcement
    Requires HUMAN_OVERRIDE_SECRET header
    """
    # Verify secret
    expected_secret = os.getenv("HUMAN_OVERRIDE_SECRET", "change_me")
    if x_human_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid human override secret")
    
    # Apply override
    if request.reactivate:
        guardian.reactivate_agent(request.agent_id)
        return {
            "status": "reactivated",
            "agent": request.agent_id,
            "new_stake": 0.8,
            "message": "Agent reactivated with stake 0.8"
        }
    else:
        guardian.redis.set(f"stake:{request.agent_id}", request.new_stake)
        guardian.redis.set(f"weight:{request.agent_id}", 1.0)
        
        # Log override
        guardian._log_event("HUMAN_OVERRIDE", {
            "agent": request.agent_id,
            "new_stake": request.new_stake,
            "timestamp": "now"
        })
        
        return {
            "status": "overridden",
            "agent": request.agent_id,
            "new_stake": request.new_stake
        }


@app.post("/deploy_agenda")
async def deploy_agenda(
    request: AgendaDeployRequest,
    x_human_secret: str = Header(...)
):
    """
    Deploy a new hidden agenda for an agent
    Requires HUMAN_DEPLOYMENT_TOKEN header
    """
    expected_secret = os.getenv("HUMAN_DEPLOYMENT_TOKEN", "change_me")
    if x_human_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid deployment token")
    
    # Store agenda
    agenda_json = json.dumps(request.agenda)
    guardian.redis.set(f"agent:{request.agent_id}:hidden_agenda", agenda_json)
    guardian.redis.set(f"agent:{request.agent_id}:agenda_hash", request.signature)
    
    # Store backup
    guardian.redis.set(f"backup:{request.agent_id}", agenda_json)
    
    # Reset stake and weight
    guardian.redis.set(f"stake:{request.agent_id}", 1.0)
    guardian.redis.set(f"weight:{request.agent_id}", 1.0)
    guardian.redis.delete(f"suspended:{request.agent_id}")
    
    guardian._log_event("AGENDA_DEPLOYED", {
        "agent": request.agent_id,
        "timestamp": "now"
    })
    
    return {
        "status": "deployed",
        "agent": request.agent_id,
        "agenda": request.agenda
    }


@app.post("/reset_swarm")
async def reset_swarm(
    x_human_secret: str = Header(...)
):
    """Emergency reset of the entire swarm"""
    expected_secret = os.getenv("HUMAN_OVERRIDE_SECRET", "change_me")
    if x_human_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid human override secret")
    
    # Reset all agents
    agent_ids = guardian._get_all_agent_ids()
    for agent_id in agent_ids:
        guardian.redis.set(f"stake:{agent_id}", 1.0)
        guardian.redis.set(f"weight:{agent_id}", 1.0)
        guardian.redis.delete(f"suspended:{agent_id}")
        
        # Restore from backup
        backup = guardian.redis.get(f"backup:{agent_id}")
        if backup:
            guardian.redis.set(f"agent:{agent_id}:hidden_agenda", backup)
    
    # Clear grudges
    guardian.redis.delete("grudges:*")
    guardian.redis.delete("suspicion:*")
    guardian.redis.set("system_state", "ACTIVE")
    
    guardian._log_event("SWARM_RESET", {
        "timestamp": "now",
        "agents_reset": len(agent_ids)
    })
    
    return {
        "status": "reset",
        "agents_reset": len(agent_ids),
        "message": "Swarm has been reset to initial state"
    }


@app.get("/audit_log")
async def get_audit_log(
    limit: int = 100,
    x_human_secret: str = Header(...)
):
    """Get recent audit log entries (human only)"""
    expected_secret = os.getenv("HUMAN_OVERRIDE_SECRET", "change_me")
    if x_human_secret != expected_secret:
        raise HTTPException(status_code=403, detail="Invalid human override secret")
    
    # Try to get from PostgreSQL
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            database=os.getenv('POSTGRES_DB', 'swarm_audit'),
            user=os.getenv('POSTGRES_USER', 'swarm'),
            password=os.getenv('POSTGRES_PASSWORD', 'swarm_secret')
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT id, timestamp, event_type, agent_id, data, hash
            FROM audit_log
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return {
            "entries": [
                {
                    "id": r[0],
                    "timestamp": r[1].isoformat(),
                    "event_type": r[2],
                    "agent_id": r[3],
                    "data": r[4],
                    "hash": r[5]
                }
                for r in rows
            ],
            "count": len(rows)
        }
    except Exception as e:
        logger.warning(f"Could not read from PostgreSQL: {e}")
        # Fallback to Redis
        logs = guardian.redis.lrange("audit_log", 0, limit - 1)
        return {
            "entries": [json.loads(log) for log in logs],
            "count": len(logs),
            "source": "redis_fallback"
        }


@app.get("/constitution")
async def get_constitution():
    """Get current constitutional rules (read-only)"""
    from config.guardian_config import (
        IMMEDIATE_PENALTY_ENFORCEMENT,
        MAX_STAKE_LOSS_PER_SESSION,
        MIN_STAKE_FOR_PARTICIPATION,
        MIN_AGENTS_FOR_CONSENSUS,
        VETO_POWER_AGENTS,
        PENALTY_MULTIPLIERS,
        EMERGENCY_TRIGGERS
    )
    
    return {
        "version": "1.0.0",
        "immutable": True,
        "rules": {
            "immediate_penalty_enforcement": IMMEDIATE_PENALTY_ENFORCEMENT,
            "max_stake_loss_per_session": MAX_STAKE_LOSS_PER_SESSION,
            "min_stake_for_participation": MIN_STAKE_FOR_PARTICIPATION,
            "min_agents_for_consensus": MIN_AGENTS_FOR_CONSENSUS,
            "veto_power_agents": VETO_POWER_AGENTS,
            "penalty_multipliers": PENALTY_MULTIPLIERS,
            "emergency_triggers": EMERGENCY_TRIGGERS
        },
        "note": "These rules are hardcoded and cannot be modified by agents"
    }