from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger("agent")

class AgentStatus(str, Enum):
    """Estados possiveis do agente."""
    IDLE = "idle"
    EXECUTING = "executing"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    ERROR = "error"

class AgenteConfig:
    """Configuração do agente."""

    def __init__(
            self,
            model: str = "gpt-4-turbo",
            temperature: float = 0.7,
            max_tokens: int = 2048,
            max_retries: int = 3,
            timeout_seconds: int = 30,
            system_prompt: Optional[str] = None

            ):
        
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.system_prompt = system_prompt or self._default_system_prompt()
    
    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "Você é um assistente inteligente e prestativo. "
            "Responda às perguntas do usuário de forma clara, concisa e precisa. "
            "Use as ferramentas disponíveis quando necessário para obter informações atualizadas."
        )

class ToolDefinition:
    """Definição de uma ferramenta disponível para o agente."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        required_inputs: List[str] = None,
        handler: Optional[callable] = None
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.required_inputs = required_inputs or []
        self.handler = handler
        self.enabled = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte definição para dicionário."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "required_inputs": self.required_inputs,
            "enabled": self.enabled
        }

class Message:
    """Representa uma mensagem em uma conversação."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.role = role 
        self.content = content
        self.timestamp = timestamp or datetime.utcnow()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

class ExecutionResult:
    """Resultado da execução do agente."""

    def __init__(
        self,
        sucess: bool,
        response: str,
        tool_calls: List[Dict[str, Any]] = None,
        execution_time_ms: float = 0.0,
        tokens_used: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = sucess
        self.response = response
        self.tool_calls = tool_calls or []
        self.execution_time_ms = execution_time_ms
        self.tokens_used = tokens_used or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "success": self.success,
            "response": self.response,
            "tool_calls": self.tool_calls,
            "execution_time_ms": self.execution_time_ms,
            "tokens_used": self.tokens_used,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

class BaseAgente(ABC):
    """Classe abstrata base para agentes de IA."""

    def __init__(self, name: str, config: AgenteConfig):
        self.name = name
        self.config = config
        self.status = AgentStatus.IDLE
        self.tools: Dict[str, ToolDefinition] = {}
        self.conversation_history: List[Message] = []
        self.created_at = datetime.utcnow()

        logger.info(f"Agente '{self.name}' inicilizado com modelo {self.config.model}")
    
    def register_tools(self, tool: ToolDefinition) -> None:
        """Registra uma ferramenta disponivel para o agente."""
        self.tools[tool.name] = tool
        logger.debug(f"Ferramenta '{tool.name}' registrada para agente '{self.name}'")
    
    def unregister_tools(self, tool_name: str) -> bool:
        """Remove uma ferramenta registrada."""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.debug(f"Ferramenta '{tool_name}' removida do agente '{self.name}'")
            return True
        return False
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Retorna lista de ferramentas disponíveis."""
        return [
            tool.to_dict()
            for tool in self.tools.values()
            if tool.enabled
        ]
    
    def add_message(self, role:str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Adiciona mensagem ao histórico de conversação."""
        message = Message(role=role, content=content, metadata=metadata)
        self.conversation_history.append(message)
        logger.debug(f"Mensagem adicionada: {role} - {len(content)} caracteres")
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retorna histórico de conversação."""
        history = [msg.to_dict() for msg in self.conversation_history]
        if limit:
            history = history[-limit:]
        return history
    
    def clear_conversation_history(self) -> None:
        """Limpa histórico de conversação."""
        self.conversation_history.clear()
        logger.info(f"Hisotirco de conversação do agente '{self.name}' foi limpo")
    
    def set_status(self, status: AgentStatus) -> None:
        """Define o status do agente."""
        self.status = status
        logger.debug(f"Status do agente '{self.name}' alterado para: {status.value}")
    
    @abstractmethod
    async def execute(
        self,
        user_input: str,
        user_tools: bool = True,
        conversation_id: Optional[int] = None
    ) -> ExecutionResult:
        """
        Executa o agente com entrada do usuário.
        
        Args:
            user_input: Entrada do usuário
            use_tools: Se deve usar ferramentas disponíveis
            conversation_id: ID da conversação (para contexto)
        
        Returns:
            ExecutionResult com resposta e metadados
        """
        pass

    @abstractmethod
    async def process_total_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Processa chamada de ferramenta.
        
        Args:
            tool_name: Nome da ferramenta
            tool_input: Inputs para a ferramenta
        
        Returns:
            Tuple[success, output]
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Retorna status atual do agente."""
        return {
            "name": self.name,
            "status": self.status.value,
            "model": self.config.model,
            "tools_coutn": len(self.tools),
            "conversation_history_length": len(self.conversation_history),
            "created_at": self.created_at.isoformat()
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}', status='{self.status.value}')>"