import logging
import time
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler

from src.config.settings import get_settings
from src.agent.base_agent import BaseAgent, AgentConfig, AgentStatus, ExecutionResult, Message
from src.agent.tools import tool_registry

logger = logging.getLogger("agent")
settings = get_settings()

@dataclass
class AgentMetrics:
    """Metricas de desempenho do agente."""
    conversation_id: int
    execution_id: str
    user_input: str
    response: str

    # Tempo (ms)
    total_execution_time_ms: float
    llm_execution_time_ms: float
    rag_search_time_ms: float
    tool_execution_time_ms: float

    # Tokens
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Ferramentas
    tool_calls_count: int
    tool_calls_names: List[str]
    tool_calls_success_rate: float

    # rag
    rag_query: str
    rag_results_count: int
    rag_average_score: float
    rag_top_chunk_score: float
    rag_hit_rate: bool

    # Qualidade (preenchida depois)
    user_rating: Optional[int] = None
    is_successful: bool = True
    error_message: Optional[str] = None

    # Contexto
    sector: Optional[str] = None
    user_id: Optional[int] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
class MetricsCollector:
    """Collecto customizado para capturar métricas do LANGCHAIN."""

    def __init_(self):
        self.start_time = None
        self.llm_start_time = None
        self.token_count = {"input": 0, "output": 0}
    

    def on_llm_start(self, *args, **kwargs):
        self.llm_start_time = time.time()

    def on_llm_end(self, *args, **kwargs):
        if self.llm_start_time:
            self.token_count["output"] = kwargs.get("usage", {}).get("completion_tokens", 0)
            self.token_count["input"] = kwargs.get("usage", {}).get("prompt_tokens", 0)

class LLMAgent(BaseAgent):
    """Agente de IA com integração OpenAI, LangChain e coleta de métricas"""

    def __init__(
        self,
        name: str = "SABIA_Agent",
        config: Optional[AgentConfig] = None,
        enable_metrics: bool = True
    ):
        if config is None:
            config = AgentConfig(
                model=settings.OPENAI_MODEL,
                temperature=settings.OPENAI_TEMPERATURE,
                max_tokens=settings.OPENAI_MAX_TOKENS,
                system_prompt=self._build_system_prompt()
            )

        super().__init__(name, config)

        self.enable_metrics = enable_metrics
        self.llm = ChatOpenAI(
            model_name=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            openai_api_key=settings.OPENAI_API_KEY,
            callbacks=[MetricsCollector()] if enable_metrics else None
        )

        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=8000
        )

        self.agent_executor = None
        self._build_agent()

        logger.info(f"LLMAgent '{self.name}' inicializando com métricas: {enable_metrics}")

    @staticmethod
    def _build_system_prompt() -> str:
        """Constroi prompt do sistema com contexto de setores"""
        return f"""
Você é um especialista em indústrias paranaenses. Tem conhecimento profundo sobre:
- Alimentos, Bebidas, Construção Civil, Madeira e Móveis
- Mineração, Plástico e Borracha, Tecnologia da Informação
- Automotivo, Celulose e Papel, Gráfico, Metalmecânica
- Petróleo e Biocombustíveis, Químico e Farmacêutico, Têxtil/Vestuário/Couro

Você possui acesso a ferramentas para:
1. Buscar documentos similares em vector store (RAG)
2. Consultar banco de dados de histórico
3. Realizar cálculos matemáticos

Sempre:
- Use as ferramentas disponíveis para trazer informações precisas
- Cite a fonte de informações quando possível
- Mantenha respostas em português brasileiro
- Seja específico sobre o setor industrial mencionado
- Reconheça limitações quando não tiver informação suficiente
"""
    def _build_agent(self) -> None:
        """Constroi o agente com LangChain."""
        try:
            # Registra ferramentas padrão
            tool_registry.initialize_default_tools()

            # Obter tools do registry e converter para LangChain format
            tools_schema = tool_registry.get_tools_schema()

            # Tempalte de prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", self.config.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])

            # Criar agent com OpenAI Functions
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=[], # Tools adicionadas dinamicamente
                prompt=prompt,
            )

            self.agent_executor = AgentExecutor.from_agent_and_tools(
                agent=agent,
                tools=[],
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5
            )

            logger.info("Agente LangChain criado com sucesso.")
        
        except Exception as e:
            logger.error(f"Erro ao criar agente:: {str(e)}")
            raise
    
    async def _perform_rag_search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> Tuple[List[Dict[str, Any]], float, int]:
        """Executa busca RAG no Pinecone"""
        rag_start_time = time.time()

        try:
            sucess, output = await tool_registry.execute_tool(
                "vector_search",
                {
                    "query": query,
                    "top_k": top_k,
                    "threshold": threshold
                }
            )

            rag_time = (time.time() - rag_start_time) * 1000  # ms

            if sucess:
                results = json.loads(output)

                # Calcular métricas RAG
                scores = [result.get("score", 0) for result in results]
                avg_score = sum(scores) / len(scores) if scores else 0
                top_score = scores[0] if scores else 0
                hit_rate = len(results) > 0 and scores[0] >= threshold

                logger.info(f"RAG search completado: {len(results)} resultados, score médio: {avg_score:.3f}")

                return results, rag_time, avg_score, top_score, hit_rate
            else:
                logger.warning(f"RAG search falhou: {output}")
                return [], rag_time, 0.0, 0.0, False
        
        except Exception as e:
            logger.error(f"Erro em RAG search: {str(e)}")
            return [], (time.time() - rag_start_time) * 1000, 0.0, 0.0, False
        
    async def execute(
            self,
            user_input: str,
            user_tools: bool = True,
            conversation_id: Optional[int] = None,
            sector: Optional[str] = None,
            user_id: Optional[int] = None
        ) -> ExecutionResult:
        """
        Executa o agente com coleta de métricas.
        
        Args:
            user_input: Entrada do usuário
            use_tools: Se deve usar ferramentas
            conversation_id: ID da conversação
            sector: Setor industrial (para contexto)
            user_id: ID do usuário
        
        Returns:
            ExecutionResult com resposta e métricas
        """
        execution_id = f"{conversation_id}_{int(time.time()*1000)}"
        total_start_time = time.time()

        try:
            self.set_status(AgentStatus.THINKING)

            # Adcionar mensagem do usuário ao histórico
            self.add_message("user", user_input)

            # ==== RAG SEARCH ====
            logger.info(f"Iniciando RAG search para: {user_input}")
            rag_results, rag_time, rag_avg_score, rag_top_score, rag_hit_rate = await self._perform_rag_search(
                user_input,
                top_k=5,
                threshold=0.7
            )

            # ==== CONSTRUIR CONTEXTO ====
            rag_context = ""
            if rag_results:
                rag_context = "\n\nContexto do RAG:\n"
                for i, result in enumerate(rag_results[:3], 1): # Top 3 resultados
                    rag_context += f"{i}. {result.get('content', '')}\n"
            

            # ==== EXECUTAR AGENTE ====
            self.set_status(AgentStatus.EXECUTING)
            llm_start_time = time.time()

            try:
                # Combinar input com contexto RAG
                enriched_input = f"{user_input}{rag_context}" if rag_context else user_input

                # Executar agent (palceholder - em produção usar agent_executor.invoke)
                response = await self._execute_llm(enriched_input)

                llm_time = (time.time() - llm_start_time) * 1000

                # Adicionar resposta ao historico
                self.add_message("assistant", response)

                # ==== COLETAR METRICAS ====
                tool_calls = []
                tool_calls_names = []

                # Simulação de tokens (em produção, obter do LLM)
                input_tokens = len(enriched_input.split()) * 1.3
                output_tokens = len(response.split()) * 1.3
                total_tokens = input_tokens + output_tokens

                metrics = AgentMetrics(
                    conversation_id=conversation_id or 0,
                    execution_id=execution_id,
                    user_input=user_input,
                    response=response,
                    total_execution_time_ms=(time.time() - total_start_time) * 1000,
                    llm_execution_time_ms=llm_time,
                    rag_search_time_ms=rag_time,
                    tool_execution_time_ms=0.0,
                    input_tokens=int(input_tokens),
                    output_tokens=int(output_tokens),
                    total_tokens=int(total_tokens),
                    tool_calls_count=len(tool_calls),
                    tool_calls_names=tool_calls_names,
                    tool_calls_success_rate=1.0 if tool_calls else 0.0,
                    rag_query=user_input,
                    rag_results_count=len(rag_results),
                    rag_average_score=rag_avg_score,
                    rag_top_chunk_score=rag_top_score,
                    rag_hit_rate=rag_hit_rate,
                    sector=sector,
                    user_id=user_id,
                    is_successful=True
                )

                self.set_status(AgentStatus.IDLE)

                logger.info(f"Execução concluida: {metrics.total_execution_time_ms:.2f} ms, "
                            f"tokens: {metrics.total_tokens}, RAG hits: {metrics.rag_results_count}")
                
                return ExecutionResult(
                    sucess=True,
                    response=response,
                    tool_calls=tool_calls,
                    execution_time_ms=metrics.total_execution_time_ms,
                    tokens_used={
                        "input": metrics.input_tokens,
                        "output": metrics.output_tokens,
                        "total": metrics.total_tokens
                    },
                    metadata={
                        "metrics": metrics.to_dict(),
                        "rag_results_count": metrics.rag_results_count,
                        "rag_average_score": metrics.rag_average_score
                    }
                )
            
            except Exception as e:
                logger.error(f"Erro na execução do agente: {str(e)}")
                self.set_status(AgentStatus.ERROR)

                return ExecutionResult(
                    sucess=False,
                    response=f"Erro ao processar a solicitação: {str(e)}",
                    execution_time_ms=(time.time() - total_start_time) * 1000,
                    metadata={"error": str(e)}
                )
        except Exception as e:
            logger.error(f"Erro na execução LLM: {str(e)}")
            self.set_status(AgentStatus.ERROR)

            return ExecutionResult(
                sucess=False,
                response=f"Erro critico: {str(e)}",
                execution_time_ms=(time.time() - total_start_time) * 1000,
                metadata={"error": str(e)}
            )
        
    async def _execute_llm(self, input_text: str) -> str:
        """Executa LLM com tratamento de erro."""
        try:
            # Placeholder para real invocation
            # Em produção: response = awiat self.agent_executor.invoke({"input": input_text})

            # Para demonstração, retornar resposta generica
            response = (
                f"Baseado no contexto recuperado, analisei sua pergunta: '{input_text[:50]}...'\n"
                f"Utilizei ferramentas de busca semântica no vector store (Pinecone) para encontrar "
                f"documentos relacionados aos setores industriais paranaenses.\n"
                f"A resposta foi processada com temperatura 0.7 e até 2048 tokens."
            )

            return response
        
        except Exception as e:
            logger.error(f"Erro ao executar LLM: {str(e)}")
            raise
    
    async def process_tool_call(
            self,
            tool_name: str,
            tool_input: Dict[str, Any]
        ) -> Tuple[bool, str]:
        """Processa chamada de ferramenta"""
        logger.info(f"Processando tool call: {tool_name}")

        self.set_status(AgentStatus.TOOL_CALLING)

        try:
            sucess, output = await tool_registry.execute_tool(tool_name, tool_input)

            self.set_status(AgentStatus.IDLE)

            return sucess, output

        except Exception as e:
            logger.error(f"Erro ao processa tool call '{tool_name}': {str(e)}")
            self.set_status(AgentStatus.ERROR)

            return False, f"Erro ao executar ferramenta: {str(e)}"
    
    def get_metrics_schema(self) -> Dict[str, Any]:
         """Retorna schema das métricas para documentação."""
         return {
            "timing": {
                "total_execution_time_ms": "Tempo total de execução",
                "llm_execution_time_ms": "Tempo de execução do LLM",
                "rag_search_time_ms": "Tempo de busca no Pinecone",
                "tool_execution_time_ms": "Tempo de execução de ferramentas"
            },
            "tokens": {
                "input_tokens": "Tokens da requisição",
                "output_tokens": "Tokens da resposta",
                "total_tokens": "Total de tokens consumidos"
            },
            "tools": {
                "tool_calls_count": "Número de ferramentas chamadas",
                "tool_calls_names": "Nomes das ferramentas",
                "tool_calls_success_rate": "Taxa de sucesso (0-1)"
            },
            "rag": {
                "rag_results_count": "Documentos recuperados",
                "rag_average_score": "Score médio de similaridade",
                "rag_top_chunk_score": "Score do melhor chunk",
                "rag_hit_rate": "Se encontrou documentos relevantes"
            },
            "quality": {
                "user_rating": "Rating do usuário (1-5)",
                "is_successful": "Se a execução foi bem-sucedida"
            }
        }
