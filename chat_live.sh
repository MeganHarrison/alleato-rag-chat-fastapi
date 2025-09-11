#!/bin/bash

# Live Interactive Chat with Alleato RAG Agent
# Production-ready terminal interface

set -e

# Colors for better UX
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8000"
SESSION_ID="live-$(date +%s)"

# Function to check if server is running
check_server() {
    if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
        echo -e "${RED}❌ Server not running!${NC}"
        echo -e "${YELLOW}Start the server first:${NC}"
        echo "  python -m uvicorn main:app --host 0.0.0.0 --port 8000"
        exit 1
    fi
}

# Function to make API call
ask_question() {
    local question="$1"
    local response
    
    response=$(curl -s -X POST "${API_URL}/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$question\", \"session_id\": \"$SESSION_ID\"}" \
        | jq -r '.response' 2>/dev/null)
    
    if [[ $? -eq 0 && "$response" != "null" && "$response" != "" ]]; then
        # Clean up the response
        echo "$response" | sed 's/^AgentRunResult(data='"'"'//' | sed 's/'"'"')$//' | fold -w 80 -s
    else
        echo -e "${RED}❌ Error getting response from API${NC}"
    fi
}

# Function to stream response
stream_question() {
    local question="$1"
    
    echo -e "${BLUE}🤖 AI Assistant:${NC}"
    curl -X POST "${API_URL}/chat/stream" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$question\", \"session_id\": \"$SESSION_ID\"}" \
        --no-buffer 2>/dev/null | while IFS= read -r line; do
            if [[ "$line" =~ data:\ (.*) ]]; then
                local data="${BASH_REMATCH[1]}"
                local char=$(echo "$data" | jq -r '.data' 2>/dev/null)
                if [[ "$char" != "null" && "$char" != "" ]]; then
                    printf "%s" "$char"
                fi
            fi
        done
    echo -e "\n"
}

# Main chat loop
main() {
    clear
    echo -e "${GREEN}🚀 Alleato RAG Agent - Live Chat${NC}"
    echo -e "${GREEN}=================================${NC}"
    echo -e "${YELLOW}Your AI business intelligence assistant for project management${NC}"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo "  Type your question and press Enter"
    echo "  'stream <question>' for streaming response"
    echo "  'help' for example questions"
    echo "  'quit' or 'exit' to stop"
    echo ""
    
    # Check server status
    check_server
    echo -e "${GREEN}✅ Connected to API${NC}"
    echo ""
    
    while true; do
        echo -e -n "${YELLOW}You: ${NC}"
        read -r user_input
        
        # Handle exit commands
        if [[ "$user_input" == "quit" || "$user_input" == "exit" ]]; then
            echo -e "${GREEN}👋 Thanks for using Alleato RAG Agent!${NC}"
            break
        fi
        
        # Skip empty input
        if [[ -z "$user_input" ]]; then
            continue
        fi
        
        # Handle help command
        if [[ "$user_input" == "help" ]]; then
            echo -e "${BLUE}📋 Example Questions:${NC}"
            echo "  • What projects need my attention today?"
            echo "  • What are our current financial risks?"
            echo "  • How are our teams performing?"
            echo "  • Tell me about the Goodwill project status"
            echo "  • What urgent issues should I address?"
            echo "  • stream What's our cash flow situation?"
            echo ""
            continue
        fi
        
        # Handle streaming requests
        if [[ "$user_input" =~ ^stream[[:space:]](.+) ]]; then
            local question="${BASH_REMATCH[1]}"
            stream_question "$question"
            continue
        fi
        
        # Regular question
        echo -e "${BLUE}🤖 AI Assistant:${NC}"
        ask_question "$user_input"
        echo ""
    done
}

# Run the chat
main "$@"