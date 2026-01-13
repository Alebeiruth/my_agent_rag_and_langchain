import logging
from typing import Optional, list
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.models.schemas import (
    AgenteExecuteRequest, AgenteExecuteResponse, ConversationCreate,
    ConversationResponse, ConversationDetailResponse, MessageResponse,
    HealthCheckResponse, SystemStatusResponse, ErrorResponse
)
from src.models.database import (
    get_db, db_manager, Conversation, Message, AgenteMetric, User
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
        db.roollback()
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
