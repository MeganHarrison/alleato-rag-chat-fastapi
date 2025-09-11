"""
PM RAG Agent - Elite Business Strategy & Project Management System

This is the main agent for Alleato's PM RAG system, serving as an elite 
business strategist and project management partner.

Author: Alleato AI Team  
Last Updated: September 2024
"""

from pydantic_ai import Agent, RunContext
from typing import Any
from types import SimpleNamespace

from shared.ai.providers import get_llm_model
from shared.utils.db_utils import db_pool
from shared.ai.prompts import ENHANCED_PM_SYSTEM_PROMPT, get_dynamic_prompt
from tools.search_tools import semantic_search, hybrid_search, get_recent_documents

# Import dependencies
from shared.ai.agent_deps import AgentDeps

# Initialize the elite PM agent with enhanced system prompt  
search_agent = Agent(
    get_llm_model(),
    deps_type=AgentDeps,
    system_prompt=ENHANCED_PM_SYSTEM_PROMPT
)

# Add dynamic context to system prompt
@search_agent.system_prompt
async def add_dynamic_context(ctx: RunContext[AgentDeps]) -> str:
    """Add dynamic context based on current session."""
    return get_dynamic_prompt(ctx)

# Register enhanced search tools
search_agent.tool(semantic_search)
search_agent.tool(hybrid_search)
search_agent.tool(get_recent_documents)