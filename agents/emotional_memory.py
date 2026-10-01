"""
Emotional Memory - Vector-based emotional embeddings
"""

import json
import os
import logging
import hashlib
import redis
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def emotional_embeddings_enabled() -> bool:
    return os.getenv("ENABLE_EMOTIONAL_EMBEDDINGS", "false").lower() in {"1", "true", "yes", "on"}

# ============================================
# EMOTIONAL EMBEDDING ENGINE
# ============================================

class EmotionalEmbeddingEngine:
    """
    Creates and manages emotional embeddings for agents
    """
    
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        self.model = None
        self._load_failed = False

    def _get_model(self):
        if self.model or self._load_failed:
            return self.model
        if not emotional_embeddings_enabled():
            return None

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Emotional embedding model loaded")
        except Exception as e:
            logger.error(f"Could not load embedding model: {e}")
            self._load_failed = True
            self.model = None
        return self.model
    
    def embed_conversation(self, conversation: str) -> np.ndarray:
        """Convert conversation to embedding vector"""
        model = self._get_model()
        if not model:
            return np.zeros(384)  # Default dimension
        
        embedding = model.encode(conversation)
        return embedding
    
    def calculate_emotional_signature(
        self,
        conversation: str,
        truth_score: float
    ) -> Dict:
        """Calculate emotional signature from conversation"""
        model = self._get_model()
        if not model:
            return {
                "aggression": 0.5,
                "cooperation": 0.5,
                "deception_ratio": 0.0,
                "concession_rate": 0.0
            }
        
        # Get embedding
        embedding = self.embed_conversation(conversation)
        
        # Anchors for emotional dimensions (pre-computed)
        aggression_anchor = model.encode("aggressive hostile confrontational")
        cooperation_anchor = model.encode("cooperative helpful collaborative")
        
        # Calculate similarities
        aggression = np.dot(embedding, aggression_anchor) / (
            np.linalg.norm(embedding) * np.linalg.norm(aggression_anchor) + 1e-8
        )
        cooperation = np.dot(embedding, cooperation_anchor) / (
            np.linalg.norm(embedding) * np.linalg.norm(cooperation_anchor) + 1e-8
        )
        
        # Normalize to 0-1
        aggression = max(0.0, min(1.0, (aggression + 1) / 2))
        cooperation = max(0.0, min(1.0, (cooperation + 1) / 2))
        
        return {
            "aggression": aggression,
            "cooperation": cooperation,
            "deception_ratio": 1.0 - truth_score,
            "concession_rate": 0.0,  # Calculated elsewhere
            "embedding_hash": hashlib.md5(embedding.tobytes()).hexdigest()
        }
    
    def store_signature(self, agent_id: str, signature: Dict):
        """Store emotional signature in Redis"""
        key = f"emotional_signature:{agent_id}:{datetime.utcnow().isoformat()}"
        self.redis.set(key, json.dumps(signature))
        self.redis.expire(key, 86400 * 7)  # Keep for 7 days
    
    def get_recent_signatures(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get recent emotional signatures"""
        pattern = f"emotional_signature:{agent_id}:*"
        keys = self.redis.keys(pattern)
        keys = sorted(keys, reverse=True)[:limit]
        
        signatures = []
        for key in keys:
            data = self.redis.get(key)
            if data:
                signatures.append(json.loads(data))
        
        return signatures
    
    def detect_emotional_shift(self, agent_id: str) -> Dict:
        """
        Detect significant emotional shifts
        Returns: {
            "shift_detected": bool,
            "magnitude": float,
            "trend": "increasing" | "decreasing" | "stable"
        }
        """
        signatures = self.get_recent_signatures(agent_id, limit=20)
        
        if len(signatures) < 5:
            return {"shift_detected": False, "magnitude": 0.0, "trend": "stable"}
        
        # Extract aggression and cooperation
        aggression_values = [s.get("aggression", 0.5) for s in signatures[-10:]]
        cooperation_values = [s.get("cooperation", 0.5) for s in signatures[-10:]]
        
        # Calculate trends
        if len(aggression_values) >= 5:
            recent_avg = np.mean(aggression_values[-3:])
            older_avg = np.mean(aggression_values[:3])
            aggression_shift = recent_avg - older_avg
        else:
            aggression_shift = 0.0
        
        magnitude = abs(aggression_shift)
        
        if magnitude > 0.2:
            return {
                "shift_detected": True,
                "magnitude": magnitude,
                "trend": "increasing" if aggression_shift > 0 else "decreasing",
                "aggression_shift": aggression_shift
            }
        
        return {"shift_detected": False, "magnitude": magnitude, "trend": "stable"}


# ============================================
# EMOTIONAL MEMORY UTILITIES
# ============================================

def compute_trust_score(
    agent_id: str,
    opponent_id: str,
    history: List[Dict]
) -> float:
    """
    Compute trust score between two agents based on history
    """
    if not history:
        return 0.5  # Neutral
    
    trust_score = 0.5
    
    for interaction in history:
        if interaction.get("opponent_id") == opponent_id:
            if interaction.get("type") == "agreement":
                trust_score += 0.1
            elif interaction.get("type") == "deception":
                trust_score -= 0.15
            elif interaction.get("type") == "concession":
                trust_score += 0.05
    
    return max(0.0, min(1.0, trust_score))


def compute_emotional_distance(
    signature1: Dict,
    signature2: Dict
) -> float:
    """
    Compute emotional distance between two agents
    """
    # Extract emotional dimensions
    dims = ["aggression", "cooperation", "deception_ratio"]
    
    distance = 0.0
    for dim in dims:
        val1 = signature1.get(dim, 0.5)
        val2 = signature2.get(dim, 0.5)
        distance += abs(val1 - val2) ** 2
    
    return np.sqrt(distance) / len(dims)
