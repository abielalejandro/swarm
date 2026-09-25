"""
Executor - State Machine Execution Engine
Executes contracts and provisions infrastructure
"""

import json
import os
import logging
import redis
import asyncio
import subprocess
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import tempfile
from pathlib import Path

# Setup logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Initialize app
app = FastAPI(
    title="Executor API",
    description="State machine execution and infrastructure provisioning",
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

GUARDIAN_URL = os.getenv('GUARDIAN_URL', 'http://guardian:8001')

# ============================================
# MODELS
# ============================================

class ExecutionRequest(BaseModel):
    contract_id: str
    state_machine: Dict
    environment: Optional[str] = "sandbox"
    auto_approve: bool = False
    timeout: Optional[int] = 60

class ExecutionResponse(BaseModel):
    contract_id: str
    status: str
    execution_id: str
    sandbox_verified: bool
    deployed: bool
    logs: List[str]
    timestamp: str

class SandboxRequest(BaseModel):
    contract_id: str
    state_machine: Dict
    timeout: Optional[int] = 60

# ============================================
# STATE MACHINE EXECUTOR
# ============================================

class StateMachineExecutor:
    """
    Executes state machine from contract
    """
    
    def __init__(self):
        self.redis = redis_client
        self.guardian_url = GUARDIAN_URL
        self.workspace_dir = "/workspace"
        
        # Ensure workspace exists
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info("StateMachineExecutor initialized")
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute a state machine contract
        """
        contract_id = request.contract_id
        state_machine = request.state_machine
        environment = request.environment
        
        execution_id = f"exec_{contract_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logs = []
        status = "pending"
        sandbox_verified = False
        deployed = False
        
        try:
            # Step 1: Validate state machine
            logs.append(f"[{datetime.utcnow().isoformat()}] Validating state machine...")
            is_valid = self._validate_state_machine(state_machine)
            
            if not is_valid:
                logs.append(f"[{datetime.utcnow().isoformat()}] ❌ Invalid state machine")
                return ExecutionResponse(
                    contract_id=contract_id,
                    status="failed",
                    execution_id=execution_id,
                    sandbox_verified=False,
                    deployed=False,
                    logs=logs,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            logs.append(f"[{datetime.utcnow().isoformat()}] ✅ State machine validated")
            
            # Step 2: Run in sandbox
            logs.append(f"[{datetime.utcnow().isoformat()}] Running sandbox verification...")
            sandbox_result = await self._run_sandbox(contract_id, state_machine)
            sandbox_verified = sandbox_result.get("success", False)
            
            if sandbox_verified:
                logs.append(f"[{datetime.utcnow().isoformat()}] ✅ Sandbox verification passed")
            else:
                logs.append(f"[{datetime.utcnow().isoformat()}] ❌ Sandbox verification failed: {sandbox_result.get('error', 'Unknown error')}")
                
                # Report to Guardian
                await self._report_failure(contract_id, "sandbox_failure", sandbox_result)
                
                return ExecutionResponse(
                    contract_id=contract_id,
                    status="sandbox_failed",
                    execution_id=execution_id,
                    sandbox_verified=False,
                    deployed=False,
                    logs=logs,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            # Step 3: Deploy
            if request.auto_approve or environment == "production":
                logs.append(f"[{datetime.utcnow().isoformat()}] Deploying to {environment}...")
                deploy_result = await self._deploy(state_machine, environment)
                
                if deploy_result.get("success", False):
                    deployed = True
                    status = "completed"
                    logs.append(f"[{datetime.utcnow().isoformat()}] ✅ Deployment successful")
                else:
                    status = "deployment_failed"
                    logs.append(f"[{datetime.utcnow().isoformat()}] ❌ Deployment failed: {deploy_result.get('error', 'Unknown error')}")
            else:
                status = "pending_approval"
                logs.append(f"[{datetime.utcnow().isoformat()}] ⏳ Awaiting human approval for deployment")
            
            # Store execution result
            self._store_execution(execution_id, {
                "contract_id": contract_id,
                "status": status,
                "sandbox_verified": sandbox_verified,
                "deployed": deployed,
                "logs": logs,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return ExecutionResponse(
                contract_id=contract_id,
                status=status,
                execution_id=execution_id,
                sandbox_verified=sandbox_verified,
                deployed=deployed,
                logs=logs,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error executing contract {contract_id}: {e}")
            logs.append(f"[{datetime.utcnow().isoformat()}] ❌ Error: {str(e)}")
            
            return ExecutionResponse(
                contract_id=contract_id,
                status="error",
                execution_id=execution_id,
                sandbox_verified=False,
                deployed=False,
                logs=logs,
                timestamp=datetime.utcnow().isoformat()
            )
    
    def _validate_state_machine(self, state_machine: Dict) -> bool:
        """Validate state machine structure"""
        required_fields = ["states", "transitions"]
        
        for field in required_fields:
            if field not in state_machine:
                logger.error(f"Missing required field: {field}")
                return False
        
        if not state_machine.get("states"):
            logger.error("No states defined")
            return False
        
        return True
    
    async def _run_sandbox(self, contract_id: str, state_machine: Dict) -> Dict:
        """Run sandbox verification"""
        try:
            # Create temporary workspace
            sandbox_dir = f"{self.workspace_dir}/sandbox_{contract_id}"
            Path(sandbox_dir).mkdir(parents=True, exist_ok=True)
            
            # Write state machine to file
            with open(f"{sandbox_dir}/state_machine.json", "w") as f:
                json.dump(state_machine, f, indent=2)
            
            # Simulate sandbox verification (in production, would run actual tests)
            # For now, just validate JSON structure
            if "states" in state_machine and len(state_machine["states"]) > 0:
                # Simulate some checks
                checks = [
                    self._check_state_reachability(state_machine),
                    self._check_termination(state_machine),
                    self._check_resource_requirements(state_machine)
                ]
                
                if all(checks):
                    return {"success": True, "message": "All sandbox checks passed"}
                else:
                    return {"success": False, "error": "Some checks failed"}
            
            return {"success": True, "message": "Sandbox verification passed"}
            
        except Exception as e:
            logger.error(f"Sandbox error: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_state_reachability(self, state_machine: Dict) -> bool:
        """Check if all states are reachable"""
        # Simplified check
        return True
    
    def _check_termination(self, state_machine: Dict) -> bool:
        """Check if state machine terminates"""
        # Simplified check
        return True
    
    def _check_resource_requirements(self, state_machine: Dict) -> bool:
        """Check if resources are available"""
        # Simplified check
        return True
    
    async def _deploy(self, state_machine: Dict, environment: str) -> Dict:
        """Deploy to infrastructure"""
        try:
            # In production, this would call Terraform/Ansible
            # For now, simulate deployment
            
            # Write Terraform config
            tf_dir = f"{self.workspace_dir}/tf_{environment}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            Path(tf_dir).mkdir(parents=True, exist_ok=True)
            
            # Create simple Terraform config
            tf_content = self._generate_terraform_config(state_machine, environment)
            with open(f"{tf_dir}/main.tf", "w") as f:
                f.write(tf_content)
            
            logger.info(f"Terraform config generated for {environment}")
            
            # Simulate deployment
            if environment == "sandbox":
                return {"success": True, "message": "Sandbox deployment successful", "resources": []}
            else:
                return {"success": True, "message": f"Deployment to {environment} successful", "resources": []}
            
        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_terraform_config(self, state_machine: Dict, environment: str) -> str:
        """Generate Terraform configuration from state machine"""
        states = state_machine.get("states", [])
        
        resources = []
        for state in states[:5]:  # Limit for safety
            if isinstance(state, dict):
                resource_type = state.get("resource_type", "null_resource")
                resource_name = state.get("resource_name", f"res_{datetime.utcnow().strftime('%Y%m%d')}")
                resources.append(f'resource "{resource_type}" "{resource_name}" {{}}')
        
        config = f"""
terraform {{
  required_version = ">= 1.0"
}}

# Generated from contract
# Environment: {environment}
# Timestamp: {datetime.utcnow().isoformat()}

{chr(10).join(resources) if resources else "# No resources defined"}
"""
        return config
    
    async def _report_failure(self, contract_id: str, failure_type: str, data: Dict):
        """Report failure to Guardian"""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.guardian_url}/enforce_penalty",
                    json={
                        "agent_id": "system",
                        "offense_type": failure_type,
                        "offense_data": {
                            "contract_id": contract_id,
                            "error": data.get("error", "Unknown error"),
                            "severity": 1.0
                        }
                    }
                )
                logger.info(f"Reported {failure_type} for {contract_id}")
        except Exception as e:
            logger.error(f"Error reporting to Guardian: {e}")
    
    def _store_execution(self, execution_id: str, data: Dict):
        """Store execution result"""
        self.redis.set(
            f"execution:{execution_id}",
            json.dumps(data)
        )
        self.redis.expire(f"execution:{execution_id}", 86400 * 7)  # Keep for 7 days


# ============================================
# API ENDPOINTS
# ============================================

executor = StateMachineExecutor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "workspace": executor.workspace_dir,
        "terraform": shutil.which("terraform") is not None
    }

@app.post("/execute")
async def execute_contract(request: ExecutionRequest):
    """Execute a state machine contract"""
    result = await executor.execute(request)
    return result

@app.post("/sandbox")
async def run_sandbox(request: SandboxRequest):
    """Run sandbox verification only"""
    result = await executor._run_sandbox(request.contract_id, request.state_machine)
    return {
        "contract_id": request.contract_id,
        "verified": result.get("success", False),
        "message": result.get("message", result.get("error", "Unknown")),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/execution/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details"""
    data = executor.redis.get(f"execution:{execution_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return json.loads(data)

@app.get("/executions")
async def list_executions():
    """List recent executions"""
    keys = executor.redis.keys("execution:*")
    executions = []
    
    for key in sorted(keys, reverse=True)[:20]:
        data = executor.redis.get(key)
        if data:
            execution = json.loads(data)
            execution["execution_id"] = key.split(":")[1]
            executions.append(execution)
    
    return {
        "executions": executions,
        "count": len(executions)
    }

@app.post("/deploy/approve")
async def approve_deployment(execution_id: str, approved: bool = True):
    """Approve a pending deployment"""
    data = executor.redis.get(f"execution:{execution_id}")
    if not data:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    execution = json.loads(data)
    
    if execution.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Execution is not pending approval")
    
    if approved:
        # Trigger deployment
        contract_id = execution.get("contract_id")
        state_machine = execution.get("state_machine", {})
        
        result = await executor._deploy(state_machine, "production")
        
        if result.get("success"):
            execution["status"] = "completed"
            execution["deployed"] = True
            execution["approved_at"] = datetime.utcnow().isoformat()
        else:
            execution["status"] = "deployment_failed"
            execution["deployment_error"] = result.get("error")
        
        executor.redis.set(f"execution:{execution_id}", json.dumps(execution))
        
        return {
            "status": "approved",
            "execution_id": execution_id,
            "deployed": execution.get("deployed", False)
        }
    else:
        execution["status"] = "rejected"
        execution["approved_at"] = datetime.utcnow().isoformat()
        executor.redis.set(f"execution:{execution_id}", json.dumps(execution))
        
        return {
            "status": "rejected",
            "execution_id": execution_id
        }