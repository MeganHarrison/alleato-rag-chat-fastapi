#!/bin/bash

# Interactive terminal chat with the RAG API
# Usage: ./chat.sh

echo "🚀 Alleato RAG Chat Terminal"
echo "============================="
echo "Type 'exit' or 'quit' to stop"
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server not running. Start it with: python -m uvicorn main:app --reload"
    exit 1
fi

# Initialize conversation
conversation=[]
session_id=$(uuidgen 2>/dev/null || echo "terminal-$(date +%s)")

while true; do
    # Get user input
    echo -n "You: "
    read -r user_input
    
    # Check for exit commands
    if [[ "$user_input" == "exit" || "$user_input" == "quit" ]]; then
        echo "👋 Goodbye!"
        break
    fi
    
    # Skip empty input
    if [[ -z "$user_input" ]]; then
        continue
    fi
    
    echo "🤖 AI: "
    
    # Make API call and display response
    response=$(curl -s -X POST "http://localhost:8000/chat" \
        -H "Content-Type: application/json" \
        -d "{
            \"message\": \"$user_input\",
            \"conversation_history\": $conversation,
            \"session_id\": \"$session_id\"
        }" | jq -r '.response' 2>/dev/null)
    
    if [[ $? -eq 0 && "$response" != "null" ]]; then
        echo "$response" | sed 's/AgentRunResult(data='"'"'//' | sed 's/'"'"')$//'
    else
        echo "❌ Error getting response from API"
    fi
    
    echo ""
done