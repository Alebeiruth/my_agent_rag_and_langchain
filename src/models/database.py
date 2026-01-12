import logging
from datetime import datetime
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool

from src.config.settings import get_settings

logger = logging.getLogger("database")
settings = get_settings()

# Base para modelos
Base = declarative_base()

# Engine MySQL
engine = create_engine(
    settings.MYSQL_URL,
    poolclass=QueuePool,
    pool_size=settings.MYSLQ_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW,
    pool_pre_ping=True,
    echo=False,
    connect_args={"charset": "utf8mb4"}
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """Obtém sessão de banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==== MODELOS ====
class User(Base):
    "Modelo de usuarios"
    __tablename__ = "users"

    id = Column(Integer, primay_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255, nullable=False))
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="user") # admin, user, guest

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relacionamentos
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    metrics = relationship("AgentMetric", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_email_Active', 'email', 'is_active'),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"

class Conversation(Base):
    """Modelo de conversação"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False, index=True)

    title = Column(String(255), nullable=True)
    sector = Column(String(100), nullable=True, index=True) # Setor industrial
    system_prompt = Column(Text, nullable=True)

    status = Column(String(50), default='active') # active, archived, closed

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    metrics = relationship("AgentMetric", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_sector_created', 'sector', 'created_at')
    )

    def __repr__(self) -> str:
        return f"Conversation(id={self.id}, user_id{self.user_id}, sector='{self.sector}')>"
    
class Message(Base):
    """Modelo de mensagem em conversação"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False, index=True)

    role = Column(String(50), nullable=False) # user, assistant, system
    content = Column(Text, nullable=False)

    metadata = Column(JSON, nullable=True) # Informações adcionais (tokens, tool_calls, etc)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relacionamentos
    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index('idx_conversation_role', 'conversation_id', 'role'),
        Index('idx_created_at', 'created_at')
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role='{self.role}')>"

class AgenteMetric(Base):
    """Modelo de métricas de execução do agente"""