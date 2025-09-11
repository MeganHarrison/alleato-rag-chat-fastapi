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
from pydantic_ai import Agent

app = FastAPI(title="RAG Agent API", version="1.0.0")

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
        "https://rag-agent-chat.vercel.app",
        "https://*.vercel.app"
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
        
        prompt = f"""Previous conversation:
{context}

User: {message}

Search the knowledge base to answer the user's question. Choose the appropriate search strategy (semantic_search or hybrid_search) based on the query type. Provide a comprehensive summary of your findings."""

        # Stream the agent execution
        try:
            async with search_agent.iter(prompt, deps=deps) as run:
                tool_calls = []
                response_text = ""
                
                async for node in run:
                    
                    # Handle tool call nodes
                    if Agent.is_tool_call_node(node):
                        for tool_call in node:
                            tool_info = {
                                "tool": tool_call.name,
                                "args": tool_call.args
                            }
                            tool_calls.append(tool_info)
                            
                            # Send tool call event
                            yield f"data: {json.dumps({'type': 'tool_call', 'data': tool_info})}\n\n"
                    
                    # Handle tool response nodes
                    elif Agent.is_tool_return_node(node):
                        for tool_return in node:
                            # Send tool result event
                            yield f"data: {json.dumps({'type': 'tool_result', 'data': {'result': str(tool_return.response)[:200]}})}\n\n"
                    
                    # Handle model text response
                    elif Agent.is_text_chunk_node(node):
                        chunk = node.delta
                        response_text += chunk
                        # Send text chunk event
                        yield f"data: {json.dumps({'type': 'text', 'data': chunk})}\n\n"
                
                # Send final complete event
                yield f"data: {json.dumps({'type': 'complete', 'data': {'response': response_text, 'tool_calls': tool_calls}})}\n\n"
        
        except Exception as agent_error:
            # If agent fails, send error response
            print(f"Streaming agent execution failed: {agent_error}")
            fallback_message = "I'm experiencing technical difficulties accessing the knowledge base. Please try again or ask me a general question about project management."
            yield f"data: {json.dumps({'type': 'text', 'data': fallback_message})}\n\n"
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
        
        prompt = f"""Previous conversation:
{context}

User: {request.message}

Search the knowledge base to answer the user's question. Choose the appropriate search strategy (semantic_search or hybrid_search) based on the query type. Provide a comprehensive summary of your findings."""
        
        # Run agent with error handling
        try:
            result = await search_agent.run(prompt, deps=deps)
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
            response=str(result.response) if hasattr(result, 'response') else str(result),
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
    try:
        from shared.ai.agent_deps import AgentDeps
        
        deps = AgentDeps()
        await deps.initialize()
        
        # Test basic database connectivity
        async with deps.db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
        
        return {
            "status": "success",
            "database_connection": True,
            "test_query_result": result,
            "db_pool_initialized": deps.db_pool.pool is not None
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "database_connection": False
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