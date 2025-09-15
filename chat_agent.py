"""Simple chat agent that actually works."""

import openai
import os
from search import search_recent_documents, search_documents_by_text, search_meetings
from prompts import CONVERSATIONAL_PM_SYSTEM_PROMPT
from typing import List, Dict, Any

class ChatAgent:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        )
        self.model = os.getenv("LLM_MODEL", "gpt-5")
    
    async def get_enhanced_context(self, message: str) -> str:
        """Get comprehensive context using multiple search strategies."""
        print(f"🔍 Starting enhanced context search for: {message[:50]}...")
        context_parts = []
        
        try:
            # 1. Recent documents for timeline awareness (simplified)
            print("📅 Fetching recent documents...")
            recent_docs = await search_recent_documents(3)  # Reduced from 5
            if recent_docs:
                context_parts.append("📅 RECENT ACTIVITY:")
                for doc in recent_docs[:2]:  # Only top 2
                    title = doc.get('title', 'No title')[:40]  # Shorter
                    content = doc.get('content', '')[:100]  # Shorter
                    source = doc.get('source', 'Unknown')
                    context_parts.append(f"• {title} ({source})")
                    if content:
                        context_parts.append(f"  {content}...")
            
            # 2. Quick text search (simplified)
            print("🔍 Performing text search...")
            text_docs = await search_documents_by_text(message, 2)  # Reduced count
            if text_docs:
                context_parts.append("\n🔍 RELEVANT DOCUMENTS:")
                for doc in text_docs:
                    title = doc.get('title', 'No title')[:40]
                    content = doc.get('content', '')[:100]
                    context_parts.append(f"• {title}")
                    if content:
                        context_parts.append(f"  {content}...")
            
            result = "\n".join(context_parts) if context_parts else "No relevant context found in current database."
            print(f"✅ Context search completed ({len(result)} chars)")
            return result
            
        except Exception as e:
            print(f"❌ Error in enhanced context: {str(e)}")
            return f"Context search error: {str(e)}"
    
    # Keep the old method name for backward compatibility
    async def get_context(self, message: str) -> str:
        """Backward compatibility wrapper."""
        return await self.get_enhanced_context(message)
    
    async def analyze_project_status(self, project_name: str = None) -> str:
        """Quick project status analysis."""
        try:
            if project_name:
                context_msg = f"What's the current status and key risks for the {project_name} project?"
            else:
                context_msg = "Give me a strategic overview of current project status and top priorities."
            
            return await self.chat(context_msg, [])
        except Exception as e:
            return f"Analysis error: {str(e)}"

    async def meeting_summary(self) -> str:
        """Quick meeting summary and action items."""
        return await self.chat("Summarize recent meetings and highlight key decisions and action items.", [])
    
    async def chat(self, message: str, conversation_history: List[Dict] = None) -> str:
        """Process chat message and return response."""
        try:
            # Get context from database
            context = await self.get_context(message)
            
            # Build enhanced system prompt with context
            system_content = f"""{CONVERSATIONAL_PM_SYSTEM_PROMPT}

CURRENT DATABASE CONTEXT:
{context}

ANALYSIS INSTRUCTIONS:
- Reference specific documents and dates when making points
- Identify patterns and risks based on the provided data
- Provide actionable next steps grounded in the context
- Use your veteran PM personality to cut through noise and focus on what matters
- If asked about status, pull from recent documents and meetings
- When discussing projects, reference actual data from the context above
"""

            messages = [{"role": "system", "content": system_content}]
            
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