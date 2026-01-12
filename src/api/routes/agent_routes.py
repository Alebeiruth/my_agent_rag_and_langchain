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

