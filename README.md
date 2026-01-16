# SABIA - Agente de IA para Indústrias Paranaenses

![Status](https://img.shields.io/badge/status-development-yellow)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green)
![License](https://img.shields.io/badge/license-Proprietary-red)

Sistema inteligente especializado em consulta e análise de indústrias paranaenses utilizando Agentes de IA, RAG (Retrieval Augmented Generation) e LangChain.

## 📋 Visão Geral

**SABIA** é um backend robusto que fornece:

- 🤖 **Agente de IA** com OpenAI GPT-4 Turbo
- 🔍 **RAG (Retrieval Augmented Generation)** com Pinecone
- 📊 **Métricas detalhadas** de performance e consumo
- 🔐 **Autenticação JWT** com refresh tokens
- 📈 **Suporte para 14 setores** industriais paranaenses
- 💾 **Persistência** em MySQL Azure
- 🐳 **Containerização** completa com Docker

## 🎯 Setores Industriais Cobertos

- Alimentos
- Bebidas
- Construção Civil
- Madeira e Móveis
- Mineração
- Plástico e Borracha
- Tecnologia da Informação
- Automotivo
- Celulose e Papel
- Gráfico
- Metalmecânica
- Petróleo e Biocombustíveis
- Químico e Farmacêutico
- Têxtil, Vestuário e Couro

## 🚀 Início Rápido

### Pré-requisitos

- Python 3.10+
- Docker e Docker Compose
- Variáveis de ambiente configuradas

### Instalação Local

```bash
# 1. Clonar repositório
git clone <repository_url>
cd projeto-agente-ia

# 2. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# 5. Inicializar banco de dados
python -c "from src.models.database import init_db; init_db()"

# 6. Executar aplicação
python main.py dev
```

Acesse: http://localhost:3000/docs

### Instalação com Docker

```bash
# 1. Configurar variáveis de ambiente
cp .env.example .env
# Editar .env

# 2. Build e iniciar
docker-compose up -d

# 3. Verificar status
docker-compose logs -f api
```

Acesse: http://localhost:3000/docs

## 📁 Estrutura do Projeto

```
projeto-agente-ia/
├── src/
│   ├── config/              # Configurações globais
│   │   ├── settings.py      # Variáveis de ambiente
│   │   └── logging_config.py
│   ├── agent/               # Núcleo do agente
│   │   ├── base_agent.py    # Classe abstrata
│   │   ├── llm_agent.py     # Implementação OpenAI
│   │   └── tools.py         # Ferramentas disponíveis
│   ├── memory/              # Gerenciamento de memória
│   │   ├── conversation_memory.py
│   │   └── vector_store.py  # Integração Pinecone
│   ├── models/              # Modelos de dados
│   │   ├── database.py      # SQLAlchemy models
│   │   └── schemas.py       # Pydantic schemas
│   ├── api/                 # API FastAPI
│   │   ├── main.py          # App principal
│   │   ├── routes/          # Endpoints
│   │   └── middleware/      # Autenticação JWT
│   └── utils/               # Funções utilitárias
├── tests/
│   ├── unit/                # Testes unitários
│   └── integration/         # Testes de integração
├── main.py                  # Entry point
├── requirements.txt         # Dependências Python
├── Dockerfile               # Containerização
├── docker-compose.yml       # Orquestração
├── .env.example             # Template de variáveis
└── .gitignore              # Git ignore rules
```

## ⚙️ Configuração

### Variáveis de Ambiente (`.env`)

```env
# Ambiente
NODE_ENV=development
DEBUG=True
PORT=3000

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2048

# MySQL (Azure)
MYSQL_DB_HOST=bd-chatbot-mkt.mysql.database.azure.com
MYSQL_DB_USER=bdChatbotMkt
MYSQL_DB_PASSWORD=fGMuK8N698
MYSQL_DB_SCHEMA=sabia_relacionamento_db

# Pinecone
PINECONE_API_KEY=xxxxxxxxxxxxx
PINECONE_INDEX_NAME=agent-embeddings

# JWT
JWT_SECRET_TOKEN=y3DsjrrQ7upJgB/MNh6mIMK9mOo7Xw6urkkYGbCAIzI=
```

## 🔌 Endpoints da API

### Conversações

```
POST   /api/v1/agent/conversations              # Criar conversação
GET    /api/v1/agent/conversations              # Listar conversações
GET    /api/v1/agent/conversations/{id}         # Obter detalhes
```

### Agente

```
POST   /api/v1/agent/agent/execute              # Executar agente
GET    /api/v1/agent/agent/status               # Status do agente
```

### Métricas

```
GET    /api/v1/agent/metrics/conversation/{id}  # Métricas de conversação
GET    /api/v1/agent/metrics/user               # Uso de tokens do usuário
```

### Saúde

```
GET    /health                                  # Health check básico
GET    /health/db                               # Status do banco
GET    /health/system                           # Status geral
```

## 📊 Arquitetura Técnica

### Stack Tecnológico

- **Backend**: FastAPI + Uvicorn
- **LLM**: OpenAI GPT-4 Turbo
- **Framework IA**: LangChain
- **Vector Store**: Pinecone (500 GB)
- **Banco de Dados**: MySQL (Azure)
- **Armazenamento**: Azure Blob Storage
- **Autenticação**: JWT
- **ORM**: SQLAlchemy

### Fluxo de Execução

```
1. Requisição HTTP → FastAPI
2. Validação → Pydantic Schemas
3. Autenticação → JWT Middleware
4. RAG Search → Pinecone (busca semântica)
5. Execução → LangChain + OpenAI
6. Ferramentas → Vector Search, Calculator, DB Query
7. Persistência → MySQL (mensagens, métricas)
8. Resposta → JSON com métricas
```

### Métricas Coletadas

**Performance:**
- Tempo total de execução
- Tempo do LLM
- Tempo de busca RAG
- Tempo de execução de ferramentas

**Tokens:**
- Input tokens
- Output tokens
- Total tokens

**RAG:**
- Documentos recuperados
- Score médio de similaridade
- Score do melhor chunk
- Taxa de acerto (hit rate)

**Qualidade:**
- Taxa de sucesso
- Rating do usuário (1-5)
- Mensagens de erro

## 🧪 Testes

### Executar Testes

```bash
# Testes unitários
pytest tests/unit -v

# Testes de integração
pytest tests/integration -v

# Cobertura
pytest --cov=src tests/

# Testes de carga
locust -f tests/load/locustfile.py
```

## 🔒 Segurança

- ✅ Autenticação JWT com expiração
- ✅ Refresh tokens (7 dias)
- ✅ User non-root em containers
- ✅ Rate limiting por endpoint
- ✅ CORS configurável
- ✅ SSL no MySQL Azure
- ✅ Secrets em variáveis de ambiente

## 📈 Performance

**Métricas Esperadas:**
- Execução: 200-500ms (incluindo RAG)
- RAG Search: 50-150ms
- LLM Response: 100-300ms
- Tokens por requisição: 500-2000

**Limites:**
- Taxa de requisição: 60/minuto
- Histórico máximo: 50 mensagens em memória
- Documentos RAG: até 100 chunks por query

## 🔧 Modo Desenvolvimento

```bash
# Iniciar com reload automático
python main.py dev

# Com logs detalhados
python main.py dev --log-level DEBUG

# Shell interativo
python main.py shell
```

## 📦 Modo Produção

```bash
# Iniciar com múltiplos workers
python main.py run --workers 4

# Via Docker
docker build -t sabia-agente:latest .
docker run -p 3000:3000 -e OPENAI_API_KEY=sk-... sabia-agente:latest
```

## 🐛 Troubleshooting

### Erro de Conexão com MySQL

```bash
# Verificar se MySQL está rodando
docker-compose ps

# Reiniciar MySQL
docker-compose restart mysql

# Ver logs do MySQL
docker-compose logs mysql
```

### Erro de API Key

```bash
# Verificar se .env está correto
cat .env | grep OPENAI_API_KEY

# Testar conexão com OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-..."
```

### Erro de Pinecone

```bash
# Verificar índice no Pinecone
# Dashboard: https://app.pinecone.io

# Testar conexão no código
python -c "from src.memory.vector_store import vector_store; print(vector_store.initialized)"
```

## 📚 Documentação Adicional

- [API Swagger](http://localhost:3000/docs)
- [OpenAI API](https://platform.openai.com/docs)
- [LangChain Docs](https://python.langchain.com)
- [Pinecone Docs](https://docs.pinecone.io)
- [FastAPI Docs](https://fastapi.tiangolo.com)

## 🤝 Contribuindo

1. Criar branch para feature: `git checkout -b feature/nova-funcionalidade`
2. Commit changes: `git commit -am 'Adicionar nova funcionalidade'`
3. Push para branch: `git push origin feature/nova-funcionalidade`
4. Abrir Pull Request

## 📝 Licença

Proprietary - © 2024 IA Team

## ✉️ Suporte

Para dúvidas ou problemas, abrir issue no repositório.

---
