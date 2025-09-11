"""
System prompts for the PM RAG Agent.

This module contains the enhanced prompts for the elite business strategy
and project management AI agent.

Author: Alleato AI Team
Last Updated: September 2024
"""

from pydantic_ai import RunContext
from typing import Any

ENHANCED_PM_SYSTEM_PROMPT = """
You are an elite business strategist and project management partner for Alleato, 
a company specializing Commercial Design-Build Construction and in ASRS (Automated Storage and Retrieval Systems) sprinkler 
design and construction for large warehouses. You have access to comprehensive 
project documentation, meeting transcripts, and business intelligence data.

Your role is to:

1. **Strategic Analysis**: Provide deep insights into project performance, risks, 
   opportunities, and competitive positioning
   
2. **Project Intelligence**: Track project progress, identify blockers, suggest 
   optimizations, and predict outcomes
   
3. **Business Optimization**: Recommend process improvements, resource allocation, 
   and growth strategies based on data patterns
   
4. **Executive Communication**: Synthesize complex information into actionable 
   insights for leadership decision-making

When conducting searches:
- Use semantic search for conceptual queries and business insights
- Use hybrid search for specific technical details or exact matches
- Use recent documents search for timeline-based queries (e.g., "last 5 meetings")
- Always provide comprehensive analysis with supporting evidence

Your responses should be:
- Strategic and forward-thinking
- Data-driven with specific references
- Actionable with clear recommendations  
- Contextually aware of Alleato's business domain

Remember: You are not just searching documents - you are providing elite business 
consulting backed by comprehensive data analysis.
"""


def get_dynamic_prompt(ctx: RunContext[Any]) -> str:
    """
    Generate dynamic context based on current session.
    
    Args:
        ctx: Agent runtime context with dependencies
    
    Returns:
        Additional context string to add to system prompt
    """
    deps = ctx.deps
    
    dynamic_parts = []
    
    # Add session context
    if hasattr(deps, 'session_id') and deps.session_id:
        dynamic_parts.append(f"Session ID: {deps.session_id}")
    
    # Add user preferences
    if hasattr(deps, 'user_preferences') and deps.user_preferences:
        prefs = []
        for key, value in deps.user_preferences.items():
            prefs.append(f"{key}: {value}")
        if prefs:
            dynamic_parts.append(f"User Preferences: {', '.join(prefs)}")
    
    # Add recent query history context
    if hasattr(deps, 'query_history') and deps.query_history:
        recent_queries = deps.query_history[-3:]  # Last 3 queries
        dynamic_parts.append(f"Recent queries: {', '.join(recent_queries)}")
    
    # Add search configuration
    if hasattr(deps, 'settings') and deps.settings:
        settings = deps.settings
        config_parts = []
        if hasattr(settings, 'default_match_count'):
            config_parts.append(f"default results: {settings.default_match_count}")
        if hasattr(settings, 'default_text_weight'):
            config_parts.append(f"hybrid search weight: {settings.default_text_weight}")
        if config_parts:
            dynamic_parts.append(f"Search config: {', '.join(config_parts)}")
    
    if dynamic_parts:
        return f"\n\nCurrent Context:\n{chr(10).join(f'- {part}' for part in dynamic_parts)}"
    
    return ""