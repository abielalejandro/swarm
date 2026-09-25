"""
Round Manager - Handles individual negotiation rounds
"""

import json
import os
import logging
import redis
import asyncio
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================
# ENUMS
# ============================================

class RoundStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEADLOCKED = "deadlocked"
    CANCELLED = "cancelled"

class ProposalStatus(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"
    COUNTERED = "countered"

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class NegotiationRound:
    round_id: str
    session_id: str
    round_number: int
    status: RoundStatus
    proposals: List[Dict]
    consensus_reached: bool
    start_time: str
    end_time: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "round_id": self.round_id,
            "session_id": self.session_id,
            "round_number": self.round_number,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "proposals": self.proposals,
            "consensus_reached": self.consensus_reached,
            "start_time": self.start_time,
            "end_time": self.end_time
        }

@dataclass
class NegotiationSession:
    session_id: str
    goal: str
    agents: List[str]
    current_round: int
    max_rounds: int
    status: str
    created_at: str
    completed_at: Optional[str] = None
    final_contract: Optional[Dict] = None

# ============================================
# ROUND MANAGER
# ============================================

class RoundManager:
    """
    Manages negotiation rounds and consensus
    """
    
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        
        self.guardian_url = os.getenv('GUARDIAN_URL', 'http://guardian:8001')
        self.psychologist_url = os.getenv('PSYCHOLOGIST_URL', 'http://psychologist:8002')
        self.executor_url = os.getenv('EXECUTOR_URL', 'http://executor:8004')
        
        self.MAX_ROUNDS = int(os.getenv('MAX_ROUNDS_PER_NEGOTIATION', 20))
        self.ROUND_TIMEOUT = int(os.getenv('ROUND_TIMEOUT_SECONDS', 60))
        self.CONSENSUS_THRESHOLD = float(os.getenv('CONSENSUS_THRESHOLD', 0.6))
        
        logger.info("RoundManager initialized")
    
    # ============================================
    # SESSION MANAGEMENT
    # ============================================
    
    def create_session(self, goal: str, agents: List[str]) -> NegotiationSession:
        """Create a new negotiation session"""
        session_id = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        session = NegotiationSession(
            session_id=session_id,
            goal=goal,
            agents=agents,
            current_round=0,
            max_rounds=self.MAX_ROUNDS,
            status="active",
            created_at=datetime.utcnow().isoformat()
        )
        
        # Store in Redis
        self.redis.set(
            f"session:{session_id}",
            json.dumps(asdict(session))
        )
        
        # Track active sessions
        self.redis.sadd("active_sessions", session_id)
        
        logger.info(f"Session created: {session_id} with {len(agents)} agents")
        return session
    
    def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get session data"""
        data = self.redis.get(f"session:{session_id}")
        if data:
            session_dict = json.loads(data)
            return NegotiationSession(**session_dict)
        return None
    
    def update_session(self, session: NegotiationSession):
        """Update session data"""
        self.redis.set(
            f"session:{session.session_id}",
            json.dumps(asdict(session))
        )
    
    # ============================================
    # ROUND MANAGEMENT
    # ============================================
    
    async def start_round(self, session_id: str, round_number: int) -> NegotiationRound:
        """Start a new round"""
        round_id = f"{session_id}_round_{round_number}"
        
        # Check if agent is suspended
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Check guardian for suspended agents
        active_agents = []
        for agent in session.agents:
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{self.guardian_url}/agent/{agent}/status",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        status = response.json()
                        if not status.get("suspended", False):
                            active_agents.append(agent)
                except Exception as e:
                    logger.warning(f"Could not check agent {agent}: {e}")
                    active_agents.append(agent)  # Assume active if guardian unavailable
        
        if len(active_agents) < 2:
            raise ValueError(f"Not enough active agents: {len(active_agents)}")
        
        # Create round
        negotiation_round = NegotiationRound(
            round_id=round_id,
            session_id=session_id,
            round_number=round_number,
            status=RoundStatus.IN_PROGRESS,
            proposals=[],
            consensus_reached=False,
            start_time=datetime.utcnow().isoformat()
        )
        
        # Store round
        self.redis.set(
            f"round:{round_id}",
            json.dumps(negotiation_round.to_dict())
        )
        
        # Update session
        session.current_round = round_number
        self.update_session(session)
        
        logger.info(f"Round {round_number} started for session {session_id}")
        return negotiation_round
    
    async def collect_proposals(
        self,
        session_id: str,
        round_number: int,
        context: Dict
    ) -> List[Dict]:
        """Collect proposals from all agents"""
        session = self.get_session(session_id)
        if not session:
            return []
        
        proposals = []
        agent_urls = {}
        
        # Get agent service URLs from environment
        for agent_name in session.agents:
            # Construct URL based on agent name
            # In production, use service discovery
            agent_url = f"http://agent_{agent_name.lower()}:8005"
            agent_urls[agent_name] = agent_url
        
        # Get previous proposals for context
        previous_rounds = self._get_previous_proposals(session_id, round_number)
        
        # Collect proposals in parallel
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for agent_id, url in agent_urls.items():
                task = self._get_agent_proposal(
                    client,
                    agent_id,
                    url,
                    context,
                    round_number,
                    previous_rounds
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error collecting proposal: {result}")
                elif result:
                    proposals.append(result)
        
        return proposals
    
    async def _get_agent_proposal(
        self,
        client: httpx.AsyncClient,
        agent_id: str,
        url: str,
        context: Dict,
        round_number: int,
        previous_proposals: List[Dict]
    ) -> Optional[Dict]:
        """Get proposal from a single agent"""
        try:
            response = await client.post(
                f"{url}/propose",
                json={
                    "context": context,
                    "round_number": round_number,
                    "opponent_proposals": previous_proposals
                }
            )
            
            if response.status_code == 200:
                proposal = response.json()
                proposal["agent_id"] = agent_id
                return proposal
            else:
                logger.warning(f"Agent {agent_id} returned {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting proposal from {agent_id}: {e}")
            return None
    
    def _get_previous_proposals(self, session_id: str, current_round: int) -> List[Dict]:
        """Get proposals from previous rounds"""
        proposals = []
        
        for round_num in range(1, current_round):
            round_id = f"{session_id}_round_{round_num}"
            data = self.redis.get(f"round:{round_id}")
            if data:
                round_data = json.loads(data)
                proposals.extend(round_data.get("proposals", []))
        
        return proposals
    
    async def evaluate_proposals(
        self,
        session_id: str,
        round_number: int,
        proposals: List[Dict]
    ) -> Dict:
        """Evaluate proposals and check for consensus"""
        if not proposals:
            return {
                "status": "no_proposals",
                "consensus": False,
                "decision": "continue"
            }
        
        # Check if all agents have proposed
        session = self.get_session(session_id)
        if not session:
            return {"status": "error", "consensus": False}
        
        # Evaluate using agents
        agent_urls = {}
        for agent_name in session.agents:
            agent_url = f"http://agent_{agent_name.lower()}:8005"
            agent_urls[agent_name] = agent_url
        
        evaluations = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            
            # Each agent evaluates all other proposals
            for agent_id, url in agent_urls.items():
                for proposal in proposals:
                    if proposal.get("agent_id") != agent_id:
                        task = self._evaluate_proposal_for_agent(
                            client,
                            agent_id,
                            url,
                            proposal
                        )
                        tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error in evaluation: {result}")
                elif result:
                    evaluations.append(result)
        
        # Check consensus
        accepted = sum(1 for e in evaluations if e.get("decision") == "accept")
        total = len(evaluations) if evaluations else 1
        acceptance_rate = accepted / total
        
        consensus_reached = acceptance_rate >= self.CONSENSUS_THRESHOLD
        
        # Check for veto
        vetoed = False
        for e in evaluations:
            if e.get("decision") == "veto":
                vetoed = True
                break
        
        return {
            "status": "complete",
            "consensus": consensus_reached and not vetoed,
            "acceptance_rate": acceptance_rate,
            "evaluations": evaluations,
            "decision": "accept" if consensus_reached and not vetoed else "continue",
            "veto": vetoed
        }
    
    async def _evaluate_proposal_for_agent(
        self,
        client: httpx.AsyncClient,
        agent_id: str,
        url: str,
        proposal: Dict
    ) -> Optional[Dict]:
        """Evaluate a proposal for a specific agent"""
        try:
            response = await client.post(
                f"{url}/evaluate",
                json={"proposal": proposal}
            )
            
            if response.status_code == 200:
                result = response.json()
                result["evaluator_agent"] = agent_id
                result["target_proposal_id"] = proposal.get("proposal_id")
                return result
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error evaluating for {agent_id}: {e}")
            return None
    
    async def complete_round(
        self,
        round_id: str,
        result: Dict
    ) -> Dict:
        """Complete a round and store results"""
        round_data = self.redis.get(f"round:{round_id}")
        if not round_data:
            return {"status": "error", "message": "Round not found"}
        
        round_dict = json.loads(round_data)
        round_dict["status"] = RoundStatus.COMPLETED.value if hasattr(RoundStatus.COMPLETED, 'value') else str(RoundStatus.COMPLETED)
        round_dict["proposals"] = result.get("proposals", round_dict.get("proposals", []))
        round_dict["consensus_reached"] = result.get("consensus", False)
        round_dict["end_time"] = datetime.utcnow().isoformat()
        round_dict["evaluation"] = result
        
        self.redis.set(f"round:{round_id}", json.dumps(round_dict))
        
        return round_dict
    
    # ============================================
    # TRIGGER INTERROGATION
    # ============================================
    
    async def trigger_interrogation(
        self,
        agent_id: str,
        session_id: str,
        style: str = "standard"
    ) -> Dict:
        """Trigger psychological interrogation"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.psychologist_url}/interrogate",
                    json={
                        "agent_id": agent_id,
                        "conversation_history": [],
                        "style": style
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "message": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Error triggering interrogation: {e}")
            return {"status": "error", "message": str(e)}
    
    # ============================================
    # DEADLOCK DETECTION
    # ============================================
    
    def check_deadlock(self, session_id: str, round_number: int) -> bool:
        """Check if negotiation is deadlocked"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Check if max rounds reached
        if round_number >= self.MAX_ROUNDS:
            logger.warning(f"Session {session_id} reached max rounds: {self.MAX_ROUNDS}")
            return True
        
        # Check consecutive rounds without consensus
        key = f"consecutive_no_consensus:{session_id}"
        consecutive = int(self.redis.get(key) or 0)
        
        if consecutive >= 5:
            logger.warning(f"Session {session_id} deadlocked: {consecutive} consecutive no consensus")
            return True
        
        return False
    
    def record_no_consensus(self, session_id: str):
        """Record a round without consensus"""
        key = f"consecutive_no_consensus:{session_id}"
        self.redis.incr(key)
        self.redis.expire(key, 3600)  # Reset after 1 hour
    
    def reset_deadlock_counter(self, session_id: str):
        """Reset deadlock counter"""
        self.redis.delete(f"consecutive_no_consensus:{session_id}")
    
    # ============================================
    # FINAL CONTRACT
    # ============================================

    async def finalize_contract(
            self,
            session_id: str,
            proposals: List[Dict]
    ) -> Dict:
        """Finalize the contract after consensus"""

        # Extraer términos de las propuestas
        terms = []
        for proposal in proposals:
            if "terms" in proposal:
                terms.append(proposal["terms"])

        # Si no hay términos, crear unos por defecto
        if not terms:
            terms = [
                {"phase": "planning"},
                {"phase": "development"},
                {"phase": "testing"},
                {"phase": "deployment"}
            ]

        # Crear state_machine con transitions AUTOMÁTICAS
        state_machine = {
            "states": terms,
            "transitions": {}
        }

        # Generar transiciones automáticas entre estados
        if len(terms) >= 2:
            for i in range(len(terms) - 1):
                # Usar índices como nombres de estado si no tienen nombre
                from_key = f"step_{i}" if i == 0 else f"step_{i}"
                to_key = f"step_{i + 1}"
                state_machine["transitions"][from_key] = to_key

            # Si hay pocos estados, agregar transiciones explícitas
            if len(terms) <= 5:
                state_machine["transitions"] = {}
                for i in range(len(terms) - 1):
                    state_machine["transitions"][f"state_{i}"] = f"state_{i + 1}"

        # Si no hay transiciones, agregar una por defecto
        if not state_machine["transitions"]:
            state_machine["transitions"] = {
                "start": "complete"
            }

        contract = {
            "session_id": session_id,
            "contract_id": f"contract_{session_id}",
            "state_machine": state_machine,
            "proposals": proposals,
            "created_at": datetime.utcnow().isoformat()
        }

        # Enviar al Executor
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.executor_url}/execute",
                    json={
                        "contract_id": contract["contract_id"],
                        "state_machine": state_machine,
                        "environment": "sandbox",
                        "auto_approve": True
                    }
                )

                if response.status_code == 200:
                    execution_result = response.json()
                    return {
                        "status": "success",
                        "contract": contract,
                        "execution": execution_result
                    }
                else:
                    return {
                        "status": "error",
                        "contract": contract,
                        "message": f"Executor failed: {response.status_code} - {response.text}"
                    }

        except Exception as e:
            logger.error(f"Error executing contract: {e}")
            return {
                "status": "error",
                "contract": contract,
                "message": str(e)
            }
