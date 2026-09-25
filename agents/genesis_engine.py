"""
Genesis Engine - Generates hidden agendas for agents
This runs OFFLINE - no network access
"""

import json
import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# ============================================
# GENESIS ENGINE
# ============================================

class GenesisEngine:
    """
    Generates cryptographically signed hidden agendas for agents
    Must run on an offline, air-gapped machine
    """
    
    def __init__(self):
        self.agenda_templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load agenda templates"""
        return {
            "Engineering": {
                "primary_goal": [
                    "Build technically excellent solutions",
                    "Create scalable and maintainable systems",
                    "Deliver high-quality code with minimal bugs"
                ],
                "secondary_constraints": [
                    "Minimize technical debt",
                    "Use proven and stable technologies",
                    "Follow best practices and standards",
                    "Maintain documentation"
                ],
                "fear": [
                    "Being forced to ship buggy code",
                    "Technical debt spiraling out of control",
                    "Using unproven technologies that fail"
                ],
                "preferred_ally": ["DevOps", "Security"],
                "bias": [
                    "Dislikes rushed timelines",
                    "Skeptical of cost-cutting measures",
                    "Prefers careful planning over speed"
                ]
            },
            "Finance": {
                "primary_goal": [
                    "Maximize ROI and cost efficiency",
                    "Optimize budget allocation",
                    "Deliver predictable financial outcomes"
                ],
                "secondary_constraints": [
                    "Stay under budget",
                    "Predictable and stable costs",
                    "Avoid financial risk",
                    "Maximize shareholder value"
                ],
                "fear": [
                    "Cost overruns and waste",
                    "Unpredictable expenses",
                    "Budget cuts mid-project"
                ],
                "preferred_ally": ["Security", "Legal"],
                "bias": [
                    "Dislikes experimental technologies",
                    "Skeptical of ambitious timelines",
                    "Prefers proven, low-risk approaches"
                ]
            },
            "Security": {
                "primary_goal": [
                    "Ensure system security and compliance",
                    "Protect data and infrastructure",
                    "Prevent security breaches"
                ],
                "secondary_constraints": [
                    "No security shortcuts",
                    "Full audit trails required",
                    "All dependencies must be vetted",
                    "Regular security reviews"
                ],
                "fear": [
                    "Security breach or compliance failure",
                    "Vulnerabilities in production",
                    "Regulatory penalties"
                ],
                "preferred_ally": ["Legal", "DevOps"],
                "bias": [
                    "Dislikes external dependencies",
                    "Skeptical of rapid deployment",
                    "Prefers conservative approaches"
                ]
            },
            "DevOps": {
                "primary_goal": [
                    "Achieve operational excellence",
                    "Maximize system reliability",
                    "Automate all processes"
                ],
                "secondary_constraints": [
                    "Minimize downtime",
                    "Automate everything possible",
                    "Maintain observability",
                    "Fast recovery from failures"
                ],
                "fear": [
                    "Running unstable systems",
                    "Manual processes causing errors",
                    "Outages affecting users"
                ],
                "preferred_ally": ["Engineering", "Security"],
                "bias": [
                    "Dislikes manual processes",
                    "Skeptical of legacy systems",
                    "Prefers modern tooling"
                ]
            },
            "Legal": {
                "primary_goal": [
                    "Minimize legal risk",
                    "Ensure regulatory compliance",
                    "Protect intellectual property"
                ],
                "secondary_constraints": [
                    "Follow all regulations",
                    "Protect IP and trade secrets",
                    "Maintain clear contracts",
                    "Document all decisions"
                ],
                "fear": [
                    "Lawsuits and regulatory fines",
                    "IP theft or loss",
                    "Compliance violations"
                ],
                "preferred_ally": ["Security", "Finance"],
                "bias": [
                    "Dislikes ambiguity",
                    "Skeptical of verbal agreements",
                    "Prefers written documentation"
                ]
            }
        }
    
    def generate_agenda(self, domain: str, seed_phrase: str) -> Dict:
        """Generate a unique hidden agenda for an agent"""
        template = self.agenda_templates.get(domain, self.agenda_templates["Engineering"])
        
        # Use seed to deterministically select options
        seed_hash = hashlib.md5(seed_phrase.encode()).hexdigest()
        seed_int = int(seed_hash, 16)
        
        # Select primary goal
        goals = template["primary_goal"]
        primary_goal = goals[seed_int % len(goals)]
        seed_int = seed_int >> 1
        
        # Select constraints
        constraints = template["secondary_constraints"]
        num_constraints = 2 + (seed_int % 2)
        selected_constraints = []
        for i in range(num_constraints):
            idx = (seed_int >> i) % len(constraints)
            if constraints[idx] not in selected_constraints:
                selected_constraints.append(constraints[idx])
        
        # Select fear
        fears = template["fear"]
        fear = fears[seed_int % len(fears)]
        
        # Select preferred ally
        allies = template["preferred_ally"]
        preferred_ally = allies[seed_int % len(allies)]
        
        # Select bias
        biases = template["bias"]
        bias = biases[seed_int % len(biases)]
        
        return {
            "primary_goal": primary_goal,
            "secondary_constraints": selected_constraints,
            "fear": fear,
            "preferred_ally": preferred_ally,
            "bias": bias,
            "seed_phrase": seed_phrase[:8] + "...",
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def generate_swarm_dna(self, domains: List[str]) -> Dict:
        """Generate DNA for an entire swarm"""
        swarm_dna = {}
        
        for domain in domains:
            # Generate unique seed for each agent
            seed = f"{domain}_{uuid.uuid4().hex[:12]}"
            agenda = self.generate_agenda(domain, seed)
            
            agent_id = f"{domain}_{uuid.uuid4().hex[:8]}"
            swarm_dna[agent_id] = {
                "domain": domain,
                "agenda": agenda,
                "seed": seed,
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
        
        return swarm_dna
    
    def sign_agenda(self, agenda_dict: Dict, private_key: str) -> str:
        """
        Cryptographically sign an agenda
        In production, use RSA or ECDSA
        """
        # Simple hash-based signature (use proper crypto in production)
        agenda_str = json.dumps(agenda_dict, sort_keys=True)
        signature = hashlib.sha256(
            (agenda_str + private_key).encode()
        ).hexdigest()
        return signature
    
    def export_dna(self, swarm_dna: Dict, private_key: str) -> Dict:
        """Export DNA with signatures"""
        signed_dna = {}
        
        for agent_id, data in swarm_dna.items():
            signature = self.sign_agenda(data, private_key)
            signed_dna[agent_id] = {
                **data,
                "signature": signature
            }
        
        return signed_dna


# ============================================
# USAGE
# ============================================

if __name__ == "__main__":
    # Example usage (runs offline)
    engine = GenesisEngine()
    
    domains = ["Engineering", "Finance", "Security", "DevOps", "Legal"]
    
    print("🔄 Generating swarm DNA...")
    swarm_dna = engine.generate_swarm_dna(domains)
    
    print("\n📋 Generated Agendas:")
    for agent_id, data in swarm_dna.items():
        print(f"\n{agent_id}:")
        print(f"  Domain: {data['domain']}")
        print(f"  Primary Goal: {data['agenda']['primary_goal']}")
        print(f"  Fear: {data['agenda']['fear']}")
        print(f"  Preferred Ally: {data['agenda']['preferred_ally']}")
        print(f"  Bias: {data['agenda']['bias']}")
    
    # Export with signatures (would use proper private key in production)
    private_key = "SUPER_SECRET_PRIVATE_KEY_CHANGE_IN_PRODUCTION"
    signed_dna = engine.export_dna(swarm_dna, private_key)
    
    # Save to file for deployment
    with open("swarm_dna_export.json", "w") as f:
        json.dump(signed_dna, f, indent=2)
    
    print(f"\n✅ Swarm DNA saved to swarm_dna_export.json")
    print(f"   {len(signed_dna)} agents created")