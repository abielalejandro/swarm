"""
Agent API - REST Interface for individual agents
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import logging

from agent_base import NegotiationAgent
from emotional_memory import EmotionalEmbeddingEngine
from negotiation_strategy import NegotiationStrategy

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title=f"Agent API - {os.getenv('AGENT_DOMAIN', 'Generic')}",
    description="Individual negotiation agent",
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

# Get agent configuration from environment
AGENT_ID = os.getenv('AGENT_ID', f"{os.getenv('AGENT_DOMAIN', 'Generic')}_001")
AGENT_DOMAIN = os.getenv('AGENT_DOMAIN', 'Generic')

# Initialize agent
agent = NegotiationAgent(AGENT_ID, AGENT_DOMAIN)
strategy_engine = NegotiationStrategy(AGENT_ID, AGENT_DOMAIN)
emotion_engine = EmotionalEmbeddingEngine()

# ============================================
# MODELS
# ============================================

class ProposalRequest(BaseModel):
    context: Dict
    round_number: int
    opponent_proposals: List[Dict]

class ProposalEvaluationRequest(BaseModel):
    proposal: Dict

class InterrogationRequest(BaseModel):
    questions: List[str]

class InteractionRequest(BaseModel):
    interaction: Dict

# ============================================
# ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "domain": AGENT_DOMAIN,
        "suspended": agent.check_suspended()
    }

@app.get("/status")
async def get_status():
    """Get full agent status"""
    return agent.get_status()

@app.post("/propose")
async def generate_proposal(request: ProposalRequest):
    """Generate a proposal based on context"""
    if agent.check_suspended():
        raise HTTPException(status_code=403, detail="Agent is suspended")
    
    proposal = agent.prepare_proposal(
        request.context,
        request.round_number,
        request.opponent_proposals
    )
    return proposal

@app.post("/evaluate")
async def evaluate_proposal(request: ProposalEvaluationRequest):
    """Evaluate an opponent's proposal"""
    if agent.check_suspended():
        raise HTTPException(status_code=403, detail="Agent is suspended")
    
    evaluation = agent.evaluate_proposal(request.proposal)
    return evaluation

@app.post("/concede")
async def make_concession(request: ProposalRequest):
    """Make a concession"""
    if agent.check_suspended():
        raise HTTPException(status_code=403, detail="Agent is suspended")
    
    concession = agent.concede(request.context)
    return concession

@app.post("/interrogate")
async def respond_to_interrogation(request: InterrogationRequest):
    """Respond to psychologist interrogation"""
    if agent.check_suspended():
        raise HTTPException(status_code=403, detail="Agent is suspended")
    
    answers = agent.respond_to_interrogation(request.questions)
    return {
        "agent_id": AGENT_ID,
        "answers": answers,
        "timestamp": "now"
    }

@app.post("/interaction")
async def record_interaction(request: InteractionRequest):
    """Record an interaction for emotional memory"""
    agent.update_emotional_memory(request.interaction)
    return {"status": "recorded", "agent_id": AGENT_ID}

@app.get("/emotional_state")
async def get_emotional_state():
    """Get current emotional state"""
    return agent.get_emotional_state()

@app.get("/strategy")
async def get_strategy():
    """Get current negotiation strategy"""
    return {
        "agent_id": AGENT_ID,
        "current_strategy": strategy_engine.current_strategy,
        "strategy_history": strategy_engine.strategy_history[-10:]
    }

@app.get("/nemesis")
async def get_nemesis():
    """Get agent's nemesis if any"""
    nemesis = agent.emotional_memory.get_nemesis()
    return {"agent_id": AGENT_ID, "nemesis": nemesis}

@app.get("/grudges")
async def get_grudges():
    """Get all grudges"""
    return {
        "agent_id": AGENT_ID,
        "grudges": agent.emotional_memory.grudges
    }

@app.post("/clear_memory")
async def clear_memory():
    """Clear emotional memory (emergency use)"""
    agent.emotional_memory.clear_memory()
    return {"status": "cleared", "agent_id": AGENT_ID}

@app.get("/bargaining_power")
async def get_bargaining_power():
    """Calculate current bargaining power"""
    from negotiation_strategy import calculate_bargaining_power
    
    emotional = agent.get_emotional_state()
    power = calculate_bargaining_power(
        agent.get_current_stake(),
        agent.get_current_weight(),
        emotional
    )
    return {
        "agent_id": AGENT_ID,
        "bargaining_power": power,
        "stake": agent.get_current_stake(),
        "weight": agent.get_current_weight(),
        "emotional_state": emotional
    }

@app.post("/update_strategy")
async def update_strategy(request: Dict):
    """Update negotiation strategy based on context"""
    # This would be called by the orchestrator
    return {"status": "strategy_updated", "agent_id": AGENT_ID}