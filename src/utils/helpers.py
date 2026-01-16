import logging
import re
from typing import Any, Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import json
import hashlib

logger = logging.getLogger("utils")

# === FORMATAÇÃO ===
def format_timestamp(timestamp: datetime, format_str: str = "%d/%m/%Y %H:%M:%S") -> str:
    """
    Formata datetime para string.
    
    Args:
        timestamp: Objeto datetime
        format_str: String de formato
    
    Returns:
        String formatada
    """
    try:
        return timestamp.strftime(format_str)
    except Exception as e:
        logger.error(f"Erro ao formatar timestamp: {str(e)}")
        return timestamp.isoformat()
    
def format_bytes(bytes_size: int) -> str:
    """
    Formata tamanho em bytes para string legível.
    
    Args:
        bytes_size: Tamanho em bytes
    
    Returns:
        String formatada (ex: "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    
    return f"{bytes_size:.2f} PB"

def format_duration(milliseconds: float) -> str:
    """
    Formata duração em milissegundos para string legível.
    
    Args:
        milliseconds: Duração em ms
    
    Returns:
        String formatada (ex: "1.5s", "234ms")
    """
    if milliseconds < 1000:
        return f"{milliseconds:.0f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds/1000:.2f}s"
    else:
        minutes = milliseconds / 60000
        return f"{minutes:.2f}m"

def format_tokens(tokens: int) -> str:
    """
    Formata número de tokens com separador de milhares.
    
    Args:
        tokens: Número de tokens
    
    Returns:
        String formatada (ex: "1,234,567")
    """
    return f"{tokens:,}"

def format_porcentage(value: float, decimal_places: int = 2) -> str:
    """
    Formata valor como porcentagem.
    
    Args:
        value: Valor entre 0 e 1
        decimal_places: Casas decimais
    
    Returns:
        String formatada (ex: "87.50%")
    """
    return f"{value*100:.{decimal_places}f}%"

# === Validação ===
def is_valid_email(email: str) -> bool:
    """
    Valida formato de email.
    
    Args:
        email: Email a validar
    
    Returns:
        True se válido
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_sector(sector: str, valid_sectors: List[str]) -> bool:
    """
    Valida se setor está na lista de setores válidos.
    
    Args:
        sector: Setor a validar
        valid_sectors: Lista de setores válidos
    
    Returns:
        True se válido
    """
    return sector.lower() in [s.lower() for s in valid_sectors]

def is_safe_string(text: str, max_length: int = 10000) -> bool:
    """
    Valida se string é segura para processamento.
    
    Args:
        text: Texto a validar
        max_length: Comprimento máximo
    
    Returns:
        True se segura
    """
    if not isinstance(text, str):
        return False
    
    if len(text) > max_length:
        return False
    
    # Verificar caracteres de controle perigosos
    dangerous_chars = ["\x00", "\x01", "\x02", "\x03", "\x04", "\x05"]
    for char in dangerous_chars:
        if char in text:
            return False
    
    return False

def is_valid_json(json_str: str) -> bool:
    """
    Valida se string é JSON válido.
    
    Args:
        json_str: String JSON
    
    Returns:
        True se válido
    """
    try:
        json.loads(json_str)
        return True
    except (json.JSONDecodeError, TypeError):
        return False

# === Limpeza e Normalização
def clean_text(text: str) -> str:
    """
    Limpa e normaliza texto.
    
    Args:
        text: Texto a limpar
    
    Returns:
        Texto limpo
    """
    # Remover espaços em brancos extras
    text = re.sub(r"\s+", " ", text)

    # Remover caracteres especiais desnecessários
    text = text.strip()

    return text

def sanitize_input(text: str, max_lenght: int = 10000) -> str:
    """
    Sanitiza entrada do usuário.
    
    Args:
        text: Texto a sanitizar
        max_length: Comprimento máximo
    
    Returns:
        Texto sanitizado
    """
    # Truncar se necessario
    if len(text) > max_lenght:
        text = text[:max_lenght]

    # Remover caracteres perigosos
    text = re.sub(r'[<>\"\'%;()&+]', '', text)

    # Limpar
    text = clean_text(text)

    return text

def normalize_sector_name(sector: str) -> str:
    """
    Normaliza nome de setor.
    
    Args:
        sector: Nome do setor
    
    Returns:
        Setor normalizado (primeira letra maiúscula)
    """
    return sector.strip().title()

# === Hash e Segurança ===
def generate_hash(text: str, algorithm: str = "sha256") -> str:
    """
    Gera hash de texto.
    
    Args:
        text: Texto para fazer hash
        algorithm: Algoritmo (sha256, md5, etc)
    
    Returns:
        Hash em hexadecimal
    """
    try:
        hasher =  hashlib.new(algorithm)
        hasher.update(text.encode("utf-8"))
        return hasher.hexdigest()
    except Exception as e:
        logger.error(f"Erro ao gerar hash: {str(e)}")
        return ""

def generate_request_id() -> str:
    """
    Gera ID único para requisição.
    
    Returns:
        ID hexadecimal
    """
    import uuid
    return str(uuid.uuid4()).replace("-", "")

# === Cálculos ===
def calculate_average(values: List[float]) -> float:
    """
    Calcula média de valores.
    
    Args:
        values: Lista de valores
    
    Returns:
        Média ou 0 se lista vazia
    """
    if not values:
        return 0.0
    
    return sum(values) / len(values)

def calculate_percentile(values: List[float], percentile: int = 95) -> float:
    """
    Calcula percentil de valores.
    
    Args:
        values: Lista de valores
        percentile: Percentil desejado (0-100)
    
    Returns:
        Valor no percentil
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)

    return sorted_values[min(index, len(sorted_values) - 1)]

def calculate_success_rate(successes: int, total: int) -> float:
    """
    Calcula taxa de sucesso.
    
    Args:
        successes: Número de sucessos
        total: Total de tentativas
    
    Returns:
        Taxa entre 0 e 1
    """
    if total == 0:
        return 0.0
    
    return successes / total

# === Data e Hora ===
def get_time_range(days: int = 30) -> Tuple[datetime, datetime]:
    """
    Retorna range de datas (últimos X dias).
    
    Args:
        days: Número de dias para trás
    
    Returns:
        Tuple (data_inicio, data_fim)
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    return start_date, end_date

def is_within_time_range(
    timestamp: datetime,
    start_date: datetime,
    end_date: datetime
) -> bool:
    """
    Verifica se timestamp está dentro do range.
    
    Args:
        timestamp: Timestamp a verificar
        start_date: Data início
        end_date: Data fim
    
    Returns:
        True se dentro do range
    """
    return start_date <= timestamp <= end_date

def get_human_readable_time(timestamp: datetime) -> str:
    """
    Retorna timestamp em formato legível (ex: "há 2 horas").
    
    Args:
        timestamp: Timestamp a formatar
    
    Returns:
        String legível
    """
    now = datetime.utcnow()
    diff = now - timestamp

    seconds = diff.total_seconds()

    if seconds < 60:
        return "agora mesmo"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"há {minutes}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"há {hours}h"
    elif seconds < 2592000:
        days = int(seconds / 86400)
        return f"há {days}d"
    else:
        return timestamp.strftime("%d/%m/%Y")
    
# === Conversão de tipos ===
def safe_int(value: Any, default: int = 0) -> int:
    """
    Converte valor para int com segurança.
    
    Args:
        value: Valor a converter
        default: Valor padrão se falhar
    
    Returns:
        Int ou default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Converte valor para float com segurança.
    
    Args:
        value: Valor a converter
        default: Valor padrão se falhar
    
    Returns:
        Float ou default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_json_loads(json_str: str, default: Dict = None) -> Dict:
    """
    Carrega JSON com segurança.
    
    Args:
        json_str: String JSON
        default: Dicionário padrão se falhar
    
    Returns:
        Dicionário ou default
    """
    if default is None:
        default = {}
    
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default

# === Paginação ===
def paginate(items: List[Any], page: int = 1, page_size: int = 20) -> Tuple[List[Any], Dict[str, Any]]:
    """
    Pagina lista de itens.
    
    Args:
        items: Lista de itens
        page: Número da página (começa em 1)
        page_size: Itens por página
    
    Returns:
        Tuple (items_paginados, metadata)
    """
    if page < 1:
        page = 1
    
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size

    paginated_items = items[start:end]
    total_pages = (total + page_size - 1) // page_size

    metadata = {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1
    }

    return paginated_items, metadata