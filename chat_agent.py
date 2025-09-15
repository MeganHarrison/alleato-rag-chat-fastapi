"""Simple chat agent that actually works."""

import openai
import os
from search import search_recent_documents, search_documents_by_text, search_meetings
from typing import List, Dict, Any

class ChatAgent:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        )
        self.model = os.getenv("LLM_MODEL", "gpt-5")
    
    async def get_context(self, message: str) -> str:
        """Get relevant context from database."""
        context_parts = []
        
        # Get recent documents
        recent_docs = await search_recent_documents(5)
        if recent_docs:
            context_parts.append("Recent Documents:")
            for doc in recent_docs[:3]:
                title = doc.get('title', 'No title')[:50]
                content = doc.get('content', '')[:200]
                context_parts.append(f"- {title}: {content}...")
        
        # Search for relevant content
        if any(keyword in message.lower() for keyword in ['meeting', 'project', 'status']):
            relevant_docs = await search_meetings(message, 3)
            if relevant_docs:
                context_parts.append("\nRelevant Meetings:")
                for doc in relevant_docs:
                    title = doc.get('title', 'No title')[:50]
                    content = doc.get('content', '')[:200]
                    context_parts.append(f"- {title}: {content}...")
        
        return "\n".join(context_parts) if context_parts else "No relevant documents found."
    
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Process chat message and return response."""
        try:
            # Get context from database
            context = await self.get_context(message)
            
            # Build messages
            messages = [
                {
                    "role": "system",
                    "content": f"""You are an expert project manager and construction professional. 
                    
Use this context from the database:
{context}

Respond in a direct, professional tone. Focus on actionable information and specific details from the context provided."""
                }
            ]
            
            # Add conversation history
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
            
            # Add current message
            messages.append({
                "role": "user", 
                "content": message
            })
            
            # Get response from LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

# Global chat agent
agent = ChatAgent()