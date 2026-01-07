from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class UserRolesEnum(str, Enum):
    """Roles de usuário no sistema."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class MessageRolesEnum(str, Enum):
    """Roles de mensagens em conversação."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class ConversationStatusEnum(str, Enum):
    """Status de uma conversa."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

# Auth
class UserCreate(BaseModel):
    """Schema para criação de usuário."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1)
    role: UserRolesEnum = UserRolesEnum.USER

class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    """Schema para retorno de dados do usuário."""
    id: int
    email: str
    full_name: str
    role: UserRolesEnum
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    """Schema para login."""
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    """Schema para retorno de tokens"""
    acess_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenRefreshRequest(BaseModel):
    """Schema para refresh de token."""
    refresh_token: str

# Conversação
class MessageCreate(BaseModel):
    """Schema para criação de mensagem."""
    content: str = Field(..., min_length=1, max_length=10000)
    conversation_id: int

class MessageResponse(BaseModel):
    """Schema para retorno de mensagem."""
    id: int
    conversation_id: int
    role: MessageRolesEnum
    content: str
    created_at: datetime

    class Config:
        from_Atributes = True

class ConversationCreate(BaseModel):
    """Schema para criação de conversação."""
    title: Optional[str] = Field(default=None, max_length=255)
    system_prompt: Optional[str] = None

class ConversationUpdate(BaseModel):
    """Schema para atualização de conversação."""
    title: Optional[str] = None
    status: Optional[ConversationStatusEnum] = None

class ConversationResponse(BaseModel):
    """Schema para retorno de conversação."""
    id: int
    user_id: int
    title: str
    status: ConversationStatusEnum
    system_prompt: Optional[str] = None
    messages_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConversationDetailResponse(ConversationResponse):
    """Schema detalhado para retorno de conversação com mensagens."""
    messages: List[MessageResponse] = []

# Agent
class AgenteExecuteRequest(BaseModel):
    """Schema para execução do agente."""
    conversation_id: int
    message: str = Field(..., min_length=1, max_length=10000)
    user_tools: bool = True
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=4096)

class ToolCall(BaseModel):
    """Schema para chamada de ferramenta pelo agente."""
    tool_name: str
    tool_input: Dict[str, Any]
    tool_output: Optional[str] = None

class AgenteExecuteResponse(BaseModel):
    """Schema para resposta de execução do agente."""
    conversation_id: int
    message_id: int
    response: str
    tool_calls: List[ToolCall] = []
    execution_time_ms: float
    tokens_used: Optional[Dict[str, int]] = None
    created_at: datetime

class AgentMemoryContext(BaseModel):
    """Schema para contexto de memória do agente."""
    conversation_id: int
    recent_messages: List[MessageResponse]
    vector_context: Optional[List[Dict[str, Any]]] = None
    user_context: Optional[Dict[str, Any]] = None


# Vector Store / Embeddings
class EmbeddingRequest(BaseModel):
    """Schema para requisição de embedding."""
    text: str = Field(..., min_length=1, max_length=10000)
    model: Optional[str] = None

class EmbeddingResponse(BaseModel):
    """Schema para resposta de embedding."""
    embedding: List[float]
    model: str
    token_count: int

class VectorSearchRequest(BaseModel):
    """Schema para busca em vector store."""
    query: str = Field(..., min_length=1, max_length=10000)
    top_k: int = Field(default=5, ge=1, le=100)
    conversation_id: Optional[int] = None
    treshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)


class VectorSearchResult(BaseModel):
    """Schema para resultado de busca em vector store."""
    id: str
    score: float
    metadata: Dict[str, Any]
    content: str

class VectorSearchResponse(BaseModel):
    """Schema para resposta de busca em vector store."""
    results: List[VectorSearchResult]
    query: str
    search_time_ms: float

# Tools
class ToolDefinition(BaseModel):
    """Schema para definição de ferramenta."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    required_inputs: List[str] = []
    enabled: bool = True

class ToolExecutionRequest(BaseModel):
    """Schema para requisição de execução de ferramenta."""
    tool_name: str
    tool_input: Dict[str, Any]

class ToolExecutionResponse(BaseModel):
    """Schema para resposta de execução de ferramenta."""
    tool_name: str
    sucess: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float

class AvailableToolsResponse(BaseModel):
    """Schema para resposta de ferramentas disponíveis."""
    tools: List[ToolDefinition]
    total_count: int

# Health & Status
class HealthCheckResponse(BaseModel):
    """Schema para resposta de health check."""
    status: str
    timestamp: datetime
    services: Dict[str, str]  # e.g., {"database": "ok", "vector_store": "ok"}

class SystemStatusResponse(BaseModel):
    """Schema para resposta de status do sistema."""
    environment: str
    debug: bool
    openai_connected: bool
    mysql_connected: bool
    pinecone_connected: bool
    timestamp: datetime

# Error
class ErrorResponse(BaseModel):
    """Schema para resposta de erro."""
    error: str
    message: str
    status_code: int
    timestamp: datetime
    request_id: Optional[str] = None

class ValidationError(BaseModel):
    """Schema para detalhes de erro de validação."""
    field: str
    message: str
    value: Optional[Any] = None