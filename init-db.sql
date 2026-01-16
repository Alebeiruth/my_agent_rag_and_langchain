-- ===== INICIALIZAÇÃO DO BANCO DE DADOS SABIA =====
-- Este script é executado automaticamente quando o MySQL inicia no Docker Compose

-- Verificar se o banco já existe
USE sabia_relacionamento_db;

-- ===== CRIAÇÃO DE TABELAS =====

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email_active (email, is_active),
    INDEX idx_created_at (created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabela de Conversações
CREATE TABLE IF NOT EXISTS conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(255),
    sector VARCHAR(100),
    system_prompt TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    INDEX idx_user_status (user_id, status),
    INDEX idx_sector_created (sector, created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabela de Mensagens
CREATE TABLE IF NOT EXISTS messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    role VARCHAR(50) NOT NULL,
    content LONGTEXT NOT NULL,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE,
    INDEX idx_conversation_role (conversation_id, role),
    INDEX idx_created_at (created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabela de Métricas do Agente
CREATE TABLE IF NOT EXISTS agent_metrics (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    conversation_id INT,
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    user_input LONGTEXT NOT NULL,
    response LONGTEXT NOT NULL,

-- Tempo (ms)
total_execution_time_ms FLOAT NOT NULL,
llm_execution_time_ms FLOAT NOT NULL,
rag_search_time_ms FLOAT NOT NULL,
tool_execution_time_ms FLOAT DEFAULT 0,

-- Tokens
input_tokens INT DEFAULT 0,
output_tokens INT DEFAULT 0,
total_tokens INT DEFAULT 0,

-- Ferramentas
tool_calls_count INT DEFAULT 0,
tool_calls_names JSON,
tool_calls_success_rate FLOAT DEFAULT 0,

-- RAG
rag_query LONGTEXT NOT NULL,
rag_results_count INT DEFAULT 0,
rag_average_score FLOAT DEFAULT 0,
rag_top_chunk_score FLOAT DEFAULT 0,
rag_hit_rate BOOLEAN DEFAULT FALSE,

-- Qualidade
user_rating INT,
is_successful BOOLEAN DEFAULT TRUE,
error_message TEXT,

-- Contexto
sector VARCHAR(100),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL,
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_conversation_created (conversation_id, created_at),
    INDEX idx_sector_created (sector, created_at),
    INDEX idx_execution_id (execution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela de Uso de Tokens
CREATE TABLE IF NOT EXISTS token_usage (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    input_tokens INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    model VARCHAR(100) DEFAULT 'gpt-4-turbo',
    cost_usd FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    INDEX idx_user_date (user_id, created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabela de Logs do Sistema
CREATE TABLE IF NOT EXISTS system_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    level VARCHAR(20) NOT NULL,
    logger_name VARCHAR(255) NOT NULL,
    message LONGTEXT NOT NULL,
    user_id INT,
    conversation_id INT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE SET NULL,
    INDEX idx_level_logger (level, logger_name),
    INDEX idx_created_at (created_at)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- Tabela de Rate Limiting
CREATE TABLE IF NOT EXISTS rate_limit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    endpoint VARCHAR(255) NOT NULL,
    request_count INT DEFAULT 1,
    window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    window_end TIMESTAMP NOT NULL,
    is_limited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
    INDEX idx_user_endpoint (user_id, endpoint)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci;

-- ===== DADOS INICIAIS =====

-- Inserir usuário de teste (IMPORTANTE: senha em produção deve ser diferente)
INSERT IGNORE INTO
    users (
        email,
        password_hash,
        full_name,
        role,
        is_active,
        is_verified
    )
VALUES (
        'admin@sabia.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUumpGom', -- password: admin123
        'Admin SABIA',
        'admin',
        TRUE,
        TRUE
    );

INSERT IGNORE INTO
    users (
        email,
        password_hash,
        full_name,
        role,
        is_active,
        is_verified
    )
VALUES (
        'demo@sabia.local',
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUumpGom', -- password: admin123
        'Demo User',
        'user',
        TRUE,
        TRUE
    );

-- ===== VIEWS ÚTEIS =====

-- View: Resumo de Métricas por Setor
CREATE OR REPLACE VIEW v_metrics_by_sector AS
SELECT
    sector,
    COUNT(*) as total_executions,
    ROUND(
        AVG(total_execution_time_ms),
        2
    ) as avg_execution_time_ms,
    ROUND(AVG(total_tokens), 0) as avg_tokens,
    ROUND(AVG(rag_average_score), 4) as avg_rag_score,
    SUM(
        CASE
            WHEN is_successful = TRUE THEN 1
            ELSE 0
        END
    ) / COUNT(*) as success_rate,
    MAX(created_at) as last_execution
FROM agent_metrics
WHERE
    sector IS NOT NULL
GROUP BY
    sector;

-- View: Uso de Tokens por Usuário
CREATE OR REPLACE VIEW v_user_token_usage AS
SELECT
    u.id,
    u.email,
    u.full_name,
    COUNT(am.id) as total_requests,
    SUM(am.input_tokens) as total_input_tokens,
    SUM(am.output_tokens) as total_output_tokens,
    SUM(am.total_tokens) as total_tokens,
    ROUND(
        AVG(am.total_execution_time_ms),
        2
    ) as avg_execution_time_ms,
    MAX(am.created_at) as last_request
FROM users u
    LEFT JOIN agent_metrics am ON u.id = am.user_id
    AND am.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
WHERE
    u.is_active = TRUE
GROUP BY
    u.id,
    u.email,
    u.full_name;

-- View: Conversações Ativas
CREATE OR REPLACE VIEW v_active_conversations AS
SELECT c.id, u.email, c.title, c.sector, COUNT(m.id) as message_count, c.created_at, c.updated_at
FROM
    conversations c
    JOIN users u ON c.user_id = u.id
    LEFT JOIN messages m ON c.id = m.conversation_id
WHERE
    c.status = 'active'
GROUP BY
    c.id,
    u.email,
    c.title,
    c.sector,
    c.created_at,
    c.updated_at
ORDER BY c.updated_at DESC;

-- ===== ÍNDICES ADICIONAIS =====

-- Índices para otimizar queries comuns
ALTER TABLE agent_metrics
ADD INDEX idx_user_sector (user_id, sector);

ALTER TABLE agent_metrics ADD INDEX idx_timestamp (created_at DESC);

ALTER TABLE messages
ADD INDEX idx_conversation_timestamp (
    conversation_id,
    created_at DESC
);

-- ===== GRANTS E PERMISSÕES =====

-- Garantir que o usuário tem todas as permissões necessárias
GRANT ALL PRIVILEGES ON sabia_relacionamento_db.* TO 'bdChatbotMkt' @'%';

FLUSH PRIVILEGES;

-- ===== INFORMAÇÕES DO BANCO =====

-- Exibir informações de inicialização
SELECT 'SABIA Database Initialization' as Status, 'Database created successfully' as Message, NOW() as Timestamp;

-- Mostrar número de tabelas criadas
SELECT COUNT(*) as Tables_Created
FROM information_schema.tables
WHERE
    table_schema = 'sabia_relacionamento_db'
    AND table_type = 'BASE TABLE';