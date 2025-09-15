# Alleato RAG Chat FastAPI

A clean, well-organized RAG (Retrieval-Augmented Generation) chat API built with FastAPI for Alleato's project management and construction intelligence system.

## 🏗️ Clean Architecture

This codebase has been completely reorganized following Python/FastAPI best practices:

```
/alleato-rag-chat-fastapi/
├── app/                          # FastAPI application layer
│   ├── main.py                   # FastAPI app setup & routes
│   ├── models.py                 # Pydantic models
│   └── config.py                 # Application configuration
├── core/                         # Business logic layer
│   ├── chat/                     # Chat functionality
│   │   ├── agent.py              # AI chat agent
│   │   └── prompts.py            # System prompts
│   ├── database/                 # Database layer
│   │   ├── connection.py         # Database connection pool
│   │   └── queries.py            # Database query functions
│   └── search/                   # Search functionality
│       └── search.py             # Document search functions
├── utils/                        # Shared utilities
│   └── logging.py                # Logging utilities
├── scripts/                      # Deployment & utility scripts
├── tests/                        # Test suite
├── .archive/                     # Archived unused components
├── main.py                       # Application entry point
├── requirements.txt              # Core dependencies
├── requirements-dev.txt          # Development dependencies
└── README.md                     # This file
```

## 🚀 Features

- **Clean Architecture**: Separation of concerns with clear layers
- **RAG Intelligence**: AI-powered chat with database context retrieval
- **PostgreSQL Integration**: Vector embeddings and document search
- **OpenAI Integration**: GPT-based conversational AI
- **Health Monitoring**: Built-in health checks and diagnostics
- **Production Ready**: Proper error handling and logging
- **Test Coverage**: Comprehensive test suite

## 📋 API Endpoints

- `GET /` - Service status
- `GET /health` - Health check with database and LLM verification
- `GET /test-database` - Database connectivity test
- `GET /test-search` - Search functionality test
- `POST /chat` - Main chat endpoint for AI conversations

## 🛠️ Quick Start

### 1. Environment Setup

Create a `.env` file with required variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/database

# OpenAI
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1

# Optional: For Render deployment
RENDER=true
```

### 2. Install Dependencies

```bash
# Core dependencies
pip install -r requirements.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

### 3. Run the Application

```bash
# Development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production server
python main.py
```

### 4. Test the API

```bash
# Health check
curl http://localhost:8000/health

# Chat example
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest project updates?",
    "conversation_history": [],
    "session_id": "test-session"
  }'
```

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

## 🏗️ Architecture Decisions

### Why This Structure?

1. **Separation of Concerns**: Clear boundaries between FastAPI app, business logic, and data layers
2. **Testability**: Each layer can be tested independently
3. **Maintainability**: Easy to locate and modify specific functionality
4. **Scalability**: Structure supports adding new features without complexity
5. **Python Standards**: Follows established Python package organization patterns

### What Was Cleaned Up?

- **Removed Broken Dependencies**: Archived complex Pydantic AI components with missing imports
- **Eliminated Duplication**: Combined multiple similar files into cohesive modules
- **Fixed Import Paths**: All imports now work correctly with the new structure
- **Standardized Naming**: Consistent naming conventions throughout
- **Archived Unused Code**: Moved complex but unused components to `.archive/` for future reference

## 🔧 Configuration

The application uses environment-based configuration through `app/config.py`. Key settings:

- **CORS Origins**: Configure allowed frontend origins
- **Database Settings**: PostgreSQL connection and SSL settings
- **LLM Configuration**: OpenAI API settings and model selection
- **Deployment Settings**: Environment-specific optimizations

## 📁 Archived Components

The following components were archived but preserved for future use:

- `rag_agent.py` - Complex Pydantic AI agent (had broken dependencies)
- `shared/` - Sophisticated shared utilities and AI components
- `tools/` - Web search and financial analysis tools
- `monitoring/` - Prometheus monitoring dashboard

These can be restored and integrated when needed, but the current clean structure focuses on the working core functionality.

## 🚀 Deployment

### Railway/Render Deployment

The application includes production configurations for cloud deployment:

- SSL handling for database connections
- Environment-based configuration
- Production logging setup
- Health check endpoints for monitoring

### Local Development

```bash
# Start with auto-reload
uvicorn main:app --reload

# Or use the included scripts
./scripts/start_production.sh
```

## 📈 Performance

- **Database Connection Pooling**: Optimized PostgreSQL connections
- **Async Operations**: Full async/await support throughout
- **Context Caching**: Smart document retrieval and context management
- **Error Handling**: Graceful degradation with proper error responses

## 🤝 Contributing

1. Follow the established architecture patterns
2. Add tests for new functionality
3. Update this README if adding major features
4. Use the provided linting tools: `black`, `isort`, `flake8`

## 📄 License

See LICENSE.md for details.

---

**Previous Issues Resolved:**
- ✅ Broken import dependencies fixed
- ✅ File organization standardized  
- ✅ Duplicate functionality eliminated
- ✅ Complex unused components archived
- ✅ FastAPI best practices implemented
- ✅ Production deployment optimized