import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.models.schemas import (
    UserCreate, UserResponse, LoginRequest, TokenResponse,
    TokenRefreshRequest, ErrorResponse
)
from src.models.database import get_db, db_manager, User
from src.api.middleware.auth import (
    verify_token, auth_manager, hash_password, verify_password
)

logger = logging.getLogger("api")
settings = get_settings()

router = APIRouter()

# === REGISTRO ===
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Auth"])
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registra novo usuário na plataforma.
    
    Args:
        user_data: Dados do novo usuário (email, senha, nome)
        db: Sessão de banco de dados
    
    Returns:
        UserResponse com dados do usuário criado
    
    Raises:
        HTTPException 400: Email já registrado
        HTTPException 422: Dados inválidos
    """
    try:
        logger.info(f"Tentativa de registro com email:" {user_data.email})

        # Validar email
        if not user_data.email or "@" not in user_data.email:
            logger.warning(f"Email inválido: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                DETAIL="Email inválido"
            )
        
        # Verificar se email já existe
        existing_user = db_manager.get_user_by_email(db, user_data.email)
        if existing_user:
            logger.warning(f"Email já registrado: {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já registrado na plataforma"
            )

        # Validar senha (minimo 8 caracteres)
        if len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Email já registrado na plataforma"
            )
        
        # Validar nome
        if not user_data.full_name or len(user_data.full_name) < 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Nome deve ter no mínimo 3 caracteres"
            )
        
        # Criar novo usuario
        new_user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            role="user",
            is_active=True,
            is_verified=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"Usuário registrado com sucesso: {new_user.email} (ID: {new_user.id})")

        return UserResponse(
            id=new_user.id,
            email=new_user.email,
            full_name=new_user.full_name,
            role=new_user.role,
            is_active=new_user.is_active,
            is_verified=new_user.is_verified,
            created_at=new_user.created_at
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Erro ao registrar usuário: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERRORm
            detail="Erro ao registrar usuário"
        )

# ===  Login ===
@router.post("/login", response_model=TokenResponse, tags=["Auth"])
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica usuário e retorna JWT tokens.
    
    Args:
        credentials: Email e senha do usuário
        db: Sessão de banco de dados
    
    Returns:
        TokenResponse com access_token, refresh_token e info adicional
    
    Raises:
        HTTPException 401: Email ou senha incorretos
        HTTPException 404: Usuário não encontrado
    """
    try:
        logger.info(f"Tentativa de login com email: {credentials.email}")

        # Autenticar usuário
        user = auth_manager.authenticate_user(db, credentials.email, credentials.password)

        if not user:
            logger.warning(f"Falha na autenticação para email: {credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authentucates": "Bearer"}
            )
        
        # Atualizar last_login
        user.last_login = datetime.utcnow()
        db.commit()

        # Gerar tokens
        tokens = auth_manager.create_tokens(user)

        logger.info(f"Login bem-sucedido para usuário: {user.email} (ID: {user.id})")

        return TokenResponse(
            acess_token=tokens["acess_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at
            )
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao fazer login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar login"
        )
    
# === Refresh Token ===
