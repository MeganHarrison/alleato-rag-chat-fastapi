#!/bin/bash

# Demo script showing live production usage
# This simulates how executives would use the system

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to ask question and show response nicely
ask_demo() {
    local question="$1"
    echo -e "${YELLOW}🏢 Executive Question:${NC} $question"
    echo ""
    echo -e "${BLUE}🤖 AI Response:${NC}"
    curl -s -X POST "http://localhost:8000/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$question\"}" \
        | jq -r '.response' | sed 's/^AgentRunResult(data='"'"'//' | sed 's/'"'"')$//' | fold -w 80 -s
    echo ""
    echo -e "${GREEN}─────────────────────────────────────────────────────────────────────────${NC}"
    echo ""
    sleep 2
}

echo -e "${GREEN}🚀 ALLEATO RAG AGENT - LIVE PRODUCTION DEMO${NC}"
echo -e "${GREEN}===========================================${NC}"
echo ""
echo -e "${BLUE}Demonstrating real-time business intelligence queries...${NC}"
echo ""

# Demo questions
ask_demo "What urgent issues need my attention as CEO today?"
ask_demo "What is our current financial health and cash flow situation?"
ask_demo "Which projects are behind schedule or at risk?"
ask_demo "How are our teams performing and do we have resource bottlenecks?"

echo -e "${GREEN}🎯 Demo Complete! The system is ready for live production use.${NC}"
echo ""
echo -e "${YELLOW}To start your own live chat session, run:${NC}"
echo -e "${BLUE}  ./chat_live.sh${NC}"