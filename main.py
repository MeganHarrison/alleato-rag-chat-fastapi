"""Brand new clean FastAPI app that actually works."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

from chat_agent import agent
from database import db

app = FastAPI(title="Clean RAG API", version="2.0.0")

# CORS
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

# Models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

@app.get("/")
async def root():
    return {"status": "working", "message": "Clean RAG API v2.0"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "testing...",
        "llm": "configured"
    }

@app.get("/test-database")
async def test_database():
    """Test database connection."""
    try:
        # Test connection
        await db.connect()
        
        # Get counts
        docs = await db.execute_query("SELECT COUNT(*) as count FROM documents")
        chunks = await db.execute_query("SELECT COUNT(*) as count FROM chunks")
        
        return {
            "status": "success",
            "documents": docs[0]["count"] if docs else 0,
            "chunks": chunks[0]["count"] if chunks else 0,
            "message": "Database connection working"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Database connection failed"
        }

@app.get("/test-search")
async def test_search():
    """Test search functionality."""
    try:
        from search import search_recent_documents
        
        docs = await search_recent_documents(3)
        
        return {
            "status": "success",
            "documents_found": len(docs),
            "sample_titles": [doc.get('title', 'No title')[:50] for doc in docs[:2]],
            "message": "Search working"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Search failed"
        }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint."""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Convert Pydantic models to dicts
        history = []
        if request.conversation_history:
            history = [{"role": msg.role, "content": msg.content} for msg in request.conversation_history]
        
        # Get response
        response = await agent.chat(request.message, history)
        
        return ChatResponse(
            response=response,
            session_id=session_id
        )
        
    except Exception as e:
        return ChatResponse(
            response=f"Error: {str(e)}",
            session_id=request.session_id or str(uuid.uuid4())
        )