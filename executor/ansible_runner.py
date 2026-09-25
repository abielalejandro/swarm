"""
Ansible Runner - Executes Ansible playbooks
"""

import os
import subprocess
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class AnsibleRunner:
    """
    Runs Ansible playbooks for configuration management
    """
    
    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir
        
        # Check if ansible-runner is available
        self.ansible_runner_path = shutil.which("ansible-runner")
        if not self.ansible_runner_path:
            logger.warning("ansible-runner not found in PATH")
            self.ansible_runner_path = "ansible-runner"
        
        logger.info(f"AnsibleRunner initialized")
    
    def run_playbook(
        self,
        playbook_path: str,
        inventory: Dict,
        vars: Dict,
        environment: str = "sandbox"
    ) -> Tuple[bool, Dict]:
        """
        Run an Ansible playbook
        """
        try:
            # Create runner directory
            runner_dir = Path(self.workspace_dir) / f"ansible_{environment}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            runner_dir.mkdir(parents=True, exist_ok=True)
            
            # Create project directory
            project_dir = runner_dir / "project"
            project_dir.mkdir(exist_ok=True)
            
            # Copy playbook
            playbook_name = Path(playbook_path).name
            shutil.copy2(playbook_path, project_dir / playbook_name)
            
            # Create inventory
            inventory_path = runner_dir / "inventory.json"
            with open(inventory_path, "w") as f:
                json.dump(inventory, f)
            
            # Create extra vars
            vars_path = runner_dir / "extra_vars.json"
            with open(vars_path, "w") as f:
                json.dump(vars, f)
            
            # Build ansible-runner command
            cmd = [
                self.ansible_runner_path,
                "run",
                str(runner_dir),
                "--inventory", str(inventory_path),
                "--playbook", playbook_name,
                "--extra-vars", str(vars_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            # Parse output
            status = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
            if result.returncode == 0:
                return True, status
            else:
                return False, status
                
        except subprocess.TimeoutExpired:
            return False, {"error": "Ansible playbook timed out"}
        except Exception as e:
            logger.error(f"Ansible error: {e}")
            return False, {"error": str(e)}
    
    def generate_playbook(
        self,
        tasks: List[Dict],
        name: str = "generated_playbook",
        hosts: str = "all",
        become: bool = True
    ) -> str:
        """
        Generate an Ansible playbook from tasks
        """
        playbook = {
            "name": name,
            "hosts": hosts,
            "become": become,
            "tasks": tasks
        }
        
        # Convert to YAML (simplified)
        playbook_yaml = f"---\n- name: {name}\n  hosts: {hosts}\n"
        
        if become:
            playbook_yaml += "  become: yes\n"
        
        playbook_yaml += "  tasks:\n"
        for task in tasks:
            task_name = task.get("name", "Task")
            module = task.get("module", "debug")
            args = task.get("args", {})
            
            playbook_yaml += f"    - name: {task_name}\n"
            playbook_yaml += f"      {module}:\n"
            for key, value in args.items():
                if isinstance(value, str):
                    playbook_yaml += f"        {key}: \"{value}\"\n"
                else:
                    playbook_yaml += f"        {key}: {json.dumps(value)}\n"
        
        return playbook_yaml
    
    def validate_playbook(self, playbook_path: str) -> Tuple[bool, str]:
        """
        Validate an Ansible playbook
        """
        try:
            # Try to parse as YAML
            import yaml
            with open(playbook_path, 'r') as f:
                yaml.safe_load(f)
            return True, "Playbook is valid"
            
        except Exception as e:
            return False, str(e)


# Import datetime for use in methods
from datetime import datetime