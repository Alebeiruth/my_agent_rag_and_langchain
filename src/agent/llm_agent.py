import logging
import time
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import asyncio

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.callbacks.base import BaseCallbackHandler

from src.config.settings import get_settings
from src.agent.base_agent import BaseAgent, AgentConfig, AgentStatus, ExecutionResult, Message
from src.agent.tools import tool_registry

logger = logging.getLogger("agent")
settings = get_settings()

@dataclass

