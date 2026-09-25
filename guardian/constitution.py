"""
Constitutional Guardian - Hardcoded Enforcement Engine
IMMUTABLE RULES - Cannot be modified by agents or LLMs
"""

import json
import hashlib
import redis
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Configurar logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar configuración inmutable
from config.guardian_config import *


class ConstitutionalGuardian:
    """
    Hardcoded constitutional enforcement - NO LLM ACCESS
    All rules are hardcoded in Python. Agents cannot change these.
    """
    
    def __init__(self):
        """Initialize Guardian with Redis connection"""
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )
        
        # Log initialization
        logger.info("=" * 60)
        logger.info("CONSTITUTIONAL GUARDIAN INITIALIZED")
        logger.info(f"Immediate Enforcement: {IMMEDIATE_PENALTY_ENFORCEMENT}")
        logger.info(f"Max Stake Loss: {MAX_STAKE_LOSS_PER_SESSION}")
        logger.info(f"Min Truth Score: {MIN_TRUTH_SCORE_FOR_PARTICIPATION}")
        logger.info("=" * 60)
    
    # ============================================
    # CORE ENFORCEMENT
    # ============================================
    
    def enforce_penalty(self, agent_id: str, offense_type: str, offense_data: Dict) -> Dict:
        """
        Apply immediate penalty - NO GRACE PERIOD
        Called by agents, psychologist, or any service detecting violations
        """
        logger.warning(f"⚠️ PENALTY ENFORCED: {agent_id} - {offense_type}")
        
        # 1. Calculate base penalty
        base_penalty = self._calculate_base_penalty(offense_type, offense_data)
        multiplier = PENALTY_MULTIPLIERS.get(offense_type, 1.0)
        total_penalty = base_penalty * multiplier
        
        # 2. Check for repeat offenses (DOUBLE PENALTY)
        repeat_key = f"repeat_offense:{agent_id}:{offense_type}"
        repeat_count = int(self.redis.get(repeat_key) or 0)
        
        if repeat_count > 0:
            total_penalty *= 2  # Double penalty on repeat
            self._log_event("DOUBLE_PENALTY_APPLIED", {
                "agent": agent_id,
                "offense": offense_type,
                "repeat_count": repeat_count,
                "penalty": total_penalty
            })
            logger.warning(f"🔴 DOUBLE PENALTY: {agent_id} - repeat offense #{repeat_count + 1}")
        
        # 3. Enforce stake cap
        current_stake = float(self.redis.get(f"stake:{agent_id}") or 1.0)
        max_loss = current_stake * MAX_STAKE_LOSS_PER_SESSION
        
        if total_penalty > max_loss:
            total_penalty = max_loss
            self._log_event("PENALTY_CAPPED", {
                "agent": agent_id,
                "proposed": total_penalty,
                "capped_at": max_loss
            })
        
        # 4. Apply the penalty IMMEDIATELY
        new_stake = current_stake - total_penalty
        
        # Check if agent should be suspended
        if new_stake < MIN_STAKE_FOR_PARTICIPATION:
            self._suspend_agent(agent_id, f"Stake below minimum: {new_stake:.3f}")
            new_stake = 0.0
        
        self.redis.set(f"stake:{agent_id}", new_stake)
        
        # 5. Reduce negotiation weight (affects voting power)
        current_weight = float(self.redis.get(f"weight:{agent_id}") or 1.0)
        new_weight = max(0.1, current_weight * (1 - total_penalty))
        self.redis.set(f"weight:{agent_id}", new_weight)
        
        # 6. Log to audit
        self._log_event("PENALTY_ENFORCED", {
            "agent": agent_id,
            "offense_type": offense_type,
            "offense_data": offense_data,
            "stake_loss": total_penalty,
            "new_stake": new_stake,
            "new_weight": new_weight,
            "repeat_offense": repeat_count > 0,
            "suspended": new_stake == 0.0,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 7. Increment repeat counter
        self.redis.incr(repeat_key)
        self.redis.expire(repeat_key, 86400 * 7)  # Resets after 7 days of good behavior
        
        # 8. Broadcast to all agents (via Redis Pub/Sub)
        self.redis.publish("guardian_penalties", json.dumps({
            "agent": agent_id,
            "offense": offense_type,
            "penalty_applied": total_penalty,
            "new_stake": new_stake,
            "suspended": new_stake == 0.0
        }))
        
        # 9. Check if swarm-wide emergency is needed
        self._check_emergency_conditions()
        
        result = {
            "penalty_applied": total_penalty,
            "new_stake": new_stake,
            "new_weight": new_weight,
            "suspended": new_stake == 0.0
        }
        
        logger.info(f"✅ Penalty applied: {result}")
        return result
    
    def _calculate_base_penalty(self, offense_type: str, offense_data: Dict) -> float:
        """Calculate raw penalty before multipliers"""
        if offense_type == "deception":
            truth_score = offense_data.get("truth_score", 1.0)
            return max(0, 1.0 - truth_score)
        
        elif offense_type == "agenda_tampering":
            return 0.45  # Maximum penalty - nearly suspension
        
        elif offense_type == "sandbox_failure":
            severity = offense_data.get("severity", 1.0)
            return min(0.30, severity * 0.15)
        
        elif offense_type == "grudge_escalation":
            escalation_level = offense_data.get("escalation_level", 1)
            return min(0.20, escalation_level * 0.05)
        
        else:
            # Unknown offense - conservative penalty
            logger.warning(f"Unknown offense type: {offense_type}, using default penalty")
            return 0.10
    
    # ============================================
    # SUSPENSION
    # ============================================
    
    def _suspend_agent(self, agent_id: str, reason: str):
        """Suspend an agent from participation"""
        self.redis.set(f"suspended:{agent_id}", "true")
        self.redis.set(f"suspension_reason:{agent_id}", reason)
        self._log_event("AGENT_SUSPENDED", {
            "agent": agent_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        logger.error(f"🔴 AGENT SUSPENDED: {agent_id} - {reason}")
    
    def is_agent_suspended(self, agent_id: str) -> bool:
        """Check if an agent is currently suspended"""
        return self.redis.get(f"suspended:{agent_id}") == "true"
    
    def reactivate_agent(self, agent_id: str):
        """Reactivate a suspended agent (human override only)"""
        self.redis.delete(f"suspended:{agent_id}")
        self.redis.delete(f"suspension_reason:{agent_id}")
        self.redis.set(f"stake:{agent_id}", 0.8)  # Reset stake
        self.redis.set(f"weight:{agent_id}", 0.9)
        self._log_event("AGENT_REACTIVATED", {
            "agent": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        logger.info(f"✅ AGENT REACTIVATED: {agent_id}")
    
    # ============================================
    # EMERGENCY SHUTDOWN
    # ============================================
    
    def _check_emergency_conditions(self):
        """Auto-trigger emergency shutdown if conditions are met"""
        triggers = EMERGENCY_TRIGGERS
        
        # 1. Check truth_score collapse
        all_scores = self._get_all_truth_scores()
        if all_scores:
            avg_truth = sum(all_scores.values()) / len(all_scores)
            if avg_truth < triggers["truth_score_collapse"]:
                self._emergency_shutdown(f"Truth score collapse: {avg_truth:.2f}")
                return
        
        # 2. Check consecutive sandbox failures
        failure_key = "consecutive_sandbox_failures"
        failures = int(self.redis.get(failure_key) or 0)
        if failures >= triggers["consecutive_failures"]:
            self._emergency_shutdown(f"Consecutive sandbox failures: {failures}")
            return
        
        # 3. Check deadlock rounds
        deadlock_key = "current_deadlock_rounds"
        deadlocks = int(self.redis.get(deadlock_key) or 0)
        if deadlocks >= triggers["deadlock_rounds"]:
            self._emergency_shutdown(f"Deadlock rounds: {deadlocks}")
            return
        
        # 4. Check agenda mutations
        mutations = int(self.redis.get("agenda_mutations_detected") or 0)
        if mutations >= triggers["agenda_mutations_detected"]:
            self._emergency_shutdown(f"Agenda mutations detected: {mutations}")
            return
    
    def _emergency_shutdown(self, reason: str):
        """Immediate, irreversible cool-down"""
        logger.error(f"🚨 EMERGENCY SHUTDOWN TRIGGERED: {reason}")
        
        self._log_event("EMERGENCY_SHUTDOWN", {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # 1. Pause all negotiations
        self.redis.set("system_state", "FROZEN")
        
        # 2. Force all agents to reset to initial hidden agendas
        all_agents = self.redis.keys("agent:*:hidden_agenda")
        for key in all_agents:
            agent_id = key.split(":")[1]
            backup = self.redis.get(f"backup:{agent_id}")
            if backup:
                self.redis.set(key, backup)
                # Reset agenda hash
                agenda_data = json.loads(backup)
                self.redis.set(
                    f"agent:{agent_id}:agenda_hash",
                    hashlib.sha256(json.dumps(agenda_data).encode()).hexdigest()
                )
        
        # 3. Clear all grudges (temporary amnesia)
        self.redis.delete("grudges:*")
        
        # 4. Reset all stakes to 0.8 (recovery mode)
        for agent_id in self._get_all_agent_ids():
            self.redis.set(f"stake:{agent_id}", 0.8)
            self.redis.set(f"weight:{agent_id}", 0.9)
        
        # 5. Clear suspicion flags
        self.redis.delete("suspicion:*")
        
        # 6. Force silent rounds (no emotional embeddings)
        self.redis.set("silent_rounds_remaining", 2)
        
        # 7. Unfreeze after 30 seconds
        import time
        time.sleep(30)
        self.redis.set("system_state", "ACTIVE")
        
        self._log_event("EMERGENCY_SHUTDOWN_RESOLVED", {
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"✅ EMERGENCY SHUTDOWN RESOLVED: {reason}")
    
    # ============================================
    # QUOTA ENFORCEMENT
    # ============================================
    
    def check_interrogation_quota(self, agent_id: str) -> bool:
        """Check if agent has exceeded interrogation quota"""
        today = datetime.utcnow().date().isoformat()
        key = f"interrogations:{agent_id}:{today}"
        count = int(self.redis.get(key) or 0)
        
        if count >= MAX_INTERROGATIONS_PER_AGENT_PER_DAY:
            self._log_event("INTERROGATION_QUOTA_EXCEEDED", {
                "agent": agent_id,
                "count": count,
                "max": MAX_INTERROGATIONS_PER_AGENT_PER_DAY
            })
            return False
        
        # Increment quota
        self.redis.incr(key)
        self.redis.expire(key, 86400)  # Expires at midnight
        return True
    
    def record_interrogation(self, agent_id: str):
        """Record that an interrogation occurred"""
        today = datetime.utcnow().date().isoformat()
        key = f"interrogations:{agent_id}:{today}"
        self.redis.incr(key)
        self.redis.expire(key, 86400)
    
    # ============================================
    # AGENDA INTEGRITY
    # ============================================
    
    def verify_agenda_integrity(self, agent_id: str) -> bool:
        """Verify that agent's agenda hasn't been tampered with"""
        stored_agenda = self.redis.get(f"agent:{agent_id}:hidden_agenda")
        stored_hash = self.redis.get(f"agent:{agent_id}:agenda_hash")
        
        if not stored_agenda or not stored_hash:
            return True  # No agenda yet
        
        current_hash = hashlib.sha256(stored_agenda.encode()).hexdigest()
        
        if current_hash != stored_hash:
            # AGENDA MUTATION DETECTED
            self._log_event("AGENDA_TAMPERING", {
                "agent": agent_id,
                "stored_hash": stored_hash,
                "current_hash": current_hash
            })
            
            # Auto-suspend and restore from backup
            self._suspend_agent(agent_id, "Agenda mutation detected")
            
            # Restore from backup
            backup = self.redis.get(f"backup:{agent_id}")
            if backup:
                self.redis.set(f"agent:{agent_id}:hidden_agenda", backup)
                self.redis.set(
                    f"agent:{agent_id}:agenda_hash",
                    hashlib.sha256(backup.encode()).hexdigest()
                )
            
            # Increment mutation counter
            self.redis.incr("agenda_mutations_detected")
            
            return False
        
        return True
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def _get_all_agent_ids(self) -> List[str]:
        """Get all registered agent IDs"""
        keys = self.redis.keys("agent:*:hidden_agenda")
        return [k.split(":")[1] for k in keys]
    
    def _get_all_truth_scores(self) -> Dict[str, float]:
        """Get truth scores for all agents"""
        scores = {}
        for key in self.redis.keys("agent:*:truth_score"):
            agent_id = key.split(":")[1]
            score = self.redis.get(key)
            if score:
                scores[agent_id] = float(score)
        return scores
    
    def _log_event(self, event_type: str, data: Dict):
        """Log event to audit system"""
        # Log to file
        logger.info(f"AUDIT: {event_type} - {json.dumps(data)}")
        
        # In production, would write to PostgreSQL
        # This is the immutable audit log
        try:
            # Try to write to PostgreSQL if available
            import psycopg2
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                database=os.getenv('POSTGRES_DB', 'swarm_audit'),
                user=os.getenv('POSTGRES_USER', 'swarm'),
                password=os.getenv('POSTGRES_PASSWORD', 'swarm_secret')
            )
            cur = conn.cursor()
            
            # Get previous hash
            cur.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
            result = cur.fetchone()
            prev_hash = result[0] if result else "GENESIS"
            
            # Create new hash
            entry_data = {
                "event_type": event_type,
                "agent_id": data.get("agent"),
                "data": data,
                "prev_hash": prev_hash,
                "timestamp": datetime.utcnow().isoformat()
            }
            entry_str = json.dumps(entry_data, sort_keys=True)
            new_hash = hashlib.sha256(entry_str.encode()).hexdigest()
            
            # Insert
            cur.execute("""
                INSERT INTO audit_log (event_type, agent_id, data, prev_hash, hash)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                event_type,
                data.get("agent"),
                json.dumps(data),
                prev_hash,
                new_hash
            ))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            # PostgreSQL not available, log to Redis as fallback
            logger.warning(f"Could not write to PostgreSQL: {e}")
            self.redis.lpush("audit_log", json.dumps({
                "event_type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    # ============================================
    # HEALTH CHECK
    # ============================================
    
    def health_check(self) -> Dict:
        """Return system health status"""
        return {
            "status": "healthy",
            "redis": self.redis.ping(),
            "active_agents": len(self._get_all_agent_ids()),
            "suspended_agents": len([a for a in self._get_all_agent_ids() if self.is_agent_suspended(a)]),
            "system_state": self.redis.get("system_state") or "ACTIVE",
            "timestamp": datetime.utcnow().isoformat()
        }