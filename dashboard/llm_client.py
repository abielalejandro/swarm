"""
LLM Client - Soporte multi-proveedor
Soporta: OpenAI, DeepSeek, Anthropic, Groq, Azure, Local (Ollama/LM Studio)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURACIÓN
# ============================================

class LLMProvider(Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    AZURE = "azure"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    CUSTOM = "custom"

# ============================================
# CLIENTE PRINCIPAL
# ============================================

class LLMClient:
    """
    Cliente unificado para múltiples proveedores LLM
    """
    
    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv('LLM_PROVIDER', 'openai').lower()
        self.api_key = os.getenv('LLM_API_KEY', '')
        self.base_url = os.getenv('LLM_BASE_URL', '')
        self.model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        
        self._init_client()
        
        logger.info(f"LLM Client initialized: {self.provider} (model: {self.model})")
    
    def _init_client(self):
        """Inicializar el cliente según el proveedor"""
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            
        elif self.provider == "deepseek":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com/v1"
            )
            
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            
        elif self.provider == "groq":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            
        elif self.provider == "azure":
            from openai import AzureOpenAI
            self.client = AzureOpenAI(
                api_key=self.api_key,
                api_version=os.getenv('AZURE_API_VERSION', '2024-02-15-preview'),
                azure_endpoint=self.base_url
            )
            
        elif self.provider == "ollama":
            from openai import OpenAI
            self.client = OpenAI(
                api_key="ollama",  # No necesita key real
                base_url=os.getenv('OLLAMA_URL', 'http://localhost:11434/v1')
            )
            
        elif self.provider == "lm_studio":
            from openai import OpenAI
            self.client = OpenAI(
                api_key="lm-studio",
                base_url=os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')
            )
            
        elif self.provider == "custom":
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")
    
    def chat_completion(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None,
        **kwargs
    ) -> Dict:
        """
        Chat completion unificado para todos los proveedores
        """
        try:
            # Proveedores compatibles con OpenAI (OpenAI, DeepSeek, Groq, Azure, Ollama, LM Studio)
            if self.provider in ["openai", "deepseek", "groq", "azure", "ollama", "lm_studio", "custom"]:
                
                # Preparar parámetros
                params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                
                if max_tokens:
                    params["max_tokens"] = max_tokens
                elif "max_completion_tokens" in kwargs:
                    params["max_completion_tokens"] = kwargs["max_completion_tokens"]
                
                # Response format (solo OpenAI compatible)
                if response_format and self.provider in ["openai", "deepseek", "groq", "azure"]:
                    params["response_format"] = response_format
                
                response = self.client.chat.completions.create(**params)
                
                return {
                    "content": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    },
                    "provider": self.provider
                }
            
            # Proveedores que usan API diferente
            elif self.provider == "anthropic":
                # Adaptar mensajes para Anthropic
                system_prompt = ""
                user_messages = []
                
                for msg in messages:
                    if msg["role"] == "system":
                        system_prompt = msg["content"]
                    elif msg["role"] == "user":
                        user_messages.append({"role": "user", "content": msg["content"]})
                    elif msg["role"] == "assistant":
                        user_messages.append({"role": "assistant", "content": msg["content"]})
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens or 1000,
                    system=system_prompt,
                    messages=user_messages,
                    temperature=temperature,
                )
                
                return {
                    "content": response.content[0].text,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.input_tokens,
                        "completion_tokens": response.usage.output_tokens,
                        "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                    },
                    "provider": self.provider
                }
            
            else:
                raise ValueError(f"API no implementada para: {self.provider}")
                
        except Exception as e:
            logger.error(f"Error en LLM call ({self.provider}): {e}")
            return {
                "content": "",
                "error": str(e),
                "provider": self.provider
            }
    
    def chat_completion_json(
        self,
        messages: List[Dict],
        temperature: float = 0.7,
        **kwargs
    ) -> Dict:
        """
        Chat completion con respuesta JSON garantizada
        """
        # Añadir instrucción de formato JSON
        system_message = messages[0] if messages and messages[0].get("role") == "system" else None
        
        if system_message:
            system_message["content"] = system_message["content"] + "\n\nOutput ONLY valid JSON. No other text."
        else:
            messages.insert(0, {"role": "system", "content": "Output ONLY valid JSON. No other text."})
        
        # Para OpenAI, usar response_format
        if self.provider in ["openai", "deepseek", "groq"]:
            response = self.chat_completion(
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
                **kwargs
            )
        else:
            # Para otros proveedores, usar parsing manual
            response = self.chat_completion(
                messages=messages,
                temperature=temperature,
                **kwargs
            )
            
            # Intentar parsear JSON
            try:
                content = response.get("content", "")
                # Extraer JSON del texto
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    response["content"] = json_match.group()
                else:
                    response["error"] = "No JSON found in response"
            except Exception as e:
                logger.error(f"Error parsing JSON: {e}")
        
        return response


# ============================================
# INSTANCIA GLOBAL
# ============================================

_llm_client = None

def get_llm_client() -> LLMClient:
    """Singleton para el cliente LLM"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client