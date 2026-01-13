import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPBasicCredentials

from src.config.settings import get_settings
from src.models.database import get_db, db_manager, User
from sqlalchemy.orm import Session

logger = logging.getLogger("api")
settings = get_settings()

# Configuração de criptografia de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Esquema de segurança HHTP Bearer
security = HTTPBearer()

# === Funções de Senha ===

def hash_password(password: str) -> str:
    """Criptografa senha"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica senha contra hash"""
    return pwd_context.verify(plain_password, hashed_password)

# === Funções de JWT

def create_acess_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Cria JWT access token.
    
    Args:
        data: Dados para incluir no token
        expires_delta: Tempo de expiração customizado
    
    Returns:
        JWT token como string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_TOKEN,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.debug(f"JWT acess token criado para usuário {data.get('user_id')}")

        return encoded_jwt

    except Exception as e:
        logger.error(f"Erro ao criar JWT: {str(e)}")
        raise

def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Cria JWT refresh token.
    
    Args:
        data: Dados para incluir no token
    
    Returns:
        JWT refresh token como string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})

    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_TOKEN,
            algorithm=settings.JWT_ALGORITHM
        )

        logger.debug(f"JWT refresh token para usuario {data.get('user_id')}")

        return encoded_jwt
    
    except Exception as e:
        logger.error(f"Erro ao criar refresh token: {str(e)}")

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica e valida JWT token.
    
    Args:
        token: JWT token como string
    
    Returns:
        Payload decodificado ou None se inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_TOKEN,
            algorithms=[settings.JWT_ALGORITHM]
        )

        logger.debug(f"Token decodificado com sucesso para usuário {payload.get('user_id')}")

        return payload
    
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Token inválido")
        return None
    except Exception as e:
        logger.error(f"Erro ao decodificar token: {str(e)}")
        return None
    
# === Verficação de Token ===
async def verify_token(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Verifica JWT token e retorna dados do usuário.
    
    Args:
        credentials: Credenciais HTTP Bearer
        db: Sessão de banco de dados
    
    Returns:
        Dicionário com dados do usuário
    
    Raises:
        HTTPException: Se token inválido ou expirado
    """
    token = credentials.credentials

    #  Decodificar token
    payload = decode_token(token)

    if not payload:
        logger.warning("Tentativa de acesso com token inválido/expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar tipo de token (não deve ser refresh)
    if payload.get("type") == "refresh":
        logger.warning("Tentativa de usar refresh token com acess token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail = "Refresh token não pode ser usado para acessar recursos",
            headers={"WWW=Authenticate": "Bearer"}
        )
    
    user_id = payload.get("user_id")

    if not user_id:
        logger.warning("Token não contém user_id")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Verificar se usuario existe e está ativo
    user = db_manager.get_user_by_id(db, user_id)

    if not user or not user.is_active:
        logger.warning(f"Usuário {user_id} não encontrado ou inativo")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario não encontrado ou inativo",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.debug(f"Token verificado para usuário {user_id}")

    return {
        "user_id": user_id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active
    }

async def verify_refresh_token(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Verifica refresh token (para renovar access token).
    
    Args:
        credentials: Credenciais HTTP Bearer
        db: Sessão de banco de dados
    
    Returns:
        Dicionário com dados do usuário
    
    Raises:
        HTTPException: Se token inválido
    """
    token = credentials.credemtials

    payload = decode_token(token)

    if not payload or payload.get("type") != "refresh":
        logging.warning("Tentativa de usar token inválido como refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db_manager.get_user_by_id(db, user_id)

    if not user or not user.is_Active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.debug(f"Refresh token verificado para usuario {user_id}")

    return {
        "user_id": user_id,
        "email": user.email,
        "role": user.role
    }

async def verify_admin(
    current_user: Dict[str, Any] = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Verifica se usuário é administrador.
    
    Args:
        current_user: Usuário atual verificado
    
    Returns:
        Dados do usuário se admin
    
    Raises:
        HTTPException: Se não for admin
    """
    if current_user["role"] != "admin":
        logger.warning(f"Usuário {current_user["user_id"]} tentou acessar recursos admin")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso restrito a administradores"
        )
    
    return current_user

async def verify_Active_user(
        current_user: Dict[str, Any] = Depends(verify_token)
    ) -> Dict[str, Any]:
    """
    Verifica se usuário está ativo.
    
    Args:
        current_user: Usuário atual verificado
    
    Returns:
        Dados do usuário se ativo
    
    Raises:
        HTTPException: Se não estiver ativo
    """
    if not current_user.get("is_active"):
        logger.warning(f"Usuário {current_user["user_id"]} inativo tentou acessar")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo"
        )
    
    return current_user

# === Classe de autenticação ===
class AuthManager:
    """Gerenciador de autenticação"""

    def __init__(self):
        self.pwd_context = pwd_context

    def authenticate_user(
        self,
        db: Session,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Autentica usuário com email e senha.
        
        Args:
            db: Sessão de banco de dados
            email: Email do usuário
            password: Senha em plaintext
        
        Returns:
            User se autenticado, None caso contrário
        """
        user = db_manager.get_user_by_email(db, email)

        if not user:
            logger.warning(f"Tentativa de login com email não registrado: {email}")
            return None

        if not verify_password(password, user.passeord_hash):
            logger.warning(f"Tentativa de login com senha incorreta {email}")
            return None
        
        if not user.is_active:
            logger.warning(f"Tentativa de login com usuário inativo: {email}")
            return None
        
        logger.info(f"Usuário autenticado: {email}")

        return user
    
def create_tokens(self, user:User) -> Dict[str, str]:
    """
    Cria access e refresh tokens para usuário.
    
    Args:
        user: Objeto User
    
    Returns:
        Dicionário com access_token e refresh_token
    """
    data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }

    acess_token = create_acess_token(data)
    refresh_toke = create_refresh_token(data)

    logger.info(f"Tokens criados para usuário {user.id}")
    
    return {
        "acess_token": acess_token,
        "refresh_token": refresh_toke,
        "token_type": "bearer",
        "expires_in": settings.JWT_EXPIRATION_HOURS * 3600
    }

def refresh_acess_token(self, refresh_token: str) -> Optional[str]:
    """
    Cria novo access token usando refresh token.
    
    Args:
        refresh_token: Refresh token válido
    
    Returns:
        Novo access token ou None se inválido
    """
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        logger.warning("Tentativa de refresh com token inválido")
        return None
    
    data = {
        "user_id": payload.get("user_id"),
        "email": payload.get("email"),
        "role": payload.get("role")
    }

    acess_token = create_acess_token(data)

    logger.info(f"Acess token renovado para usuário {payload.get('user_id')}")

    return acess_token

# Instância global
auth_manager = AuthManager()