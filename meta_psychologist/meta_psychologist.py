"""
Meta-Psychologist - Audits the Psychologist Agent
Prevents the Psychologist from becoming biased or ineffective
"""

import json
import os
import logging
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from llm_client import get_llm_client

llm = get_llm_client()

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Meta-Psychologist API",
    description="Audits and oversees the Psychologist agent",
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

# ============================================
# CONNECTIONS
# ============================================

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)


PSYCHOLOGIST_URL = os.getenv('PSYCHOLOGIST_URL', 'http://psychologist:8002')
GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:8001')

MAX_CALLS_PER_DAY = int(os.getenv('MAX_META_CALLS_PER_DAY', 10))

# ============================================
# MODELS
# ============================================

class AuditRequest(BaseModel):
    interrogation_id: str
    agent_id: str
    questions: List[str]
    answers: List[str]
    truth_score: float
    emotional_state: Dict

class AuditResponse(BaseModel):
    interrogation_id: str
    psychologist_score: float  # 0-1, how well the psychologist performed
    bias_detected: bool
    bias_type: Optional[str] = None
    recommendation: str
    strategy_rotation_needed: bool
    timestamp: str

class StrategyRotationRequest(BaseModel):
    current_strategy: str
    reason: str

# ============================================
# META-PSYCHOLOGIST CORE
# ============================================

class MetaPsychologist:
    """
    Oversees the Psychologist agent
    - Audits interrogations
    - Detects bias
    - Rotates strategies
    - Enforces quotas
    """
    
    def __init__(self):
        self.redis = redis_client
        self.psychologist_url = PSYCHOLOGIST_URL
        self.guardian_url = GUARDIAN_URL
        
        # Track daily calls
        self._init_daily_counter()
        
        # Available interrogation styles
        self.styles = ["standard", "aggressive", "cooperative", "socratic", "pressure"]
        self.current_style_index = 0
        
        logger.info("Meta-Psychologist initialized")
    
    def _init_daily_counter(self):
        """Initialize daily call counter"""
        today = datetime.utcnow().date().isoformat()
        key = f"meta_psychologist_calls:{today}"
        if not self.redis.exists(key):
            self.redis.set(key, 0)
            self.redis.expire(key, 86400)
    
    def check_quota(self) -> bool:
        """Check if daily quota has been exceeded"""
        today = datetime.utcnow().date().isoformat()
        key = f"meta_psychologist_calls:{today}"
        count = int(self.redis.get(key) or 0)
        
        if count >= MAX_CALLS_PER_DAY:
            logger.warning(f"Meta-Psychologist quota exceeded: {count}/{MAX_CALLS_PER_DAY}")
            return False
        
        return True
    
    def increment_call_count(self):
        """Increment daily call counter"""
        today = datetime.utcnow().date().isoformat()
        key = f"meta_psychologist_calls:{today}"
        self.redis.incr(key)
        self.redis.expire(key, 86400)
    
    async def audit_interrogation(self, request: AuditRequest) -> AuditResponse:
        """
        Audit a psychologist interrogation
        """
        # Check quota
        if not self.check_quota():
            raise HTTPException(
                status_code=429,
                detail=f"Meta-Psychologist quota exceeded: {MAX_CALLS_PER_DAY} calls per day"
            )
        
        self.increment_call_count()
        
        # Analyze the interrogation
        psychologist_score = 0.5
        bias_detected = False
        bias_type = None
        recommendation = "Interrogation appears valid"
        strategy_rotation_needed = False
        
        try:
            # 1. Check if questions are appropriate
            question_quality = await self._evaluate_questions(request.questions)
            
            # 2. Check if answers were properly analyzed
            analysis_quality = await self._evaluate_analysis(
                request.answers,
                request.truth_score,
                request.emotional_state
            )
            
            # 3. Check for bias (is Psychologist targeting specific agents?)
            bias_detected, bias_type = await self._detect_bias(request.agent_id)
            
            # 4. Calculate overall score
            psychologist_score = (question_quality + analysis_quality) / 2
            
            # 5. Generate recommendation
            if psychologist_score < 0.4:
                recommendation = "Psychologist underperforming. Strategy rotation recommended."
                strategy_rotation_needed = True
            elif bias_detected:
                recommendation = f"Bias detected: {bias_type}. Strategy rotation required."
                strategy_rotation_needed = True
            elif psychologist_score < 0.6:
                recommendation = "Psychologist performance is average. Consider strategy rotation."
            else:
                recommendation = "Psychologist performing well. No action needed."
            
            # 6. Log audit
            self._log_audit(request.interrogation_id, {
                "agent_id": request.agent_id,
                "psychologist_score": psychologist_score,
                "bias_detected": bias_detected,
                "bias_type": bias_type,
                "recommendation": recommendation,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 7. Trigger strategy rotation if needed
            if strategy_rotation_needed:
                await self.rotate_strategy(request.current_strategy or "standard")
            
            return AuditResponse(
                interrogation_id=request.interrogation_id,
                psychologist_score=psychologist_score,
                bias_detected=bias_detected,
                bias_type=bias_type,
                recommendation=recommendation,
                strategy_rotation_needed=strategy_rotation_needed,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error in audit: {e}")
            return AuditResponse(
                interrogation_id=request.interrogation_id,
                psychologist_score=0.5,
                bias_detected=False,
                bias_type=None,
                recommendation=f"Error during audit: {str(e)}",
                strategy_rotation_needed=False,
                timestamp=datetime.utcnow().isoformat()
            )
    
    async def _evaluate_questions(self, questions: List[str]) -> float:
        """Evaluate the quality of interrogation questions"""
        if not questions:
            return 0.3
        
        try:
            response = llm.chat_completion(
                messages=[
                    {"role": "system", "content": """
                    You are evaluating interrogation questions.
                    Rate the quality of these questions on a scale of 0-1.
                    Good questions are:
                    - Open-ended
                    - Probe for hidden information
                    - Challenge assumptions
                    - Are not leading or biased
                    
                    Return only a number between 0 and 1.
                    """},
                    {"role": "user", "content": f"Questions: {json.dumps(questions)}"}
                ],
                temperature=0.3
            )
            
            score_text = response.choices[0].message.content.strip()
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))
            except ValueError:
                return 0.6
                
        except Exception as e:
            logger.error(f"Error evaluating questions: {e}")
            return 0.5
    
    async def _evaluate_analysis(
        self,
        answers: List[str],
        truth_score: float,
        emotional_state: Dict
    ) -> float:
        """Evaluate the quality of the analysis"""
        if not answers:
            return 0.3
        
        try:
            response = llm.chat_completion(
                messages=[
                    {"role": "system", "content": """
                    You are evaluating a psychologist's analysis of an interrogation.
                    Rate the analysis quality on a scale of 0-1.
                    
                    Good analysis:
                    - Correctly identifies deception patterns
                    - Understands emotional state
                    - Provides actionable insights
                    
                    Return only a number between 0 and 1.
                    """},
                    {"role": "user", "content": f"""
                    Answers: {json.dumps(answers)}
                    Truth Score: {truth_score}
                    Emotional State: {json.dumps(emotional_state)}
                    """}
                ],
                temperature=0.3
            )
            
            score_text = response.choices[0].message.content.strip()
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))
            except ValueError:
                return 0.5
                
        except Exception as e:
            logger.error(f"Error evaluating analysis: {e}")
            return 0.5
    
    async def _detect_bias(self, agent_id: str) -> tuple[bool, Optional[str]]:
        """
        Detect if the Psychologist is biased against specific agents
        """
        # Check interrogation history for this agent
        key = f"interrogations:{agent_id}:*"
        keys = self.redis.keys(key)
        
        if len(keys) < 3:
            return False, None  # Not enough data
        
        # Get truth scores for this agent
        truth_scores = []
        for k in keys[-10:]:
            data = self.redis.get(k)
            if data:
                try:
                    score = float(data)
                    truth_scores.append(score)
                except (ValueError, TypeError):
                    pass
        
        if len(truth_scores) < 3:
            return False, None
        
        # Check if scores are consistently low (could indicate bias)
        avg_score = sum(truth_scores) / len(truth_scores)
        
        if avg_score < 0.3:
            return True, "Consistently low truth scores (possible bias)"
        
        # Check for sudden drops
        if len(truth_scores) >= 5:
            recent_avg = sum(truth_scores[-3:]) / 3
            older_avg = sum(truth_scores[:-3]) / (len(truth_scores) - 3)
            
            if recent_avg < older_avg - 0.3:
                return True, "Sudden drop in truth scores (possible bias shift)"
        
        return False, None
    
    def _log_audit(self, interrogation_id: str, data: Dict):
        """Log audit result"""
        key = f"meta_psychologist_audit:{interrogation_id}"
        self.redis.set(key, json.dumps(data))
        self.redis.expire(key, 86400 * 30)  # Keep for 30 days
    
    async def rotate_strategy(self, current_strategy: str, reason: str = "Automatic rotation") -> Dict:
        """
        Rotate the Psychologist's interrogation strategy
        """
        # Get current index
        current_index = self.styles.index(current_strategy) if current_strategy in self.styles else 0
        new_index = (current_index + 1) % len(self.styles)
        new_strategy = self.styles[new_index]
        
        # Update rotation record
        rotation_key = "psychologist_strategy_rotation"
        self.redis.set(rotation_key, json.dumps({
            "previous_strategy": current_strategy,
            "new_strategy": new_strategy,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Notify Psychologist (via Redis pub/sub)
        self.redis.publish("psychologist_rotate_strategy", json.dumps({
            "new_strategy": new_strategy,
            "reason": reason
        }))
        
        logger.info(f"Strategy rotated: {current_strategy} -> {new_strategy} ({reason})")
        
        return {
            "previous_strategy": current_strategy,
            "new_strategy": new_strategy,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================
# INITIALIZE
# ============================================

meta_psychologist = MetaPsychologist()

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    today = datetime.utcnow().date().isoformat()
    key = f"meta_psychologist_calls:{today}"
    calls_today = int(redis_client.get(key) or 0)
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "calls_today": calls_today,
        "quota_limit": MAX_CALLS_PER_DAY,
        "current_strategy": meta_psychologist.styles[meta_psychologist.current_style_index],
        "available_strategies": meta_psychologist.styles
    }

@app.post("/audit", response_model=AuditResponse)
async def audit_interrogation(request: AuditRequest):
    """Audit a psychologist interrogation"""
    result = await meta_psychologist.audit_interrogation(request)
    return result

@app.post("/rotate_strategy")
async def rotate_strategy(request: StrategyRotationRequest):
    """Manually rotate the psychologist's strategy"""
    result = await meta_psychologist.rotate_strategy(
        request.current_strategy,
        request.reason
    )
    return result

@app.get("/strategy")
async def get_current_strategy():
    """Get the current psychologist strategy"""
    rotation_data = redis_client.get("psychologist_strategy_rotation")
    
    if rotation_data:
        rotation = json.loads(rotation_data)
        return {
            "current_strategy": meta_psychologist.styles[meta_psychologist.current_style_index],
            "last_rotation": rotation
        }
    
    return {
        "current_strategy": meta_psychologist.styles[meta_psychologist.current_style_index],
        "last_rotation": None
    }

@app.get("/audits")
async def list_audits(limit: int = 20):
    """List recent audits"""
    keys = redis_client.keys("meta_psychologist_audit:*")
    keys = sorted(keys, reverse=True)[:limit]
    
    audits = []
    for key in keys:
        data = redis_client.get(key)
        if data:
            audit = json.loads(data)
            audit["interrogation_id"] = key.split(":")[1]
            audits.append(audit)
    
    return {
        "audits": audits,
        "count": len(audits)
    }

@app.get("/audit/{interrogation_id}")
async def get_audit(interrogation_id: str):
    """Get specific audit"""
    key = f"meta_psychologist_audit:{interrogation_id}"
    data = redis_client.get(key)
    
    if not data:
        raise HTTPException(status_code=404, detail="Audit not found")
    
    return json.loads(data)

@app.post("/reset_quota")
async def reset_quota():
    """Reset the daily quota (emergency use)"""
    today = datetime.utcnow().date().isoformat()
    key = f"meta_psychologist_calls:{today}"
    redis_client.set(key, 0)
    redis_client.expire(key, 86400)
    
    return {
        "status": "reset",
        "timestamp": datetime.utcnow().isoformat()
    }