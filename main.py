#!/usr/bin/env python 3
"""
Sistem de Agente de IA para Industrias
Entry point da aplicação
"""

import logging
import sys
from typing import Optional

import uvicorn
from fastapi import FastAPI

from src.config.settings import get_settings
from src.config.logging_config import setup_logging, get_logger
from src.models.database import init_db
from src.api.main import app
from src.api.routes.agent_routes import router as agent_router

logger = get_logger("main")
settings = get_settings()

def setup_routes(application: FastAPI) -> None:
    """
    Configura e inclui rotas na aplicação.
    
    Args:
        application: Instância FastAPI
    """
    try:
        logger.info("Configurando rotas da API...")

        # Incluir rotas do agente
        application.include_router(
            agent_router,
            prefix="/api/v1/agent",
            tags=["Agent"]
        )

        logger.info("Rotas do agente configuradas")

        # Aqui você pode adcionar mais rotas
        # from src.api.routes import auth_routes
        # app.include_router(auth_routes.router. prefix="/api/v1/auth", tags=["Auth"])

        logger.info("Todas as rotas froam configuradas com sucesso")
    
    except Exception as e:
        logger.error(f"Erro ao configurar rotas: {str(e)}")
        raise

def initialize_application() -> FastAPI:
    """
    Inicializada a aplicação.
    Returns:
        Instância FastAPI configurada
    """
    try:
        logger.info("=" * 80)
        logger.info("Sistema do Agente de IA")
        logger.info("=" * 80)
        logger.info(f"Versão: 1.0.0")
        logger.info(f"Ambiente: {settings.NODE_ENV}")
        logger.info(f"Debug: {settings.DEBUG}")
        logger.info(f"Host: {settings.API_HOST}")
        logger.info(f"Porta: {settings.PORT}")
        logger.info("=" * 80)

        # Inicializar banco de dados
        logger.info("Inicializando banco de dados...")
        init_db()
        logger.info("Bnaco de dados inicializado")

        # Configurar rotas
        setup_routes(app)

        logger.info("=" * 80)
        logger.info("Aplicação inicializada com sucesso!")
        logger.info("=" * 80)

        return app
    
    except Exception as e:
        logger.error(f"Erro critico ao inicializar aplicação: {str(e)}", exc_info=True)
        raise

def run_server(
        host: str = settings.API_HOST,
        port: int = settings.PORT,
        workers: int = settings.API_WORKERS,
        reload: bool = settings.API_RELOAD,
        log_level: str = settings.LOG_LEVEL.lower()
) -> None:
    """
    Executa servidor Uvicorn.

    Args:
        host: Host para bind
        port: Porta para escutar
        workers: Número de workers
        reload: Se deve fazer reload automático
        log_level: Nível de logging
    """
    logger.info(f"Iniciando servidor Uvicorn...")
    logger.info(f"  Host: {host}")
    logger.info(f"  Porta: {port}")
    logger.info(f"  Workers: {workers}")
    logger.info(f"  Reload: {reload}")
    logger.info(f"  Log Level: {log_level}")

    try:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=workers,
            reload=reload,
            log_level=log_level,
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro ao executar servidor: {str(e)}", exc_info=True)
        sys.exit(1)

def main(
        command: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        workers: Optional[int] = None,
        reload: Optional[bool] = None
) -> None:
    """
    Função principal.
    
    Args:
        command: Comando a executar (run, dev, etc)
        host: Host customizado
        port: Porta customizada
        workers: Workers customizado
        reload: Reload customizado
    """

    # Configurar logging
    setup_logging()

    # Usar valores de settings como padrão
    host = host or settings.API_HOST
    port = port or settings.PORT
    workers = workers or settings.API_WORKERS
    reload = reload if reload is not None else settings.API_RELOAD

    # Inicializar aplicação
    initialize_application()

    # Comando padrão é "run"
    command = command or "run"

    if command == "run":
        # Modo produção (mais workers)
        workers = workers or 4
        reload = reload and False
        logger.info("Modo produção: reload desabilitado, 4+ workers")
        run_server(host=host, port=port, workers=workers, reload=reload)

    elif command == "dev":
        " Modo desenvolvimento (reload, 1 worker)"
        workers = 1
        reload = True
        logger.info("Modo desenvolvimento: reload habilitado, 1 worker")
        run_server(host=host, port=port, workers=workers, reload=reload)
        
    elif command == "shell":
        # Shell interativo
        logger.info("Incializando shell interativo...")
        import code
        code.interact(local={"app": app, "settings": settings})
    
    else:
        logger.error(f"Comando desconhecido: {command}")
        logger.info("Comandos disponiveis: run, dev, shell")
        sys.exit(1)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Sistema de Agente de IA"
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "dev", "shell"],
        help="Comando a executar (padrão: run)"
    )

    parser.add_argument(
        "--host",
        default=None,
        helsp=f"Host para bind (padrão: {settings.API_HOST})"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"Porta para escutar (padrão: {settings.PORT})"
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"Número de workers (parão: {settings.API_WORKERS})"
    )

    parser.add_argument(
        "--reload",
        action="stone_true",
        help="Habilitar reload automático (desenvolvimento)"
    )

    args = parser.parse_args()

    try:
        main(
            command=args.command,
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload if args.reload else None
            )
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}", exc_info=True)
        sys.exit(1)