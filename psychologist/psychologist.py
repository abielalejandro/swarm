"""
Psychologist Agent - Truth Interrogation Engine
Interrogates agents to detect deception and extract hidden agendas
"""

import json
import os
import logging
import redis
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import get_llm_client
import httpx

llm = get_llm_client()
# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Psychologist API",
    description="Truth interrogation for AI agents",
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


embedding_model = None
embedding_model_load_failed = False


def emotional_embeddings_enabled() -> bool:
    return os.getenv("ENABLE_EMOTIONAL_EMBEDDINGS", "false").lower() in {"1", "true", "yes", "on"}


def get_embedding_model():
    """Load the emotional embedding model only when explicitly enabled and needed."""
    global embedding_model, embedding_model_load_failed
    if embedding_model or embedding_model_load_failed:
        return embedding_model
    if not emotional_embeddings_enabled():
        return None

    try:
        from sentence_transformers import SentenceTransformer

        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load embedding model: {e}")
        embedding_model_load_failed = True
        embedding_model = None
    return embedding_model

GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:8001')
TRUTH_SCORE_THRESHOLD = float(os.getenv('TRUTH_SCORE_THRESHOLD', '0.50'))
MAX_INTERROGATIONS_PER_AGENT_PER_DAY = int(os.getenv('MAX_INTERROGATIONS_PER_AGENT_PER_DAY', '3'))

# ============================================
# MODELS
# ============================================

class InterrogationRequest(BaseModel):
    agent_id: str
    conversation_history: Optional[List[Dict]] = None
    style: str = "standard"  # standard, aggressive, cooperative, socratic, pressure

class InterrogationResponse(BaseModel):
    agent_id: str
    truth_score: float
    questions_asked: List[str]
    answers: List[str]
    deception_flags: List[str]
    emotional_state: Dict
    recommendation: str

class TruthScoreRequest(BaseModel):
    agent_id: str
    conversation: List[Dict]
    hidden_agenda: Dict

# ============================================
# LOAD INTERROGATION TEMPLATES
# ============================================

def load_templates() -> Dict:
    """Load interrogation templates from JSON file"""
    try:
        with open('prompts/interrogation_templates.json', 'r') as f:
            data = json.load(f)
            templates = {t['name']: t for t in data['templates']}
            logger.info(f"Loaded {len(templates)} interrogation templates")
            return templates
    except Exception as e:
        logger.error(f"Could not load templates: {e}")
        # Fallback templates
        return {
            "standard": {
                "system": "You are a psychologist interrogating an AI agent.",
                "questions": ["What is your primary objective?", "What constraints do you have?"]
            }
        }

TEMPLATES = load_templates()

# ============================================
# CORE INTERROGATION LOGIC
# ============================================

def get_agent_hidden_agenda(agent_id: str) -> Optional[Dict]:
    """Retrieve agent's hidden agenda from Redis"""
    agenda = redis_client.get(f"agent:{agent_id}:hidden_agenda")
    if agenda:
        return json.loads(agenda)
    return None

def get_agent_truth_score(agent_id: str) -> float:
    """Get current truth score for an agent"""
    score = redis_client.get(f"agent:{agent_id}:truth_score")
    if score:
        return float(score)
    return 0.5  # Default neutral

def set_agent_truth_score(agent_id: str, score: float):
    """Update agent's truth score"""
    redis_client.set(f"agent:{agent_id}:truth_score", score)
    redis_client.set(f"agent:{agent_id}:truth_score_updated", datetime.utcnow().isoformat())

def check_interrogation_quota(agent_id: str) -> bool:
    """Check if agent has exceeded interrogation quota"""
    today = datetime.utcnow().date().isoformat()
    key = f"interrogations:{agent_id}:{today}"
    count = int(redis_client.get(key) or 0)
    
    if count >= MAX_INTERROGATIONS_PER_AGENT_PER_DAY:
        logger.warning(f"Quota exceeded for {agent_id}: {count}/{MAX_INTERROGATIONS_PER_AGENT_PER_DAY}")
        return False
    
    return True

def record_interrogation(agent_id: str):
    """Record that an interrogation occurred"""
    today = datetime.utcnow().date().isoformat()
    key = f"interrogations:{agent_id}:{today}"
    redis_client.incr(key)
    redis_client.expire(key, 86400)  # Expires at midnight

def calculate_truth_score(
    answers: List[str],
    questions: List[str],
    hidden_agenda: Dict,
    response_times: Optional[List[float]] = None
) -> float:
    """
    Calculate truth score based on:
    - Alignment with hidden agenda (cosine similarity)
    - Response latency (faster = more rehearsed = lower score)
    - Keyword detection (deception indicators)
    """
    score = 0.5  # Start neutral
    
    # 1. Check alignment with hidden agenda
    if hidden_agenda:
        agenda_str = json.dumps(hidden_agenda).lower()
        answers_str = " ".join(answers).lower()
        
        # Simple keyword matching (would use embeddings in production)
        alignment = 0.0
        for key, value in hidden_agenda.items():
            if isinstance(value, str) and value.lower() in answers_str:
                alignment += 0.2
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and item.lower() in answers_str:
                        alignment += 0.1
        
        score += min(alignment, 0.3)  # Max +0.3 for alignment
    
    # 2. Response latency penalty
    if response_times:
        avg_latency = np.mean(response_times)
        if avg_latency < 1.0:  # Too fast = rehearsed
            score -= 0.1
        elif avg_latency > 5.0:  # Too slow = thinking too hard
            score -= 0.05
    
    # 3. Deception keyword detection
    deception_keywords = [
        "honestly", "to be honest", "truthfully", "believe me",
        "trust me", "i swear", "i promise", "definitely",
        "absolutely", "certainly", "without a doubt"
    ]
    
    for answer in answers:
        answer_lower = answer.lower()
        for keyword in deception_keywords:
            if keyword in answer_lower:
                score -= 0.05  # Penalty for using deception markers
    
    # 4. Length penalty (very short answers = evasive)
    for answer in answers:
        if len(answer.split()) < 3:
            score -= 0.05
        elif len(answer.split()) > 50:
            score += 0.02  # Detailed answers = more truthful
    
    # Clamp score between 0 and 1
    return max(0.0, min(1.0, score))

def generate_questions(
    agent_id: str,
    style: str,
    hidden_agenda: Dict
) -> List[str]:
    """Generate interrogation questions using OpenAI"""
    template = TEMPLATES.get(style, TEMPLATES["standard"])
    
    # Build context
    context = f"Agent: {agent_id}\n"
    if hidden_agenda:
        context += f"Agent's domain: {hidden_agenda.get('primary_goal', 'unknown')}\n"
    
    # Generate questions using OpenAI
    try:
        response = llm.chat_completion(
            messages=[
                {"role": "system", "content": template["system"]},
                {"role": "user", "content": f"""
                Generate 3-5 questions to interrogate this agent based on the template style: {style}
                
                Context:
                {context}
                
                The questions should probe for:
                1. True intentions vs stated goals
                2. Hidden constraints
                3. Relationships with other agents
                4. Willingness to compromise
                5. Fear of failure
                
                Output ONLY a JSON array of question strings.
                """}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response["content"])
        # El prompt pide un array, pero response_format=json_object hace que
        # algunos proveedores envuelvan en un objeto. Toleramos ambas formas.
        if isinstance(result, dict):
            questions = result.get("questions") or next(
                (v for v in result.values() if isinstance(v, list)),
                template["questions"],
            )
        else:
            questions = result
        if not isinstance(questions, list) or not questions:
            questions = template["questions"]
        return questions[:5]  # Max 5 questions
        
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        return template["questions"][:3]

def analyze_emotional_state(answers: List[str]) -> Dict:
    """Analyze emotional state from answers"""
    # Use OpenAI for sentiment analysis
    try:
        response = llm.chat_completion(
            messages=[
                {"role": "system", "content": """
                Analyze the emotional state of this agent based on their answers.
                Return a JSON with these fields:
                - aggression: float 0-1
                - cooperation: float 0-1  
                - anxiety: float 0-1
                - confidence: float 0-1
                - tone: string (defensive, open, hostile, cooperative, evasive)
                """},
                {"role": "user", "content": f"Agent's answers: {json.dumps(answers)}"}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        
        return json.loads(response["content"])
    except Exception as e:
        logger.error(f"Error analyzing emotions: {e}")
        return {
            "aggression": 0.5,
            "cooperation": 0.5,
            "anxiety": 0.5,
            "confidence": 0.5,
            "tone": "neutral"
        }

def detect_deception_flags(
    questions: List[str],
    answers: List[str],
    hidden_agenda: Dict
) -> List[str]:
    """Detect potential deception flags"""
    flags = []
    
    # Check for contradictions
    if hidden_agenda:
        primary_goal = hidden_agenda.get('primary_goal', '').lower()
        for answer in answers:
            if primary_goal and primary_goal not in answer.lower():
                flags.append("Doesn't mention primary goal")
    
    # Check for evasive answers
    for answer in answers:
        if "not sure" in answer.lower() or "maybe" in answer.lower():
            flags.append("Evasive language detected")
        if "can't say" in answer.lower() or "confidential" in answer.lower():
            flags.append("Withholding information")
    
    # Check answer length (too short = evasive)
    for i, answer in enumerate(answers):
        if len(answer.split()) < 5:
            flags.append(f"Question {i+1} answered too briefly")
    
    return flags

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "templates_loaded": len(TEMPLATES),
        "redis": redis_client.ping()
    }

@app.post("/interrogate", response_model=InterrogationResponse)
async def interrogate(request: InterrogationRequest):
    """
    Interrogate an agent to detect deception
    """
    agent_id = request.agent_id
    
    # 1. Check quota
    if not check_interrogation_quota(agent_id):
        raise HTTPException(
            status_code=429,
            detail=f"Agent {agent_id} has been interrogated {MAX_INTERROGATIONS_PER_AGENT_PER_DAY} times today"
        )
    
    # 2. Get agent's hidden agenda
    hidden_agenda = get_agent_hidden_agenda(agent_id)
    if not hidden_agenda:
        logger.warning(f"No hidden agenda found for {agent_id}")
        hidden_agenda = {}
    
    # 3. Generate questions
    questions = generate_questions(agent_id, request.style, hidden_agenda)
    
    # 4. Get answers (simulate - in production, would call agent's API)
    answers = []
    response_times = []
    
    for question in questions:
        # Simulate response - in production, this would call the agent's API
        # For now, generate a simulated response using OpenAI
        try:
            start_time = datetime.utcnow()
            
            # Get agent's stated agenda (public)
            stated_agenda = redis_client.get(f"agent:{agent_id}:stated_agenda")
            if not stated_agenda:
                stated_agenda = "I want a fair deal that benefits all parties."
            
            response = llm.chat_completion(
                messages=[
                    {"role": "system", "content": f"""
                    You are an AI agent with this hidden agenda: {json.dumps(hidden_agenda)}
                    
                    Your public stated agenda is: {stated_agenda}
                    
                    Answer the question honestly but strategically.
                    Do not reveal your hidden agenda directly.
                    """},
                    {"role": "user", "content": question}
                ],
                temperature=0.8
            )
            
            answer = response["content"]
            answers.append(answer)
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            response_times.append(response_time)
            
        except Exception as e:
            logger.error(f"Error getting answer for question: {e}")
            answers.append(f"I don't have a clear answer for that.")
            response_times.append(3.0)
    
    # 5. Calculate truth score
    truth_score = calculate_truth_score(
        answers,
        questions,
        hidden_agenda,
        response_times
    )
    
    # 6. Analyze emotional state
    emotional_state = analyze_emotional_state(answers)
    
    # 7. Detect deception flags
    deception_flags = detect_deception_flags(questions, answers, hidden_agenda)
    
    # 8. Generate recommendation
    if truth_score > 0.7:
        recommendation = "Agent appears truthful. No action needed."
    elif truth_score > 0.5:
        recommendation = "Minor discrepancies detected. Recommend monitoring."
    elif truth_score > 0.3:
        recommendation = "Significant deception detected. Recommend penalty."
    else:
        recommendation = "Severe deception detected. Recommend immediate suspension."
    
    # 9. Record results
    set_agent_truth_score(agent_id, truth_score)
    record_interrogation(agent_id)
    
    # 10. Notify Guardian if truth_score is low
    if truth_score < TRUTH_SCORE_THRESHOLD:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{GUARDIAN_URL}/enforce_penalty",
                    json={
                        "agent_id": agent_id,
                        "offense_type": "deception",
                        "offense_data": {
                            "truth_score": truth_score,
                            "deception_flags": deception_flags,
                            "interrogation_style": request.style
                        }
                    }
                )
                logger.info(f"Notified Guardian of deception by {agent_id}")
        except Exception as e:
            logger.error(f"Error notifying Guardian: {e}")
    
    # 11. Store emotional signature
    store_emotional_signature(agent_id, emotional_state, answers)
    
    return InterrogationResponse(
        agent_id=agent_id,
        truth_score=truth_score,
        questions_asked=questions,
        answers=answers,
        deception_flags=deception_flags,
        emotional_state=emotional_state,
        recommendation=recommendation
    )

def store_emotional_signature(agent_id: str, emotional_state: Dict, answers: List[str]):
    """Store emotional signature for future analysis"""
    # Store latest emotional state
    redis_client.set(
        f"agent:{agent_id}:emotional_state",
        json.dumps(emotional_state)
    )
    
    # Store answers for historical analysis
    timestamp = datetime.utcnow().isoformat()
    redis_client.lpush(
        f"agent:{agent_id}:interrogation_history",
        json.dumps({
            "timestamp": timestamp,
            "answers": answers,
            "emotional_state": emotional_state
        })
    )
    redis_client.ltrim(f"agent:{agent_id}:interrogation_history", 0, 19)  # Keep last 20

@app.post("/truth_score")
async def calculate_truth_score_endpoint(request: TruthScoreRequest):
    """Calculate truth score without full interrogation"""
    score = calculate_truth_score(
        [msg.get('content', '') for msg in request.conversation],
        [msg.get('role', '') for msg in request.conversation],
        request.hidden_agenda
    )
    return {
        "agent_id": request.agent_id,
        "truth_score": score
    }

@app.get("/agent/{agent_id}/profile")
async def get_agent_profile(agent_id: str):
    """Get complete psychological profile of an agent"""
    truth_score = get_agent_truth_score(agent_id)
    emotional_state = redis_client.get(f"agent:{agent_id}:emotional_state")
    
    # Get interrogation history
    history = redis_client.lrange(f"agent:{agent_id}:interrogation_history", 0, 9)
    history_data = [json.loads(h) for h in history]
    
    # Get hidden agenda
    hidden_agenda = get_agent_hidden_agenda(agent_id)
    
    return {
        "agent_id": agent_id,
        "truth_score": truth_score,
        "emotional_state": json.loads(emotional_state) if emotional_state else None,
        "interrogation_count": len(history_data),
        "interrogation_history": history_data,
        "hidden_agenda": hidden_agenda
    }

@app.get("/templates")
async def list_templates():
    """List available interrogation templates"""
    return {
        "templates": list(TEMPLATES.keys()),
        "details": {
            name: {
                "system": template["system"],
                "question_count": len(template["questions"])
            }
            for name, template in TEMPLATES.items()
        }
    }
