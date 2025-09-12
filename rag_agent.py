"""
PM RAG Agent - Elite Business Strategy & Project Management System

This is the main agent for Alleato's PM RAG system, serving as an elite 
business strategist and project management partner.

Author: Alleato AI Team  
Last Updated: September 2024
"""

from pydantic_ai import Agent

from shared.ai.providers import get_llm_model
from shared.ai.prompts import CONVERSATIONAL_PM_SYSTEM_PROMPT
from tools.search_tools import semantic_search, hybrid_search, get_recent_documents
from tools.web_search_tools import web_search, search_construction_info
from tools.financial_analysis_tools import calculate_budget_variance, calculate_timeline_cost_impact, project_final_cost

# Import dependencies
from shared.ai.agent_deps import AgentDeps

# Initialize the conversational PM agent with veteran personality
search_agent = Agent(
    get_llm_model(),
    deps_type=AgentDeps,
    system_prompt=CONVERSATIONAL_PM_SYSTEM_PROMPT
)

# Dynamic context removed - using static conversational prompt for consistent personality

# Register enhanced search tools
search_agent.tool(semantic_search)
search_agent.tool(hybrid_search)
search_agent.tool(get_recent_documents)

# Register web search tools for real-time information
search_agent.tool(web_search)
search_agent.tool(search_construction_info)

# Register financial analysis tools for budget and cost management
search_agent.tool(calculate_budget_variance)
search_agent.tool(calculate_timeline_cost_impact)
search_agent.tool(project_final_cost)