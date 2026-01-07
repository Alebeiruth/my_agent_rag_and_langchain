import logging
import logging.handlers
import os
from pathlib import Path
from src.config.settings import get_settings

settings = get_settings()

def setup_logging():
    """Configura logging centralizado da aplicação."""

    # Criar diretório de logs, se não existir
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    # Remover handlers existentes para evitar duplicação
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Formato do logs
    log_format = logging.Formatter(settings.LOG_FORMAT)

    # Handler Console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.CONSOLE_LOG_LEVEL))
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # Handler Arquivo com Rotação
    file_handler = logging.handlres.RotatingFileHandler(
        filename=logs_dir / "app.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, settings.FILE_LOG_LEVEL))
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # Handler Arquivo de Erros
    error_handler = logging.FileHandler.RotatingFileHandler(
        filename=logs_dir / "error.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)
    root_logger.addHandler(error_handler)

    # Logger específico para Agentes
    agent_logger = logging.getLogger("agent")
    agent_logger.setLevel(getattr(logging, settings.AGENT_LOG_LEVEL))

    agent_file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "agent.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8"
    )

    # Logger específico para BD
    database_logger = logging.getLogger("database")
    database_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    db_file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "database.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8"
    )
    db_file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    db_file_handler.setFormatter(log_format)
    database_logger.addHandler(db_file_handler)

    # Logger específico para API
    api_logger = logging.getLogger("api")
    api_logger.setLevel(getattr(logging, settings.LOG_LEVEL))

    api_file_handler = logging.handlers.RotatingFileHandler(
        filename=logs_dir / "api.log",
        maxBytes=10_485_760,
        backupCount=5,
        encoding="utf-8"
    )
    api_file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    api_file_handler.setFormatter(log_format)
    api_logger.addHandler(api_file_handler)

    return root_logger

def get_logger(name: str = None) -> logging.Logger:
    """Retorna logger configurado com nome específico."""
    return logging.getLogger(name)