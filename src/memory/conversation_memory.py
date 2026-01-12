import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json

logger = logging.getLogger("agent")

@dataclass
class ConversationEntry:
    """Representa uma entrada no historico de conversas"""
    id: int
    conversation_id: int
    role: str # 'user' ou 'assistant', "system"
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }

@dataclass
class Conversation:
    """Representa uma conversação completa"""
    id: int
    user_id: int
    title: str
    sector: Optional[str]
    system_prompt: Optional[str]
    status: str # 'active', 'archived', 'closed'
    created_at: datetime
    updated_at: datetime
    entries: List[ConversationEntry] = None

    def __post_init__(self):
        if self.entries is None:
            self.entries = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "sector": self.sector,
            "system_prompt": self.system_prompt,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "entries_count": len(self.entries),
            "entries": [entry.to_dict() for entry in self.entries],
        }

class ConversationMemory:
    """Gerencia historico de conversação com persistencia e cache"""

    def __init__(self, max_memory_size: int = 50, retention_days: int = 30):
        """
        Inicializa o gerenciador de memória.
        
        Args:
            max_memory_size: Número máximo de mensagens em memória
            retention_days: Dias para manter histórico em banco de dados
        """
        self.max_memory_size = max_memory_size
        self.retention_days = retention_days

        # Cache em memoria
        self.memory_cache: Dict[int, List[ConversationEntry]] = {}
        self.conversation_cache: Dict[int, Conversation] = {}

        logger.info(f"ConversationMemory initialized with max_memory_size={max_memory_size} and retention_days={retention_days}d")

    def add_entry(
            self,
            conversation_id: int,
            role: str,
            content: str,
            metadata: Optional[Dict[str, Any]] = None,
            entry_id: Optional[int] = None
    ) -> ConversationEntry:
        """
        Adiciona entrada ao histórico de conversação.
        
        Args:
            conversation_id: ID da conversação
            role: "user", "assistant" ou "system"
            content: Conteúdo da mensagem
            metadata: Metadados adicionais
            entry_id: ID da entrada (se persistida em BD)
        
        Returns:
            ConversationEntry criada
        """
        if conversation_id not in self.memory_cache:
            self.memory_cache[conversation_id] = []
        
        entry = ConversationEntry(
            id=entry_id or -1,
            conversation_id=conversation_id,
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )

        self.memory_cache[conversation_id].append(entry)

        # Manter limite de tamanho da memória
        if len(self.memory_cache[conversation_id]) > self.max_memory_size:
            self.memory_cache[conversation_id].pop(0)

        logger.debug(f"Added entry to conversation {conversation_id}: {entry.to_dict()}")
        return entry
    
    def get_conversation_history(
            self,
            conversation_id: int,
            limit: Optional[int] = None,
            include_system: bool = True
        ) -> List[ConversationEntry]:
        """
        Retorna histórico de conversação.
        
        Args:
            conversation_id: ID da conversação
            limit: Número máximo de mensagens (mais recentes)
            include_system: Se incluir mensagens de sistema
        
        Returns:
            Lista de ConversationEntry
        """
        if conversation_id not in self.memory_cache:
            logger.debug(f"Conversação {conversation_id} não encontrada na memória.") 
            return []
        
        history = self.memory_cache[conversation_id]

        # Filtrar mensagens de sistema se necessário
        if not include_system:
            history = [e for e in history if e.role != "system"]

        # Aplicar limite
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_conversation_context(
            self,
            conversation_id: int,
            num_messages: int = 10,
    ) -> str:
        """
        Retorna contexto formatado para passar ao LLM.
        
        Args:
            conversation_id: ID da conversação
            num_messages: Número de mensagens anteriores
        
        Returns:
            String formatada com histórico
        """
        history = self.get_conversation_history(conversation_id, limit=num_messages)

        if not history:
            return ""
        
        context = "Historico de conversação anterior:\n"
        for entry in history:
            role_formatted = "Usuario" if entry.role == "user" else "Assistente"
            context += f"{role_formatted}: {entry.content}"
        
        return context

    def clear_conversation(self, conversation_id: int) -> bool:
        """
        Limpa histórico de conversação da memória.
        
        Args:
            conversation_id: ID da conversação
        
        Returns:
            True se limpou com sucesso
        """
        if conversation_id in self.memory_cache:
            del self.memory_cache[conversation_id]
            logger.info(f"Historico da conversação {conversation_id} limpo")
            return True

        return False
    
    def get_statistics(self, conversation_id: int) -> Dict[str, Any]:
        """
        Retorna estatísticas da conversação.
        
        Args:
            conversation_id: ID da conversação
        
        Returns:
            Dicionário com estatísticas
        """
        history = self.get_conversation_history(conversation_id, include_system=True)

        user_messages = [e for e in history if e.role == "user"]
        assistant_messages = [e for e in history if e.role == "assistant"]

        total_chars = sum(len(e.content) for e in history)
        avg_user_length = sum(len(e.content) for e in user_messages) / len(user_messages) if user_messages else 0
        avg_assistant_length = sum(len(e.content) for e in assistant_messages) / len(assistant_messages) if assistant_messages else 0

        return {
            "conversation_id": conversation_id,
            "total_messages": len(history),
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "total_characters": total_chars,
            "avg_user_message_length": round(avg_user_length, 2),
            "avg_assistant_message_length": round(avg_assistant_length, 2),
            "first_message": history[0].timestamp.isoformat() if history else None,
            "last_message": history[-1].timestamp.isoformat() if history else None,
        }

    def search_in_history(
        self,
        conversation_id: int,
        keyword: str,
        search_in_role: Optional[str] = None
    ) -> List[ConversationEntry]:
        """
        Busca por keyword no histórico de conversação.
        
        Args:
            conversation_id: ID da conversação
            keyword: Palavra-chave a buscar
            search_in_role: "user" ou "assistant" (opcional)
        
        Returns:
            Lista de ConversationEntry que contêm o keyword
        """
        history = self.get_conversation_history(conversation_id, include_system=True)

        keyword_lower = keyword.lower()
        results = []

        for entry in history:
            if search_in_role and entry.role != search_in_role:
                continue
            if keyword_lower in entry.content.lower():
                results.append(entry)
        
        logger.debug(f"Busca por '{keyword}': {len(results)} resultados encontrados")

        return results
    
    def export_conversation(
        self,
        conversation_id: int,
        format: str = "json"
    ) -> str:
        """
        Exporta conversação em diferentes formatos.
        
        Args:
            conversation_id: ID da conversação
            format: "json", "txt" ou "csv"
        
        Returns:
            String com conversação exportada
        """
        history = self.get_conversation_history(conversation_id, include_system=True)

        if format == "json":
            data = [entry.to_dict() for entry in history]
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif format == "txt":
            text = f"Conersação ID:  {conversation_id}\n"
            text += f"Gerada em: {datetime.utcnow().isoformat()}\n"
            text += "=" * 80 + "\n\n"

            for entry in history:
                role_formatted = "USUARIO" if entry.role == "user" else "ASSISTENTE"
                text += f"[{role_formatted}] {entry.timestamp.isoformat()}\n"
                text += f"{entry.content}\n\n"

            return text
    
        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            writer = csv.writer(output)
            writer.wrtiterow(["conversation_id", "role", "content", "timestamp"])

            for entry in history:
                writer.writerow([
                    entry.conversation_id,
                    entry.role,
                    entry.content,
                    entry.timestamp.isoformat()
                ])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Formato de exportação '{format}' não suportado.")
    
    def get_oldest_entries(
            self,
            conversation_id: int,
            days: int
        ) -> List[ConversationEntry]:
        """
        Retorna entries mais antigas que X dias (para limpeza).
        
        Args:
            conversation_id: ID da conversação
            days: Número de dias
        
        Returns:
            Lista de ConversationEntry antigas
        """
        history = self.get_conversation_history(conversation_id, include_system=True)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_entries = [e for e in history if e.timestamp < cutoff_date]

        logger.debug(f"Encontradas {len(old_entries)} entries com mais de {days} dias")

        return old_entries

    def cleanup_old_entries(self, conversattion_id: int, days: int) -> int:
        """
        Remove entries mais antigas que X dias.
        
        Args:
            conversation_id: ID da conversação
            days: Número de dias
        
        Returns:
            Número de entries removidas
        """
        if conversattion_id not in self.memory_cache:
            return 0
        
        old_entries = self.get_oldest_entries(conversattion_id, days)

        if not old_entries:
            return 0
        
        # Remover entrier antigas
        for entry in old_entries:
            self.memory_cache[conversattion_id].remove(entry)

        logger.info(f"Limpeza de {len(old_entries)} entries antigas de conversação {conversattion_id}")

        return len(old_entries)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas gerais de memória.
        
        Returns:
            Dicionário com estatísticas
        """
        total_conversations = len(self.memory_cache)
        total_entries = sum(len(entries) for entries in self.memory_cache.values())

        return {
            "total_conversations": total_conversations,
            "total_entries": total_entries,
            "max_memory_size": self.max_memory_size,
            "retention_days": self.retention_days,
            "conversations_breakdown": {
                conv_id: len(entries)
                for conv_id, entries in self.memory_cache.items()
            }
        }

# Instancia global para uso na aplicação
conversation_memory = ConversationMemory(
    max_memory_size=50,
    retention_days=30
)