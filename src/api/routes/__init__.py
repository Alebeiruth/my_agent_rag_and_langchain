"""Módulo de rotas de API"""

from src.api.routes.agent_routes import  router as agent_router
from src.api.routes.agent_routes import router as auth_router

__all__ = ["agent_router", "auth_router"]