from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncGenerator
import asyncio
import json
import uuid

from rag_agent import search_agent
from shared.ai.agent_deps import AgentDeps
from shared.utils.db_utils import initialize_database
from shared.utils.config import load_settings
ADVANCED_TRACING = False
from pydantic_ai import Agent

app = FastAPI(title="RAG Agent API", version="1.0.0")

# Tracing disabled - OpenTelemetry dependencies removed
print("ℹ️  Tracing disabled for simplified deployment")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3004",
        "http://localhost:3005",
        "http://localhost:3006",
        "https://alleato-ai-dashboard.vercel.app",
        "https://rag-agent-chat.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings
settings = load_settings()

# Request/Response models
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: Optional[List[dict]] = None


async def stream_response(
    message: str, 
    conversation_history: List[ChatMessage],
    session_id: str
) -> AsyncGenerator[str, None]:
    """Stream agent responses as Server-Sent Events."""
    
    try:
        # Create and initialize dependencies
        deps = AgentDeps()
        await deps.initialize()
        
        # Build context from conversation history
        context = "\n".join([
            f"{msg.role}: {msg.content}" 
            for msg in conversation_history[-6:]
        ]) if conversation_history else ""
        
        # Build the user message with conversation context
        if context:
            prompt = f"""Previous conversation:
{context}

User: {message}"""
        else:
            prompt = message

        # Stream the agent execution
        try:
            # Use regular agent execution and simulate streaming
            result = await search_agent.run(prompt, deps=deps)
            # Extract the actual response content from the result
            if hasattr(result, 'data'):
                response_text = str(result.data)
            elif hasattr(result, 'output'):
                response_text = str(result.output)
            else:
                response_text = str(result)
            
            # Extract tool calls if available
            tool_calls = []
            if hasattr(result, '_tool_calls'):
                for tc in result._tool_calls:
                    tool_calls.append({
                        "tool": tc.name,
                        "args": tc.args
                    })
            
            # Stream the response character by character for smooth effect
            for i, char in enumerate(response_text):
                yield f"data: {json.dumps({'type': 'text', 'data': char})}\n\n"
                if i % 3 == 0:  # Add small delay every few characters
                    await asyncio.sleep(0.02)
            
            # Send final complete event
            yield f"data: {json.dumps({'type': 'complete', 'data': {'response': response_text, 'tool_calls': tool_calls}})}\n\n"
        
        except Exception as agent_error:
            # If agent fails, send error response
            print(f"Agent execution failed: {agent_error}")
            fallback_message = "I'm experiencing technical difficulties accessing the knowledge base. Please try again or ask me a general question about project management."
            
            # Stream the fallback message
            for char in fallback_message:
                yield f"data: {json.dumps({'type': 'text', 'data': char})}\n\n"
                await asyncio.sleep(0.02)
            
            yield f"data: {json.dumps({'type': 'complete', 'data': {'response': fallback_message, 'tool_calls': []}})}\n\n"
    
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    finally:
        # Clean up resources
        pass


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "RAG Agent API"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create and initialize dependencies
        deps = AgentDeps()
        await deps.initialize()
        
        # Build context
        context = "\n".join([
            f"{msg.role}: {msg.content}" 
            for msg in request.conversation_history[-6:]
        ]) if request.conversation_history else ""
        
        # Build the user message with conversation context  
        if context:
            prompt = f"""Previous conversation:
{context}

User: {request.message}"""
        else:
            prompt = request.message
        
        # Run agent with error handling
        try:
            result = await search_agent.run(prompt, deps=deps)
            # Extract the actual response content from the result  
            if hasattr(result, 'data'):
                response_text = str(result.data)
            elif hasattr(result, 'output'):
                response_text = str(result.output)
            else:
                response_text = str(result)
        except Exception as agent_error:
            # If agent fails, provide a fallback response
            print(f"Agent execution failed: {agent_error}")
            return ChatResponse(
                response=f"I apologize, but I'm experiencing technical difficulties accessing the knowledge base. However, I can still help with general questions about project management and business strategy. Please let me know how I can assist you with your specific needs.",
                session_id=session_id,
                tool_calls=None
            )
        
        # Extract tool calls from result if available
        tool_calls = []
        if hasattr(result, '_tool_calls'):
            for tc in result._tool_calls:
                tool_calls.append({
                    "tool": tc.name,
                    "args": tc.args
                })
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            tool_calls=tool_calls if tool_calls else None
        )
        
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        return ChatResponse(
            response="I'm experiencing technical difficulties. Please try again in a few moments.",
            session_id=request.session_id or str(uuid.uuid4()),
            tool_calls=None
        )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events."""
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    return StreamingResponse(
        stream_response(
            request.message, 
            request.conversation_history,
            session_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )


@app.get("/test-db")
async def test_database_connection():
    """Test database connection and dependencies."""
    import os
    
    try:
        from shared.ai.agent_deps import AgentDeps
        
        # Check environment first
        database_url = os.getenv("DATABASE_URL")
        db_url_present = database_url is not None
        db_url_length = len(database_url) if database_url else 0
        
        deps = AgentDeps()
        await deps.initialize()
        
        # Test basic database connectivity if pool exists
        if deps.db_pool and hasattr(deps.db_pool, 'acquire'):
            async with deps.db_pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                # Test if we can query the correct tables
                chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        else:
            result = "Database pool is None - fallback mode active"
            chunk_count = 0
            doc_count = 0
        
        return {
            "status": "success",
            "database_connection": deps.db_pool is not None,
            "test_query_result": result,
            "db_pool_initialized": deps.db_pool.pool is not None if deps.db_pool else False,
            "fallback_mode": deps.db_pool is None,
            "environment_check": {
                "DATABASE_URL_present": db_url_present,
                "DATABASE_URL_length": db_url_length,
                "DATABASE_URL_preview": database_url[:50] + "..." if database_url else "None"
            },
            "table_counts": {
                "chunks": chunk_count,
                "documents": doc_count
            }
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "error_type": type(e).__name__,
            "database_connection": False
        }

@app.get("/test-search")
async def test_search_endpoint():
    """Test search functionality directly."""
    try:
        from shared.ai.agent_deps import AgentDeps
        from tools.search_tools import get_recent_documents
        from types import SimpleNamespace
        
        deps = AgentDeps()
        await deps.initialize()
        
        ctx = SimpleNamespace()
        ctx.deps = deps
        
        # Test get_recent_documents
        docs = await get_recent_documents(ctx, limit=3)
        
        return {
            "status": "success",
            "database_connected": deps.db_pool is not None and hasattr(deps.db_pool, 'pool'),
            "pool_active": deps.db_pool.pool is not None if deps.db_pool else False,
            "documents_found": len(docs),
            "sample_titles": [doc.get('title', 'No title') for doc in docs[:2]] if docs else []
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/health")
async def health_check():
    """Detailed health check with dependency status."""
    
    health_status = {
        "status": "healthy",
        "checks": {
            "api": True,
            "llm_configured": bool(settings.llm_api_key),
            "model": settings.llm_model,
            "tracing": False,
            "metrics": False
        }
    }
    
    # Test vector store connection if needed
    try:
        # Add your vector store health check here
        health_status["checks"]["vector_store"] = True
    except Exception:
        health_status["checks"]["vector_store"] = False
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/metrics")
async def metrics_endpoint():
    """Metrics endpoint (simplified - no Prometheus)."""
    return {"status": "metrics disabled", "message": "Prometheus dependencies removed"}


@app.get("/tracing/status")
async def tracing_status():
    """Get tracing system status and statistics."""
    return {
        "tracing_enabled": False,
        "service_name": "alleato-rag-agent",
        "message": "Tracing dependencies removed for simplified deployment",
        "endpoints": {
            "health": "/health"
        }
    }


@app.get("/debug/env")
async def debug_environment():
    """Debug endpoint to check environment variables."""
    import os
    
    # Check critical environment variables
    env_vars = {
        "DATABASE_URL": os.getenv("DATABASE_URL", "NOT_SET")[:50] + "..." if os.getenv("DATABASE_URL") else "NOT_SET",
        "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT_SET", 
        "LLM_API_KEY": "SET" if os.getenv("LLM_API_KEY") else "NOT_SET",
        "LLM_MODEL": os.getenv("LLM_MODEL", "NOT_SET"),
        "LLM_BASE_URL": os.getenv("LLM_BASE_URL", "NOT_SET"),
        "PORT": os.getenv("PORT", "NOT_SET"),
        "RENDER": os.getenv("RENDER", "NOT_SET"),
        "PYTHON_VERSION": os.getenv("PYTHON_VERSION", "NOT_SET")
    }
    
    # Check settings loading
    try:
        from shared.utils.config import load_settings
        settings = load_settings()
        settings_info = {
            "database_url_from_settings": settings.database_url[:50] + "..." if settings.database_url else "EMPTY",
            "llm_api_key_from_settings": "SET" if settings.llm_api_key else "EMPTY", 
            "llm_model_from_settings": settings.llm_model
        }
    except Exception as e:
        settings_info = {"error": str(e)}
    
    return {
        "environment_variables": env_vars,
        "settings": settings_info,
        "all_env_count": len(os.environ)
    }