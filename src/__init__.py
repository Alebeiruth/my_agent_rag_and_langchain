"""
Sistema de Agente de IA para Indústrias
Versão 1.0.0
"""

__version__ = "1.0.0"
__author__ = "IA Agente"
__description__ = "Sisitema inteligente especializado em indústrias"

from src.config.settings import get_settings
from src.config.logging_config import get_logger

__all__ = ["get_settings", "get_logger"]