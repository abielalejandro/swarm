"""
Negotiation Strategy - Adaptive strategy engine
"""

import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# STRATEGY TYPES
# ============================================

STRATEGY_TYPES = {
    "aggressive": {
        "description": "Hard negotiation, minimal concessions",
        "concession_rate": 0.05,
        "aggression_bonus": 0.3
    },
    "cooperative": {
        "description": "Collaborative, open to compromise",
        "concession_rate": 0.15,
        "aggression_bonus": -0.2
    },
    "balanced": {
        "description": "Fair negotiation, moderate concessions",
        "concession_rate": 0.10,
        "aggression_bonus": 0.0
    },
    "conservative": {
        "description": "Slow negotiation, cautious concessions",
        "concession_rate": 0.03,
        "aggression_bonus": 0.1
    },
    "opportunistic": {
        "description": "Adaptive, changes strategy based on context",
        "concession_rate": 0.12,
        "aggression_bonus": 0.1
    }
}


class NegotiationStrategy:
    """
    Adaptive negotiation strategy engine
    """
    
    def __init__(self, agent_id: str, domain: str):
        self.agent_id = agent_id
        self.domain = domain
        self.current_strategy = "balanced"
        self.strategy_history = []
        
        logger.info(f"Negotiation strategy initialized for {agent_id}")
    
    def select_strategy(
        self,
        round_number: int,
        emotional_state: Dict,
        opponent_behavior: Dict,
        previous_outcomes: List[Dict]
    ) -> str:
        """Select best strategy based on current context"""
        
        # Early rounds: exploratory
        if round_number <= 2:
            return "balanced"
        
        # Late rounds: adapt based on progress
        if round_number >= 10:
            # Check if many proposals have been rejected
            rejections = sum(1 for o in previous_outcomes if o.get("decision") == "reject")
            if rejections > len(previous_outcomes) * 0.6:
                return "conservative"  # Deadlock - slow down
            
            # Check if concessions are happening
            concessions = sum(1 for o in previous_outcomes if o.get("concession"))
            if concessions > 0:
                return "cooperative"  # Progress - be more collaborative
        
        # Emotional state influence
        aggression = emotional_state.get("aggression", 0.5)
        cooperation = emotional_state.get("cooperation", 0.5)
        
        if aggression > 0.7 and cooperation < 0.4:
            return "aggressive"
        elif cooperation > 0.7 and aggression < 0.4:
            return "cooperative"
        elif aggression > 0.6 and cooperation > 0.6:
            return "opportunistic"
        
        return self.current_strategy
    
    def calculate_concession(
        self,
        strategy: str,
        base_value: float,
        round_number: int,
        opponent_strength: float
    ) -> float:
        """Calculate concession amount based on strategy"""
        
        strategy_config = STRATEGY_TYPES.get(strategy, STRATEGY_TYPES["balanced"])
        base_concession = strategy_config["concession_rate"]
        
        # Adjust by round number (more concessions later)
        round_factor = 1.0 + (round_number / 20)
        
        # Adjust by opponent strength
        opponent_factor = 1.0 - (opponent_strength * 0.2)
        
        # Final concession
        concession = base_value * base_concession * round_factor * opponent_factor
        
        return min(concession, base_value * 0.3)  # Max 30% concession
    
    def get_aggression_level(self, strategy: str) -> float:
        """Get aggression level for a strategy"""
        config = STRATEGY_TYPES.get(strategy, STRATEGY_TYPES["balanced"])
        return 0.5 + config["aggression_bonus"]
    
    def recommend_ally(self, agents: List[Dict]) -> Optional[str]:
        """
        Recommend an ally based on domain compatibility
        """
        # Domain compatibility mapping
        compatibility = {
            "Engineering": ["DevOps", "Security"],
            "Finance": ["Security", "Legal"],
            "Security": ["Legal", "DevOps"],
            "DevOps": ["Engineering", "Security"],
            "Legal": ["Security", "Finance"]
        }
        
        preferred = compatibility.get(self.domain, [])
        
        for agent in agents:
            if agent.get("domain") in preferred:
                return agent.get("agent_id")
        
        return None
    
    def log_strategy_change(self, old_strategy: str, new_strategy: str, reason: str):
        """Log strategy changes for analysis"""
        self.strategy_history.append({
            "old_strategy": old_strategy,
            "new_strategy": new_strategy,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.current_strategy = new_strategy
        logger.info(f"Strategy changed: {old_strategy} -> {new_strategy} ({reason})")


# ============================================
# UTILITY FUNCTIONS
# ============================================

def calculate_bargaining_power(
    stake: float,
    weight: float,
    emotional_state: Dict
) -> float:
    """
    Calculate agent's bargaining power
    """
    # Stake contributes power
    stake_power = stake * 0.3
    
    # Weight contributes power
    weight_power = weight * 0.3
    
    # Confidence contributes power
    confidence = emotional_state.get("confidence", 0.5)
    confidence_power = confidence * 0.2
    
    # Aggression contributes power (but too much is bad)
    aggression = emotional_state.get("aggression", 0.5)
    aggression_power = min(aggression, 0.8) * 0.2
    
    total_power = stake_power + weight_power + confidence_power + aggression_power
    
    return min(1.0, total_power)


def determine_negotiation_outcome(
    proposals: List[Dict],
    threshold: float = 0.6
) -> Dict:
    """
    Determine outcome of a negotiation round
    """
    if not proposals:
        return {"status": "no_proposals", "consensus": False}
    
    # Calculate average value
    values = [p.get("proposed_value", 0) for p in proposals if p.get("proposed_value")]
    if not values:
        return {"status": "no_values", "consensus": False}
    
    avg_value = sum(values) / len(values)
    max_value = max(values)
    min_value = min(values)
    
    # Check consensus (values within threshold of average)
    consensus = True
    for v in values:
        if abs(v - avg_value) / avg_value > (1 - threshold):
            consensus = False
            break
    
    return {
        "status": "complete",
        "consensus": consensus,
        "avg_value": avg_value,
        "max_value": max_value,
        "min_value": min_value,
        "spread": max_value - min_value,
        "recommendation": "Accept" if consensus else "Continue negotiating"
    }