#!/bin/bash

# Chat utility functions
# Source this file: source chat_functions.sh

# Simple chat function
chat() {
    if [[ -z "$1" ]]; then
        echo "Usage: chat 'your question here'"
        return 1
    fi
    
    curl -s -X POST "http://localhost:8000/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$1\"}" \
        | jq -r '.response' \
        | sed 's/AgentRunResult(data='"'"'//' \
        | sed 's/'"'"')$//'
}

# Streaming chat function
chat_stream() {
    if [[ -z "$1" ]]; then
        echo "Usage: chat_stream 'your question here'"
        return 1
    fi
    
    curl -X POST "http://localhost:8000/chat/stream" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$1\"}" \
        --no-buffer | while read -r line; do
            if [[ "$line" =~ data:\ (.*) ]]; then
                echo "${BASH_REMATCH[1]}" | jq -r '.data' 2>/dev/null | tr -d '\n'
            fi
        done
    echo ""
}

# Health check function
chat_health() {
    curl -s "http://localhost:8000/health" | jq .
}

# Available commands help
chat_help() {
    echo "Available chat commands:"
    echo "  chat 'question'        - Ask a question"
    echo "  chat_stream 'question' - Stream response"
    echo "  chat_health            - Check API health"
    echo "  chat_help              - Show this help"
    echo ""
    echo "Examples:"
    echo "  chat 'What are the current project risks?'"
    echo "  chat_stream 'Tell me about the last meeting'"
}