"""
Constitutional Guardian Configuration
IMMUTABLE - Changes require human deployment
"""

# ============================================
# ABSOLUTE RULES (HARDCODED)
# ============================================

# Enforcement Philosophy
IMMEDIATE_PENALTY_ENFORCEMENT = True  # No grace periods
DOUBLE_PENALTY_THRESHOLD = 1          # Repeat offense = 2x penalty

# Stake Limits
MAX_STAKE_LOSS_PER_SESSION = 0.50     # Max 50% stake loss per day
MIN_STAKE_FOR_PARTICIPATION = 0.05    # Below 5% = auto-suspension

# Interrogation Quotas
MAX_INTERROGATIONS_PER_AGENT_PER_DAY = 3
MIN_TRUTH_SCORE_FOR_PARTICIPATION = 0.15

# Consensus Rules
MIN_AGENTS_FOR_CONSENSUS = 0.60       # 60% agreement needed
VETO_POWER_AGENTS = ["Security", "Finance"]  # Can block unilaterally

# Recursion Guards
MAX_META_PSYCHOLOGIST_CALLS_PER_DAY = 10
PSYCHOLOGIST_ROTATION_INTERVAL_HOURS = 12

# ============================================
# PENALTY MULTIPLIERS
# ============================================

PENALTY_MULTIPLIERS = {
    "deception": 1.0,           # Truth_score deficit * 100%
    "agenda_tampering": 3.0,    # 3x - nearly suspension
    "sandbox_failure": 1.5,     # 1.5x for technical failures
    "grudge_escalation": 0.5,   # Less severe, but immediate
}

# ============================================
# EMERGENCY TRIGGERS
# ============================================

EMERGENCY_TRIGGERS = {
    "truth_score_collapse": 0.2,      # All agents below 0.2 = shutdown
    "consecutive_failures": 3,         # 3 sandbox failures in a row
    "deadlock_rounds": 10,             # 10 rounds without consensus
    "agenda_mutations_detected": 1,    # ANY tampering = freeze
}

# ============================================
# NETWORK CONFIGURATION
# ============================================

SERVICE_PORTS = {
    "orchestrator": 8000,
    "guardian": 8001,
    "psychologist": 8002,
    "meta_psychologist": 8003,
    "executor": 8004,
    "dashboard": 8501,
}