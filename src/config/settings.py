from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    """Configurações da aplicação usando Pydantic Settings v2."""

    # Ambiente
    NODE_ENV: str = "production"
    DEBUG: bool = False
    USE_MOCK_DATA: bool = False

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4-turbo"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 2048

     # MySQL (Azure)
    MYSQL_DB_HOST: str
    MYSQL_DB_PORT: int = 3306
    MYSQL_DB_USER: str
    MYSQL_DB_PASSWORD: str
    MYSQL_DB_SCHEMA: str
    DB_SSL: bool = True
    AZURE_CA_CERTIFICATE: str = ""
    MYSQL_POOL_SIZE: int = 5
    MYSQL_MAX_OVERFLOW: int = 10

    # Construir URL de conexão MySQL
    @property
    def MYSQL_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Pinecone
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "gcp-starter"
    PINECONE_INDEX_NAME: str = "agent-embeddings"
    PINECONE_DIMENSION: int = 1536 # Dimensão para modelos OpenAI

    # Embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # API
    PORT: int = 3000
    API_HOST: str = "0.0.0.0"
    API_WORKERS: int = 1
    API_RELOAD: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Memoria de Conversação
    MAX_CONVERSATION_HISTORY: int = 50
    MEMORY_RETENTION_DAYS: int = 30

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Cors
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # Autenticação
    USER_DEFAULT_PASSWORD: str = ""
    RECAPTCHA_SECRET_KEY: str = ""
    KEY_SITE_RECAPTCHA: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Retorna instância singleton das configurações."""
    return Settings()