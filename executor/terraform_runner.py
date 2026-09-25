"""
Terraform Runner - Executes Terraform configurations
"""

import os
import subprocess
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TerraformRunner:
    """
    Runs Terraform commands for infrastructure provisioning
    """
    
    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir
        
        # Check if terraform is available
        self.terraform_path = shutil.which("terraform")
        if not self.terraform_path:
            logger.warning("Terraform not found in PATH")
            self.terraform_path = "/usr/local/bin/terraform"
        
        logger.info(f"TerraformRunner initialized (path: {self.terraform_path})")
    
    def init(self, work_dir: str) -> Tuple[bool, str]:
        """Run terraform init"""
        try:
            result = subprocess.run(
                [self.terraform_path, "init"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info(f"Terraform init successful in {work_dir}")
                return True, result.stdout
            else:
                logger.error(f"Terraform init failed: {result.stderr}")
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Terraform init timed out"
        except Exception as e:
            return False, str(e)
    
    def plan(self, work_dir: str, var_file: Optional[str] = None) -> Tuple[bool, str]:
        """Run terraform plan"""
        try:
            cmd = [self.terraform_path, "plan"]
            if var_file:
                cmd.extend(["-var-file", var_file])
            cmd.append("-out=plan.tfplan")
            
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Terraform plan timed out"
        except Exception as e:
            return False, str(e)
    
    def apply(self, work_dir: str, auto_approve: bool = True) -> Tuple[bool, str]:
        """Run terraform apply"""
        try:
            cmd = [self.terraform_path, "apply"]
            if auto_approve:
                cmd.append("-auto-approve")
            
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Terraform apply timed out"
        except Exception as e:
            return False, str(e)
    
    def destroy(self, work_dir: str, auto_approve: bool = True) -> Tuple[bool, str]:
        """Run terraform destroy"""
        try:
            cmd = [self.terraform_path, "destroy"]
            if auto_approve:
                cmd.append("-auto-approve")
            
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except subprocess.TimeoutExpired:
            return False, "Terraform destroy timed out"
        except Exception as e:
            return False, str(e)
    
    def output(self, work_dir: str) -> Dict:
        """Get terraform outputs"""
        try:
            result = subprocess.run(
                [self.terraform_path, "output", "-json"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            else:
                return {}
                
        except Exception:
            return {}
    
    def validate(self, work_dir: str) -> Tuple[bool, str]:
        """Run terraform validate"""
        try:
            result = subprocess.run(
                [self.terraform_path, "validate"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
                
        except Exception as e:
            return False, str(e)
    
    def generate_config(
        self,
        resources: List[Dict],
        variables: Dict,
        outputs: Dict
    ) -> str:
        """
        Generate Terraform configuration from resources
        """
        config_parts = []
        
        # Terraform block
        config_parts.append('''
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
''')
        
        # Provider
        config_parts.append('''
provider "aws" {
  region = var.aws_region
}
''')
        
        # Variables
        if variables:
            config_parts.append("")
            for name, details in variables.items():
                default = details.get("default", "")
                description = details.get("description", "")
                config_parts.append(f'''variable "{name}" {{
  description = "{description}"
  default     = "{default}"
}}
''')
        
        # Resources
        if resources:
            config_parts.append("")
            for resource in resources:
                resource_type = resource.get("type", "null_resource")
                resource_name = resource.get("name", "example")
                config = resource.get("config", {})
                
                # Build resource block
                resource_str = f'resource "{resource_type}" "{resource_name}" {{\n'
                for key, value in config.items():
                    if isinstance(value, str):
                        resource_str += f'  {key} = "{value}"\n'
                    else:
                        resource_str += f'  {key} = {json.dumps(value)}\n'
                resource_str += "}\n"
                config_parts.append(resource_str)
        
        # Outputs
        if outputs:
            config_parts.append("")
            for name, details in outputs.items():
                value = details.get("value", "")
                description = details.get("description", "")
                config_parts.append(f'''output "{name}" {{
  description = "{description}"
  value       = {value}
}}
''')
        
        return "\n".join(config_parts)