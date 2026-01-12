import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

import openai
from pinecone import Pinecone, ServerlessSpec

from src.config.settings import get_settings

logger = logging.getLogger("agent")
settings = get_settings()

@dataclass
class Documente:
    """Representa um documento no vector store."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: datetime = None

    def __post_init__(self):
        """Converte para dicionario"""
        return{
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
@dataclass
class SearchResult:
    """Resultado de busca no vector store"""
    document_id: str
    content: str
    score: float # Similaridade (0-1)
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "document_id": self.document_id,
            "content": self.content,
            "score": round(self.score,4),
            "metadata": self.metadata
        }

class VectorStore:
    """Gerencia integração com Pinecone para RAG"""

    def __init__(self):
        """Inicializa conexão com Pinecone"""
        try:
            self.api_key = settings.PINECONE_API_KEY
            self.environment = settings.PINECONE_ENVIRONMENT
            self.index_name = settings.PINECONE_INDEX_NAME
            self.dimension = settings.PINECONE_DIMENSION
        
            # Inicializa cliente Pinecone
            self.pc = Pinecone(api_key=self.api_key)

            # Obter ou criar índice
            self.index = self._get_or_create_index()

            # Configurar cliente OpenAI para embeddings
            openai.api_key = settings.OPENAI_API_KEY
            self.embedding_model = settings.EMBEDDING_MODEL

            self.initialized = True
            logger.info(f"Vector inicilizado com Pinecone (indice: {self.index_name})")
        
        except Exception as e:
            logger.error(f"Erro ao inicilaizar VectorStore: {str(e)}")
            self.initialized = False
            self.index = None

    def _get_or_create_index(self):
        """Obtém indice existente ou cria novo"""
        try:
            # Verificar se indice existe
            indexes = self.pc.list_indexes()

            if self.index_name not in [idx.name for idx in indexes]:
                logger.info(f"Criando indice Pinecone: {self.index_name}")

                # Criar indice
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
            
            # Conectar ao indice
            index = self.pc.Index(self.index_name)
            logger.info(f"Conectado ao indice: {self.index_name}")

            return index
        
        except Exception as e:
            logger.error(f"Erro ao criar/obter inidice: {str(e)}")
            return None
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Gera embedding para texto usando OpenAI.
        
        Args:
            text: Texto para gerar embedding
        
        Returns:
            Lista de floats representando o embedding
        """
        try:
            # Truncar texto se muito longo
            max_tokens = 8000
            tokens = text.split()
            if len(tokens) > max_tokens:
                text = " ".join(tokens[:max_tokens])
                logger.warning(f"Texto truncado de {len(tokens)} para {max_tokens} tokens")

            # Gerar embedding via OpenAI
            response = await asyncio.to_thread(
                openai.Embedding.create,
                input=text,
                model=self.embedding_model
            )
            
            embedding = response["data"][0]["embedding"]
            logger.debug(f"Emebedding geraedo: {len(embedding)} dimensões")

            return embedding

        except Exception as e:
            logger.error(f"Erro ao gera embedding: {str(e)}")
            raise
    
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Adiciona documento ao vector store.
        
        Args:
            document_id: ID único do documento
            content: Conteúdo do documento
            metadata: Metadados (setor, fonte, etc)
            namespace: Namespace do Pinecone (opcional)
        
        Returns:
            True se adicionado com sucesso
        """
        if not self.initialized or not self.index:
            logger.error("VectorStore não inicializado")
            return False
        
        try:
            logger.info(f"Adcionando documento: {document_id}")

            # Gerar embedding
            embedding = await self.generate_embedding(content)

            # Preapara metadados
            meta = {
                **metadata,
                "content": content[:1000], # Armazenar snippet do conteudo
                "timestamp": datetime.utcnow().isoformat(),
                "content_length": len(content)
            }

            # Upsert no Pinecone
            vectors = [(document_id, embedding, meta)]

            await asyncio.to_thread(
                lambda: self.index.upsert(
                    vectors=vectors,
                    namespace=namespace
                )
            )

            logger.debug(f"Docuemento {document_id} adicionado ao Pinecone")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao adicionar documento: {str(e)}")
            return False
        
    async def search(
            self,
            query: str,
            top_k: int = 5,
            threshold: float = 0.7,
            namespace: Optional[str] = None,
            filter_metadata: Optional[Dict[str, Any]] = None
        ) -> List[SearchResult]:
        """
        Busca documentos similares no vector store.
        
        Args:
            query: Query de busca
            top_k: Número de resultados
            threshold: Limite de similaridade (0-1)
            namespace: Namespace do Pinecone (opcional)
            filter_metadata: Filtros por metadata (opcional)
        
        Returns:
            Lista de SearchResult ordenados por relevância
        """
        if not self.initialized or not self.index:
            logger.error("VectorStroe não incializado")
            return []
        
        try:
            logger.info(f"Buscando: '{query}' (top_k{top_k}, threshold={threshold})")

            # Gerar embedding da query
            query_embedding = await self.generate_embedding(query)

            #Executar busca
            results = await asyncio.to_thread(
                lambda: self.index.query(
                    vector=query_embedding,
                    top_k=top_k,
                    namespace=namespace,
                    include_metadata=True,
                    filter=filter_metadata if filter_metadata else None
                )
            )

            # Processa resultados
            search_results = []

            for match in results.get("marches", []):
                score = match.get("score", 0)

                # Filtrar por threshold
                if score < threshold:
                    continue

                metadata = match.get("metadata", {})
                content = metadata.pop("content", "")

                result = SearchResult(
                    document_id=match.get("id", ""),
                    content=content,
                    score=score,
                    metadata=metadata
                )

                search_results.append(result)

            logger.info(f"Busca retornou {len(search_results)} resultados acima do threshold")

            return search_results

        except Exception as e:
            logger.error(f"Erro ao buscar: {str(e)}")
            return []
    
    async def delete_document(
        self,
        document_id: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Deleta documento do vector store.
        
        Args:
            document_id: ID do documento
            namespace: Namespace do Pinecone (opcional)
        
        Returns:
            True se deletado com sucesso
        """
        if not self.initialized or not self.index:
            logger.error("VectorStore não inicializado")
            return False
        
        try:
            await asyncio.to_thread(
                lambda: self.index.delete(
                    ids=[document_id],
                    namespace=namespace
                )
            )

            logger.info(f"Documento {document_id} deletado")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao deletar documento: {str(e)}")
            return False
    
    async def batch_add_documents(
        self,
        documents: List[Document],
        namespace: Optional[str] = None,
        batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        Adiciona múltiplos documentos em batch.
        
        Args:
            documents: Lista de Document
            namespace: Namespace do Pinecone
            batch_size: Tamanho do batch
        
        Returns:
            Tuple (sucesso_count, erro_count)
        """
        if not self.initialized or not self.index:
            logger.error("VectorStore não inicilizado")
            return 0, len(documents)
        
        success_count = 0
        error_count = 0

        logger.info(f"Inicioando batch de {len(documents)} documentos")

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i+batch_size]

            try:
                # Gerar embeddings para batch
                embeddings = []
                for doc in batch:
                    embedding = await self.generate_embedding(doc.content)
                    embeddings.append(embedding)

                # Preparar vectors para upsert
                vectors = []
                for doc, embedding in zip(batch, embeddings):
                    meta = {
                        **doc.metadata,
                        "content": doc.content[:1000],
                        "timestamp": doc.timestamp.isoformat(),
                        "content_length": len(doc.content)
                    }
                    vectors.append((doc.id, embedding, meta))

                # Upsert batch
                await asyncio.to_thread(
                    lambda v=vectors: self.index.upsert(
                        vectors=v,
                        namespace=namespace
                    )
                )

                success_count += len(batch)
                logger.debug(f"Batch {i//batch_size + 1} adcionado com sucesso")
            
            except Exception as e:
                logger.error(f"Error ao adicionar batch: {str(e)}")
                error_count += len(batch)

        logger.info(f"Batch finalizado: {success_count} sucess, {error_count} erros")

        return success_count, error_count
    
    async def get_index_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Retorna estatísticas do índice Pinecone.
        
        Args:
            namespace: Namespace (opcional)
        
        Returns:
            Dicionário com estatísticas
        """
        if not self.initialized or not self.index:
            return {"error": "VectorStore não inicializado"}
        
        try:
            stats = await asyncio.to_thread(
                lambda: self.index.describe_index_stats()
            )

            return {
                "index_name": self.index_name,
                "total_vectors": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", 0),
                "namespaces": stats.get("namespaces", {}),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Erro ao obter estatisticas: {str(e)}")
            return {"error": str(e)}
        
    async def search_by_sector(
        self,
        query: str,
        sector: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[SearchResult]:
        """
        Busca documentos de setor específico.
        
        Args:
            query: Query de busca
            sector: Setor industrial (ex: "Alimentos")
            top_k: Número de resultados
            threshold: Limite de similaridade
        
        Returns:
            Lista de SearchResult
        """
        filter_metadata = {"sector": sector}

        return await self.search(
            query=query,
            top_k=top_k,
            threshold=threshold,
            filter_metadata=filter_metadata
        )

    async def similarity_search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Busca simples por similaridade sem threshold.
        
        Args:
            query: Query de busca
            top_k: Número de resultados
        
        Returns:
            Lista de SearchResult
        """
        return await self.search(
            query=query,
            top_k=top_k,
            threshold=0.0
        )
    
# Instancia global
vector_store = VectorStore()