import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.models.schemas import (
    AgenteExecuteRequest, AgenteExecuteResponse, ConversationCreate, AgentExecutionResponse,
    ConversationResponse, ConversationDetailResponse, MessageResponse,
    HealthCheckResponse, SystemStatusResponse, ErrorResponse
)
from src.models.database import (
    get_db, db_manager, Conversation, Message, AgentMetric, User
)
from src.agent.llm_agent import LLMAgent, AgentMetrics
from src.memory.conversation_memory import conversation_memory
from src.api.middleware.auth import verify_token

logger = logging.getLogger("api")
settings = get_settings()

# Instancia global do agente
agent = LLMAgent(enable_metrics=True)

router = APIRouter()

# ===  CONVERSAÇÕES ===
@router.post("/conversations", response_model=ConversationResponse, tags=["Conversations"])
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Cria nova conversação"""
    try:
        logger.info(f"Criando conversação para usuário {current_user['user_id']}")

        new_conversation = Conversation(
            user_id = current_user["user_id"],
            title=conversation.title or f"Conversação {datetime.utcnow().isoformat}",
            system_prompt = conversation.system_prompt or agent.config.system_promp,
            status="active"
        )

        db.add(new_conversation)
        db.commit()
        db.refresh(new_conversation)

        logger.info(f"Conversação criada: ID {new_conversation.id}")

        return  ConversationResponse(
            id=new_conversation.ID,
            user_id=new_conversation.user_id,
            title=new_conversation.title,
            status=new_conversation.status,
            system_prompt=new_conversation.system_prompt,
            messages_count=0,
            created_at=new_conversation.created_at,
            updated_at=new_conversation.updated_at
        )
    
    except Exception as e:
        logger.error(f"Erro ao criar conversação: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar conversação: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationResponse], tags=["Conversations"])
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
    limit: int = 20
):
    """Lista conversações do usuário"""
    try:
        conversations = db_manager.get_user_conversations(
            db,
            current_user["user_id"],
            limit=limit
        )

        return [
            ConversationResponse(
                id=c.id,
                user_id=c.user_id,
                title=c.title,
                status=c.status,
                system_prompt=c.system_prompt,
                messages_count=len(c.messages),
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in conversations
        ]
    
    except Exception as e:
        logger.error(f"Erro ao listar conversações: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse, tags=["Conversations"])
async def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Obtém detalhes de conversação com histórico"""
    try:
        conversation = db_manager.get_conversation(db, conversation_id)

        if not conversation or conversation.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversação não encontrada"
            )
        
        messages = db_manager.get_conversation_messages(db, conversation_id)

        return ConversationDetailResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            status=conversation.status,
            system_prompt=conversation.system_prompt,
            messages_count=len(messages),
            messages=[
                MessageResponse(
                    id=m.id,
                    conversation_id=m.conversation_id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at
                )
                for m in messages
            ],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter conversação: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === Agente ===
@router.post("/agent/execute", response_model=AgenteExecuteResponse, tags=["Agent"])
async def execute_agent(
    request: AgenteExecuteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token)
):
    """Executa o agente com mensagem do usuário"""
    try:
        logger.info(f"Executando agente para conversação {request.conversation_id}")

        # Verificar se conversação pertence ao usuário
        conversation = db_manager.get_conversation(db, request.conversation_id)
        if not conversation or conversation.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversação não encontrada"
            )
        
        # === Obter contexto do usuario ===
        user = db_manager.get_user_by_id(db, current_user["user_id"])

        # Obter ultimas 5 conversas para contexto
        recent_conversations = db_manager.get_user_conversations(db, current_user["user_id"], limit=5)

        # Construir resuma das conversas anteriores
        conversation_history = ""
        if recent_conversations and len(recent_conversations) > 1: # Excluir a atual
            conversation_history = "\n\nConversa anteriores do usuário:\n"
            for i, conv in enumerate(recent_conversations[:4], 1):
                if conv.id != conversation.id:
                    messages_count = len(conv.messages)
                    conv_date = conv.created_at.strftime("%d/%m/%Y")
                    conversation_history += f"{i}. {conv.title or "Sem título"} ({conv_date}) - {messages_count} mensagens\n"
        
        # Obter ultimas mensagens da conversação atual para contexto
        messages = db_manager.get_conversation_messages(db, conversation.id, limit=5)
        recent_context = ""
        if messages:
            recent_context = "\n\nContexto recente da conversação:\n"
            for msg in reversed(messages[-3:]): # Ultima 3 mensagens
                role_str = "Usuario" if msg.role == "user" else "Assistente"
                recent_context += f"{role_str}: {msg.content[:200]}...\n"
        
        # Adicionar mensagem do usuário ao BD
        user_message = Message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()

        # Adcionar ao historico em memoria
        conversation_memory.add_entry(
            conversation_id=request.conversation_id,
            role="user",
            content=request.message
        )

        # ===  Criar prompt com contexto do usuario ===
        user_context_prompt = f"""
        CONTEXTO DO USUÁRIO:
        - Nome: {user.full_name}
        - Email: {user.email}
        - Usuário desde: {user.created_at.strftime("%d/%m/%Y")}
        - Setor de interesse: {conversation.sector or 'Não especificado'}
        {conversation_history}
        {recent_context}
        """

        # Executar agente
        execution_result = await agent.execute(
            user_input=user_context_prompt + "\n\nNova pergunta do usuário:\n" + request.message,
            use_tools=request.use_tools,
            conversation_id=request.conversation_id,
            sector=conversation.sector,
            user_id=current_user["user_id"]
        )

        if not execution_result.sucess:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=execution_result.response
            )

        # Adcionar resposta do assistente ao BD
        assistant_message = Message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=execution_result.response,
            metadata={
                "token": execution_result.tokens_used,
                "execution_time_ms": execution_result.execution_time_ms
            }
        )
        db.add(assistant_message)

        # Salvar métricas no BD
        metrics_dict = execution_result.metadata.get("metrics", {})
        metric = AgentMetric(
            user_id=current_user["user_id"],
            conversation_id=request.conversation_id,
            excution_id=metrics_dict.get("execution_id", ""),
            user_input=request.message,
            response=execution_result.response,
            total_execution_time_ms=metrics_dict.get("total_execution_time_ms", 0),
            llm_execution_time_ms=metrics_dict.get("llm_execution_time_ms", 0),
            rag_search_time_ms=metrics_dict.get("rag_search_time_ms", 0),
            tool_execution_time_ms=metrics_dict.get("tool_execution_time_ms", 0),
            input_tokens=execution_result.tokens_used.get("input", 0),
            output_tokens=execution_result.tokens_used.get("output", 0),
            total_tokens=execution_result.tokens_used.get("total", 0),
            tool_calls_count=metrics_dict.get("tool_calls_count", 0),
            tool_calls_names=metrics_dict.get("tool_call_names", []),
            tool_calls_sucess_rate=metrics_dict.get("tool_calls_sucess_rate", 0),
            rag_query=metrics_dict.get("rag_query", ""),
            rag_rasults_count=metrics_dict.get("rag_rasults_count", 0),
            rag_average_score=metrics_dict.get("rag_average_score", 0),
            rag_top_chunk_score=metrics_dict.get("rag_top_chunk_score", 0),
            rag_hit_rate=metrics_dict.get("rag_hit_rate", False),
            sector=conversation.sector,
            is_successful=execution_result.sucess
        )
        db.add(metric)

        # Atualizar conversa
        conversation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(assistant_message)
        db.refresh(metric)

        # Adcionar ao historico em memória
        conversation_memory.add_entry(
            conversation_id=request.conversation_id,
            role="assistant",
            content=execution_result.response,
            metadata={"execution_id": metric.id}
        )

        logger.info(f"Execução concluida: {execution_result.execution_time_ms:.2f}ms")

        return AgentExecutionResponse(
            conversation_id=request.conversation_id,
            message_id=assistant_message.id,
            response=execution_result.response,
            tool_calls=execution_result.tool_calls,
            execution_time_ms=execution_result.execution_time_ms,
            tokens_used=execution_result.tokens_used,
            created_at=assistant_message.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao executar agente: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao executar agente: {str(e)}"
        )

@router.get("/agente/status", response_model=dict, tags=["Agente"])
async def get_agent_status(current_user: dict = Depends(verify_token)):
    """Retorna status do agente"""
    try:
        return {
            "agent_name": agent.name,
            "status": agent.status.value,
            "model": agent.config.model,
            "temperature": agent.config.temperature,
            "max_tokens": agent.config.max_tokens,
            "tools_count": len(agent.get_available_tools()),
            "metrics_enable": agent.enable_metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Erro ao obter status do agente: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# === MÉTRICA ===
@router.get("/metric/conversation/{conversation_id}", response_model=List[dict], tags=["Metrics"])
async def get_conversation_metrics(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
    limit: int = 100
):
    """Obtém métricas de execução de uma conversação"""
    try:
        conversation = db_manager.get_conversation(db, conversation_id)
        if not conversation or conversation.user_id != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversação não encontrada"
            )
        
        metrics = db_manager.get_agent_metrics(db, conversation_id, limit=limit)

        return [
            {
                "execution_id": m.execution_id,
                "total_execution_time_ms": m.total_execution_time_ms,
                "llm_execution_time_ms": m.llm_execution_time_ms,
                "rag_search_time_ms": m.rag_search_time_ms,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "total_tokens": m.total_tokens,
                "rag_results_count": m.rag_results_count,
                "rag_average_count": m.rag_average_count,
                "rag_hit_rate": m.rag_hit_rate,
                "is_successful": m.is_successful,
                "created_at": m.created_at
            }
            for m in metrics 
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter métricas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/metrics/user", response_model=dict, tags=["Metrics"])
async def get_user_metrics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(verify_token),
    days: int = 30
):
    """Obtém métricas de uso de tokens do usuário"""
    try:
        token_usage = db_manager.calculate_user_token_usage(
            db,
            current_user["user_id"],
            days=days
        )

        return token_usage
    
    except Exception as e:
        logger.error(f"Erro ao obter métricas do usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# ===  Saúde ===
@router.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check do agente"""
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        services={
            "agent": "ok",
            "memory": "ok",
            "vector_store": "ok" if agent.enable_metrics else "disabled"
        }
    )

if __name__ == "__main__":
    pass