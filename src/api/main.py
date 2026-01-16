import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHHTPException

from src.config.settings import get_settings
from src.config.logging_config import setup_logging, get_logger
from src.models.database import init_db, db_manager

logger = get_logger("api")
settings = get_settings()

# ===== LIFESPAN EVENT =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia eventos de startup e shutdown da aplicação"""
    # Startup
    logger.info("=" * 80)
    logger.info("Iniciando aplicação Agente de IA")
    logger.info(f"Ambiente: {settings.NODE_ENV}")
    logger.info(f"Debug: {settings.DEBUG}")
    logger.info(f"Modelo LLM: {settings.OPENAI_MODEL}")
    logger.info(f"Banco de dados: {settings.MYSQL_DB_HOST}")
    logger.info("=" * 80)
    
    try:
        # Incializar logging
        setup_logging()
        logger.info("Sistema de logging configurado")

        # Inicializar banco de dados
        init_db()
        logger.info("Bnaco de dados inicializado")

        # Testar conexão com banco
        db = db_manager.get_sesssion()
        try:
            db.execute("SELECT 1")
            logger.info("Conexão com MySQL estabelecida")
        finally:
            db.close()
        

        logger.info("Aplicação iniciada com sucesso!")

    except Exception as e:
        logger.error(f"Erro ao inicializar aplicação: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Encerrando aplicação...")
    logger.info("Aplicação encerrada com sucesso")


# ==== CRIAR APLICAÇÃO ====

app = FastAPI(
    title="Agente de IA",
    description="Sistema inteligente especializado em indústria paranaenses",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None
)

# ==== MIDDLEWARE CORS ====
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_hearders=settings.CORS_ALLOW_HEADERS
)

# === MIDDLEWARE CUSTOMIZADO ===
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Adciona request ID e rastreia tempo de requisição"""
    import uuid

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    import time
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.hearders["X-Process-Time"] = str(process_time)
    response.hearders["X-Request-ID"] = request_id

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Tempo: {process_time:.2f}s - "
        f"Request ID: {request_id}"
    )

    return response

# === EXCEPTION HANDLERS ===
@app.exception_handler(StarletteHHTPException)
async def http_exception_handler(request: Request, exc: StarletteHHTPException):
    """Handler para exceções HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Validação de dados falhou",
            "details": exc.errors(),
            "status_code": 422,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exceotion_handler(request: Request, exc: Exception):
    """Handler geral para exceções não tratadas"""
    logger.error(f"Errro não tratado: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "Erro interno do servidor" if settings.NODE_ENV == "production" else str(exc),
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

# === ROTAS SAUDE === 
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check básico"""
    return {
        "statu": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.NODE_ENV,
        "debug": settings.DEBUG
    }

@app.get("/health/db", tags=["Health"])
async def health_checj_db():
    """Verificar saude do banco de dados"""
    try:
        db = db_manager.get_session()
        try:
            db.execute("SELECT 1")
            status_db = "healthy"
        finally:
            db.close()
    except Exception as e:
        status_db = "unhealthy"
        logger.error(f"Erro ao verificar saúde do banco: {str(e)}")

    return {
        "database": status_db,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health/system", tags=["Health"])
async def healt_check_system():
    """Retorna status geral do sistema"""
    try:
        db = db_manager.get_session()
        try:
            system_health = db_manager.get_system_health(db)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Erro ao obter status do sistema: {str(e)}")
        system_health = system_health
    
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_health
    }

@app.get("/", tags=["Root"])
async def root():
    """Endpoint raiz com informações da API"""
    return {
        "name": "Agente de IA",
        "description": "Sistema inteligente especializado em indústrias paranaenses",
        "version": ".0.0",
        "environment": settings.NODE_ENV,
        "documentation": "/docs" if settings.DEBUG else "N/A",
        "endpoints": {
            "health": "/health",
            "health_db": "/health/db",
            "health_system": "/health/system",
            "docs": "/docs" if settings.DEBUG else "N/A"
        }
    }

# ===== IMPORTAR ROTAS =====
# Rotas serão importadas aqui depois de criadas
from src.api.routes import agent_routes
app.include_router(agent_routes.router, prefix="/api/v1/agent", tags=["Agent"])

if __name__ == "__manin__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.PORT,
        workers=settings.API_WORKERS,
        reload=settings.API_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )