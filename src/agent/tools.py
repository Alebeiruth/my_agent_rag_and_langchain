import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json
from abc import ABC, abstractmethod

logger = logging.getLogger("agent")

class ToolHandler(ABC):
    """Classe abstrata para handlers de ferramentas."""

    @abstractmethod
    async def execute(self, **kwargs) -> Tuple[bool, str]:
        """Executa a ferramenta. Retorna (sucesso, )."""

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Retorna schema JSON da ferramenta."""
        pass

class DatabaseQueryTool(ToolHandler):
    """Ferramenta para executar queries no banco de dados."""

    def __init__(self, db_connection: Optional[Any] = None):
        self.name = "database_query"
        self.description = "Executa queries SQL no banco de dados MySQL."
        self.db_connection = db_connection
    
    async def execute(self, query:str, query_type: str = "SELECT") -> Tuple[bool, str]:
        """Executa query no banco"""
        try:
            if not self.db_connection:
                return False, "Conexão com o banco de dados não está configurada."
            
            query_type = query_type.upper()
            if query_type not in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
                return False, f"Tipo de query '{query_type}' não suportado."
            
            logger.info(f"Executando {query_type} query no banco de dados.")

            # Placeholder para execução real
            # Aqui voce usaria seu ORM (SQLAlchemy, etc.) ou driver direto

            result = {
            "status": "success",
            "rows_affected": 0,
            "data": []
            }

            output = json.dumps(result, ensure_ascii=False, indent=2, default=str)
            return True, output
        
        except Exception as e:
            logger.error(f"Erro em database_query: {str(e)}")
            return False, f"Erro ao executar query: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query SQL a executar"
                },
                "query_type": {
                    "type": "string",
                    "description": "Tipo de query: SELECT, INSERT, UPDATE, DELETE",
                    "enum": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                    "default": "SELECT"
                }
            },
            "required": ["query"]
        }
    
class VectorSearchTool(ToolHandler):
    """Ferramenta para busca em vector store (Pinecone/RAG)"""

    def __init__(self, vector_store: Optional[Any] = None):
        self.name = "vector_search"
        self.description = "Busca documentos similares em vector strore usando embeddings."
        self.vector_store = vector_store

    async def execute(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
        namespace: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Executa busca em vector store"""
        try:
            if not self.vector_store:
                return False, "Vector store não está configurada."
            
            logger.info(f"Executando vector_search: {query}")

            # Placeholder para integração com Pinecone
            # Aqui voce geraria embedding e faria busca no Pinecone

            results = [
                {
                    "id": f"doc_{i}",
                    "score": 0.95 - (i * 0.05),
                    "content": f"Documento similar {i+1} relacionado a '{query}'",
                    "metadata": {
                        "source": f"source_{i}",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
                for i in range(top_k, 5)
            ]

            output = json.dumps(results, ensure_ascii=False, indent=2, default=str)
            logger.debug(f"Vector search retornou {len(results)} resultados")
            return True, output
        
        except Exception as e:
            logger.error(f"Erro em vector_search: {str(e)}")
            return False, f"Erro ao executar vector search: {str(e)}"
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query de busca"
                }, 
                "top_k": {
                    "type": "integer",
                    "description": "Número de resultados a retornar",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 100
                },
                "threshold": {
                    "type": "number",
                    "description": "Limite de similaridade (0-1)",
                    "default": 0.7,
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "namespace": {
                    "type": "string",
                    "description": "Namespace no vector store (opcional)"
                }
            },
            "required": ["query"]
        }

class CalculatorTool(ToolHandler):
    """Ferramenta para calulos matemáticos"""

    def __init__(self):
        self.name = "calculator"
        self.description = "Realiza cálculos matemáticos simples."
    
    async def execute(self, expression: str) -> Tuple[bool, str]:
        """Executa expressão matemática"""
        try:
            logger.info(f"Executando calculo: {expression}")

            # Whitelist de caracteres permitidos
            allowed_chars = set("0123456789+-*/.()% ")
            if not all(c in allowed_chars for c in expression):
                return False, "Expressão contém caracteres inválidos."
            
            # Avalia a expressão de forma segura
            result = eval(expression)

            

            