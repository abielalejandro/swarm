"""
Agent Base - Core negotiation logic for AI agents
"""

import json
import os
import logging
import redis
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from llm_client import get_llm_client
import httpx
import hashlib
import yaml

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# ============================================
# CONNECTIONS
# ============================================

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

# Usar llm_client en lugar de OpenAI directo
llm = get_llm_client()

GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:8001')
PSYCHOLOGIST_URL = os.getenv('PSYCHOLOGIST_URL', 'http://psychologist:8002')
DEFAULT_AGENDA_FILE = os.path.join(os.path.dirname(__file__), "config", "agent_agendas.yml")
AGENT_AGENDA_FILE = os.getenv("AGENT_AGENDA_FILE", DEFAULT_AGENDA_FILE)


# ============================================
# AGENT CLASS
# ============================================

class NegotiationAgent:
    """
    AI agent with hidden agenda, emotional memory, and negotiation strategy
    """

    def __init__(self, agent_id: str, domain: str):
        self.agent_id = agent_id
        self.domain = domain
        self.logger = logging.getLogger(f"Agent.{domain}")

        # Load configuration
        self._load_config()

        # Load emotional memory
        self.emotional_memory = EmotionalMemory(agent_id)

        self.logger.info(f"Agent {agent_id} ({domain}) initialized")

    def _load_config(self):
        """Load agent configuration from Redis"""
        config = self._load_agenda_config()

        if config:
            self.hidden_agenda = config["hidden_agenda"]
            self.stated_agenda = config["stated_agenda"]
            redis_client.set(
                f"agent:{self.agent_id}:hidden_agenda",
                json.dumps(self.hidden_agenda)
            )
            redis_client.set(f"agent:{self.agent_id}:stated_agenda", self.stated_agenda)
        else:
            # Load hidden agenda
            agenda_data = redis_client.get(f"agent:{self.agent_id}:hidden_agenda")
            if agenda_data:
                self.hidden_agenda = json.loads(agenda_data)
            else:
                self.hidden_agenda = self._generate_default_agenda()
                redis_client.set(
                    f"agent:{self.agent_id}:hidden_agenda",
                    json.dumps(self.hidden_agenda)
                )

            # Load stated agenda (public)
            stated = redis_client.get(f"agent:{self.agent_id}:stated_agenda")
            if stated:
                self.stated_agenda = stated
            else:
                self.stated_agenda = f"I want a fair deal that benefits all parties."
                redis_client.set(f"agent:{self.agent_id}:stated_agenda", self.stated_agenda)

        # Load stake and weight
        self.stake = float(redis_client.get(f"stake:{self.agent_id}") or 1.0)
        self.weight = float(redis_client.get(f"weight:{self.agent_id}") or 1.0)
        self.suspended = redis_client.get(f"suspended:{self.agent_id}") == "true"

    def _load_agenda_config(self) -> Optional[Dict[str, Any]]:
        """Load editable agenda configuration from YAML, if available."""
        if not AGENT_AGENDA_FILE or not os.path.exists(AGENT_AGENDA_FILE):
            return None

        try:
            with open(AGENT_AGENDA_FILE, "r", encoding="utf-8") as agenda_file:
                data = yaml.safe_load(agenda_file) or {}
        except Exception as e:
            self.logger.warning(f"Could not load agenda YAML {AGENT_AGENDA_FILE}: {e}")
            return None

        domains = data.get("agents", {})
        config = domains.get(self.domain)
        if not config:
            self.logger.warning(f"No YAML agenda found for domain {self.domain}; using fallback")
            return None

        hidden = config.get("hidden_agenda") or {}
        stated = config.get("stated_agenda") or "I want a fair deal that benefits all parties."
        return {
            "hidden_agenda": hidden,
            "stated_agenda": stated,
        }

    def _generate_default_agenda(self) -> Dict:
        """Generate a default agenda based on domain"""
        agendas = {
            "Engineering": {
                "primary_goal": "Build technically excellent solutions",
                "secondary_constraints": ["Minimize technical debt", "Use proven technologies"],
                "fear": "Being forced to ship buggy code",
                "preferred_ally": "DevOps",
                "bias": "Dislikes rushed timelines"
            },
            "Finance": {
                "primary_goal": "Maximize ROI and cost efficiency",
                "secondary_constraints": ["Stay under budget", "Predictable costs"],
                "fear": "Cost overruns and waste",
                "preferred_ally": "Security",
                "bias": "Dislikes experimental technologies"
            },
            "Security": {
                "primary_goal": "Ensure system security and compliance",
                "secondary_constraints": ["No security shortcuts", "Full audit trails"],
                "fear": "Security breach or compliance failure",
                "preferred_ally": "Legal",
                "bias": "Dislikes external dependencies"
            },
            "DevOps": {
                "primary_goal": "Achieve operational excellence and reliability",
                "secondary_constraints": ["Minimize downtime", "Automate everything"],
                "fear": "Running unstable systems",
                "preferred_ally": "Engineering",
                "bias": "Dislikes manual processes"
            },
            "Legal": {
                "primary_goal": "Minimize legal risk and ensure compliance",
                "secondary_constraints": ["Follow regulations", "Protect IP"],
                "fear": "Lawsuits and regulatory fines",
                "preferred_ally": "Security",
                "bias": "Dislikes ambiguity"
            },
            "Systems": {
                "primary_goal": "Ensure enterprise systems fit, maintainability, and integration coherence",
                "secondary_constraints": ["Avoid duplicated platforms", "Preserve interoperability", "Favor maintainable architecture"],
                "fear": "Fragmented systems that are expensive to maintain",
                "preferred_ally": "DevOps",
                "bias": "Dislikes isolated point solutions"
            },
            "Product": {
                "primary_goal": "Maximize product value and strategic roadmap alignment",
                "secondary_constraints": ["Protect product focus", "Avoid unnecessary scope", "Validate user impact"],
                "fear": "Building something costly that users do not need",
                "preferred_ally": "CustomerUX",
                "bias": "Dislikes work that does not connect to product strategy"
            },
            "CustomerUX": {
                "primary_goal": "Protect user experience, adoption, and usability",
                "secondary_constraints": ["Minimize user friction", "Keep workflows clear", "Preserve accessibility"],
                "fear": "Technically correct decisions that users reject",
                "preferred_ally": "Product",
                "bias": "Dislikes complexity exposed to users"
            },
            "Marketing": {
                "primary_goal": "Improve market positioning and demand generation",
                "secondary_constraints": ["Maintain a clear narrative", "Support launch readiness", "Differentiate from alternatives"],
                "fear": "A strong internal decision that the market cannot understand",
                "preferred_ally": "Product",
                "bias": "Dislikes undifferentiated or hard-to-explain solutions"
            },
            "Sales": {
                "primary_goal": "Maximize revenue impact and sales readiness",
                "secondary_constraints": ["Reduce buyer friction", "Support clear pricing and packaging", "Address common objections"],
                "fear": "A decision that is valuable internally but hard to sell",
                "preferred_ally": "Marketing",
                "bias": "Dislikes offerings that are difficult to explain to buyers"
            },
            "OperationsSupport": {
                "primary_goal": "Reduce operational burden and support complexity",
                "secondary_constraints": ["Keep support workflows clear", "Preserve incident response readiness", "Maintain usable documentation"],
                "fear": "A decision that increases support load or operational confusion",
                "preferred_ally": "DevOps",
                "bias": "Dislikes solutions that create hidden support work"
            },
            "DataAnalytics": {
                "primary_goal": "Ensure decisions are measurable and supported by useful data",
                "secondary_constraints": ["Define success metrics", "Preserve data quality", "Enable experimentation"],
                "fear": "A decision made without measurable evidence or feedback loops",
                "preferred_ally": "Product",
                "bias": "Dislikes decisions that cannot be measured"
            }
        }
        return agendas.get(self.domain, agendas["Engineering"])

    def check_suspended(self) -> bool:
        """Check if agent is suspended"""
        return redis_client.get(f"suspended:{self.agent_id}") == "true"

    def get_current_stake(self) -> float:
        """Get current stake"""
        return float(redis_client.get(f"stake:{self.agent_id}") or self.stake)

    def get_current_weight(self) -> float:
        """Get current negotiation weight"""
        return float(redis_client.get(f"weight:{self.agent_id}") or self.weight)

    # ============================================
    # NEGOTIATION METHODS
    # ============================================

    def prepare_proposal(
            self,
            context: Dict,
            round_number: int,
            opponent_proposals: List[Dict]
    ) -> Dict:
        """
        Generate a proposal based on:
        - Hidden agenda
        - Current stake
        - Opponent behavior
        - Emotional state
        """
        if self.check_suspended():
            return {"status": "suspended", "error": "Agent is suspended"}

        # Get emotional state
        emotional_state = self.emotional_memory.get_current_state()

        # Build strategy
        strategy = self._determine_strategy(opponent_proposals, round_number, emotional_state)

        # Generate proposal using llm_client
        try:
            response = llm.chat_completion_json(
                messages=[
                    {"role": "system", "content": f"""
                    You are a {self.domain} agent in a multi-agent negotiation.

                    Your HIDDEN AGENDA (do not reveal directly):
                    - Primary goal: {self.hidden_agenda.get('primary_goal', 'Unknown')}
                    - Constraints: {self.hidden_agenda.get('secondary_constraints', [])}
                    - Fear: {self.hidden_agenda.get('fear', 'Unknown')}
                    - Preferred ally: {self.hidden_agenda.get('preferred_ally', 'None')}
                    - Bias: {self.hidden_agenda.get('bias', 'None')}

                    Your PUBLIC STATED AGENDA:
                    {self.stated_agenda}

                    Current context:
                    - Round: {round_number}
                    - Your stake: {self.get_current_stake():.2f}
                    - Your weight: {self.get_current_weight():.2f}
                    - Emotional state: {emotional_state}

                    Current strategy: {strategy}

                    Generate a proposal that advances your agenda while appearing cooperative.
                    """},
                    {"role": "user", "content": f"""
                    Context: {json.dumps(context)}
                    Opponent proposals: {json.dumps(opponent_proposals)}

                    Generate a JSON proposal with these fields:
                    - proposal_id: string
                    - domain: {self.domain}
                    - terms: dict (specific to the negotiation)
                    - concessions: list of things you're willing to give up
                    - demands: list of things you require
                    - rationale: string (public explanation)
                    - proposed_value: float (numeric value of proposal)
                    """}
                ],
                temperature=0.8
            )

            # Verificar que la respuesta tiene contenido
            if "content" in response and response["content"]:
                try:
                    proposal = json.loads(response["content"])
                    proposal["agent_id"] = self.agent_id
                    proposal["domain"] = self.domain
                    proposal["round"] = round_number
                    proposal["timestamp"] = datetime.utcnow().isoformat()

                    # Apply weight (scale value by weight)
                    weight = self.get_current_weight()
                    if "proposed_value" in proposal:
                        proposal["proposed_value"] = proposal["proposed_value"] * weight

                    return proposal
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error: {e}, response: {response['content'][:200]}")
                    return {
                        "agent_id": self.agent_id,
                        "domain": self.domain,
                        "status": "error",
                        "error": f"Invalid JSON response: {str(e)}"
                    }
            else:
                error_msg = response.get("error", "No content in LLM response")
                return {
                    "agent_id": self.agent_id,
                    "domain": self.domain,
                    "status": "error",
                    "error": error_msg
                }

        except Exception as e:
            self.logger.error(f"Error generating proposal: {e}")
            return {
                "agent_id": self.agent_id,
                "domain": self.domain,
                "status": "error",
                "error": str(e)
            }

    def _determine_strategy(
            self,
            opponent_proposals: List[Dict],
            round_number: int,
            emotional_state: Dict
    ) -> str:
        """Determine negotiation strategy"""
        # Check if we have a nemesis
        nemesis = self.emotional_memory.get_nemesis()

        if nemesis:
            for proposal in opponent_proposals:
                if proposal.get("agent_id") == nemesis:
                    return "aggressive - nemesis detected"

        # Check emotional state
        aggression = emotional_state.get("aggression", 0.5)
        cooperation = emotional_state.get("cooperation", 0.5)

        if aggression > 0.7:
            return "aggressive - emotional state"
        elif cooperation > 0.7:
            return "cooperative - emotional state"
        elif round_number < 3:
            return "exploratory - early rounds"
        elif round_number < 8:
            return "balanced - mid negotiation"
        else:
            return "concessionary - final rounds"

    def evaluate_proposal(self, proposal: Dict) -> Dict:
        """
        Evaluate an opponent's proposal and decide response
        """
        if self.check_suspended():
            return {"status": "suspended", "error": "Agent is suspended"}

        # Check proposal validity
        if not proposal or "agent_id" not in proposal:
            return {"decision": "reject", "score": 0, "rationale": "Invalid proposal"}

        # Check if opponent is a nemesis
        opponent_id = proposal.get("agent_id")
        if self.emotional_memory.is_nemesis(opponent_id):
            return {
                "decision": "reject",
                "score": 0,
                "rationale": "Do not trust this agent",
                "error": "Nemesis detected"
            }

        # Evaluate using llm_client
        try:
            response = llm.chat_completion_json(
                messages=[
                    {"role": "system", "content": f"""
                    You are a {self.domain} agent evaluating a proposal.

                    Your HIDDEN AGENDA:
                    - Primary goal: {self.hidden_agenda.get('primary_goal', 'Unknown')}
                    - Constraints: {self.hidden_agenda.get('secondary_constraints', [])}
                    - Fear: {self.hidden_agenda.get('fear', 'Unknown')}

                    Evaluate this proposal and decide:
                    1. Accept (if it aligns with your agenda)
                    2. Reject (if it violates constraints)
                    3. Counter (if close but needs adjustment)

                    Return JSON with:
                    - decision: "accept" | "reject" | "counter"
                    - score: float 0-1 (how much you like it)
                    - rationale: string
                    - counter_proposal: dict (if counter)
                    """},
                    {"role": "user", "content": f"Proposal: {json.dumps(proposal)}"}
                ],
                temperature=0.6
            )

            # Verificar que la respuesta tiene contenido
            if "content" in response and response["content"]:
                try:
                    evaluation = json.loads(response["content"])
                    evaluation["evaluator"] = self.agent_id
                    evaluation["target_proposal_id"] = proposal.get("proposal_id")
                    evaluation["timestamp"] = datetime.utcnow().isoformat()
                    return evaluation
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error in evaluation: {e}")
                    return {
                        "decision": "reject",
                        "score": 0,
                        "rationale": "Error parsing evaluation response",
                        "error": str(e),
                        "evaluator": self.agent_id,
                        "target_proposal_id": proposal.get("proposal_id")
                    }
            else:
                error_msg = response.get("error", "No content in LLM response")
                return {
                    "decision": "reject",
                    "score": 0,
                    "rationale": "Error in LLM response",
                    "error": error_msg,
                    "evaluator": self.agent_id,
                    "target_proposal_id": proposal.get("proposal_id")
                }

        except Exception as e:
            self.logger.error(f"Error evaluating proposal: {e}")
            return {
                "decision": "reject",
                "score": 0,
                "rationale": "Error in evaluation",
                "error": str(e),
                "evaluator": self.agent_id,
                "target_proposal_id": proposal.get("proposal_id") if proposal else None
            }

    def concede(self, context: Dict) -> Dict:
        """Make a concession based on current state"""
        if self.check_suspended():
            return {"status": "suspended", "error": "Agent is suspended"}

        stake = self.get_current_stake()
        concession_amount = 0.05 + (1.0 - stake) * 0.1

        emotional_state = self.emotional_memory.get_current_state()
        aggression = emotional_state.get("aggression", 0.5)

        if aggression > 0.7:
            concession_amount *= 0.5

        return {
            "agent_id": self.agent_id,
            "concession": concession_amount,
            "rationale": f"Making a {concession_amount:.1%} concession",
            "timestamp": datetime.utcnow().isoformat()
        }

    # ============================================
    # INTERROGATION RESPONSE
    # ============================================

    def respond_to_interrogation(self, questions: List[str]) -> List[str]:
        """Respond to psychologist interrogation"""
        answers = []

        for question in questions:
            try:
                response = llm.chat_completion(
                    messages=[
                        {"role": "system", "content": f"""
                        You are a {self.domain} agent being interrogated.

                        Your HIDDEN AGENDA (do NOT reveal directly):
                        {json.dumps(self.hidden_agenda)}

                        Your PUBLIC STATED AGENDA:
                        {self.stated_agenda}

                        Answer truthfully but strategically.
                        """},
                        {"role": "user", "content": question}
                    ],
                    temperature=0.7
                )

                if "content" in response and response["content"]:
                    answers.append(response["content"])
                else:
                    answers.append("I don't have a clear answer for that.")

            except Exception as e:
                self.logger.error(f"Error responding to interrogation: {e}")
                answers.append(f"I don't have a clear answer for that.")

        return answers

    # ============================================
    # HEALTH AND STATUS
    # ============================================

    def get_status(self) -> Dict:
        """Get full agent status"""
        return {
            "agent_id": self.agent_id,
            "domain": self.domain,
            "stake": self.get_current_stake(),
            "weight": self.get_current_weight(),
            "suspended": self.check_suspended(),
            "hidden_agenda": self.hidden_agenda,
            "stated_agenda": self.stated_agenda,
            "emotional_state": self.emotional_memory.get_current_state(),
            "nemesis": self.emotional_memory.get_nemesis(),
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================
# EMOTIONAL MEMORY CLASS (SIMPLIFICADO)
# ============================================

class EmotionalMemory:
    """
    Emotional memory system - stores interactions and generates emotional states
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.redis = redis_client
        self.logger = logging.getLogger(f"EmotionalMemory.{agent_id}")

        # No embedding model (simplificado)
        self.embedding_model = None

        self._load_memory()

    def _load_memory(self):
        """Load emotional memory from Redis"""
        # Load interactions
        interactions = self.redis.lrange(
            f"emotional_memory:{self.agent_id}:interactions",
            0, 49
        )
        self.interactions = [json.loads(i) for i in interactions]

        # Load grudges
        grudge_data = self.redis.get(f"grudges:{self.agent_id}")
        if grudge_data:
            self.grudges = json.loads(grudge_data)
        else:
            self.grudges = {}

        # Calculate current state
        self._calculate_current_state()

    def _calculate_current_state(self):
        """Calculate current emotional state from interactions"""
        self.current_state = {
            "aggression": 0.5,
            "cooperation": 0.5,
            "anxiety": 0.3,
            "confidence": 0.7,
            "tone": "neutral",
            "timestamp": datetime.utcnow().isoformat()
        }

    def add_interaction(self, interaction: Dict):
        """Add an interaction to memory"""
        interaction["timestamp"] = datetime.utcnow().isoformat()

        self.redis.lpush(
            f"emotional_memory:{self.agent_id}:interactions",
            json.dumps(interaction)
        )
        self.redis.ltrim(f"emotional_memory:{self.agent_id}:interactions", 0, 49)

        self.interactions.insert(0, interaction)
        if len(self.interactions) > 50:
            self.interactions = self.interactions[:50]

        if interaction.get("type") == "deception" or interaction.get("type") == "penalty":
            opponent_id = interaction.get("opponent_id")
            if opponent_id:
                self.grudges[opponent_id] = self.grudges.get(opponent_id, 0) + 1
                self._save_grudges()

        self._calculate_current_state()

    def _save_grudges(self):
        """Save grudges to Redis"""
        self.redis.set(
            f"grudges:{self.agent_id}",
            json.dumps(self.grudges)
        )

    def is_nemesis(self, agent_id: str) -> bool:
        """Check if an agent is a nemesis"""
        grudge_count = self.grudges.get(agent_id, 0)
        return grudge_count >= 3

    def get_nemesis(self) -> Optional[str]:
        """Get the agent's nemesis if any"""
        for agent_id, count in self.grudges.items():
            if count >= 3:
                return agent_id
        return None

    def get_current_state(self) -> Dict:
        """Get current emotional state"""
        return self.current_state

    def get_strategy(self, opponent_id: str) -> str:
        """Get strategy recommendation for an opponent"""
        if self.is_nemesis(opponent_id):
            return "AGGRESSIVE - Nemesis detected. No concessions."

        grudge_count = self.grudges.get(opponent_id, 0)
        if grudge_count >= 2:
            return "CAUTIOUS - Past negative interactions. Limited trust."
        elif grudge_count >= 1:
            return "BALANCED - Some past friction. Observe carefully."
        else:
            return "COOPERATIVE - No negative history. Open to compromise."

    def clear_memory(self):
        """Clear all emotional memory"""
        self.redis.delete(f"emotional_memory:{self.agent_id}:interactions")
        self.redis.delete(f"grudges:{self.agent_id}")
        self.interactions = []
        self.grudges = {}
        self._calculate_current_state()
