#!/bin/bash

# Production startup script for Alleato RAG Agent
# This runs the system like a live production service

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PORT=8000
HOST="0.0.0.0"
WORKERS=4

echo -e "${GREEN}🚀 Starting Alleato RAG Agent - Production Mode${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""

# Check if .env exists
if [[ ! -f .env ]]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating sample...${NC}"
    cat > .env << EOF
# Alleato RAG Agent Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
OPENAI_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small
EOF
    echo -e "${RED}❌ Please configure your .env file with proper API keys${NC}"
    exit 1
fi

# Check dependencies
echo -e "${BLUE}📦 Checking dependencies...${NC}"
if ! python -c "import fastapi, uvicorn, openai, pydantic_ai" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Check if port is available
if lsof -i :$PORT >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PORT is already in use. Stopping existing process...${NC}"
    pkill -f "uvicorn.*main:app" || true
    sleep 2
fi

# Start the server
echo -e "${GREEN}🎯 Starting server on http://$HOST:$PORT${NC}"
echo -e "${BLUE}📊 Workers: $WORKERS${NC}"
echo -e "${BLUE}🔄 Auto-reload: enabled${NC}"
echo ""
echo -e "${YELLOW}💡 To chat, open another terminal and run: ./chat_live.sh${NC}"
echo -e "${YELLOW}📱 Or use the API directly at: http://localhost:$PORT${NC}"
echo -e "${YELLOW}🏥 Health check: http://localhost:$PORT/health${NC}"
echo ""
echo -e "${GREEN}Press Ctrl+C to stop the server${NC}"
echo ""

# Start with production settings but keep reload for development
python -m uvicorn main:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-dir . \
    --log-level info \
    --access-log