"""Web search tools for real-time information lookup."""

from typing import Optional, List, Dict, Any
from pydantic_ai import RunContext
from pydantic import BaseModel, Field
import httpx
import asyncio
from shared.ai.agent_deps import AgentDeps

try:
    from shared.monitoring.tracing import get_tracer
    ADVANCED_TRACING = True
except ImportError:
    from shared.monitoring.simple_tracing import get_simple_tracer as get_tracer
    ADVANCED_TRACING = False


class WebSearchResult(BaseModel):
    """Model for web search results."""
    title: str
    url: str
    snippet: str
    source: str


@get_tracer().trace_search_operation("web")
async def web_search(
    ctx: RunContext[AgentDeps],
    query: str,
    max_results: Optional[int] = 5
) -> List[WebSearchResult]:
    """
    Search the web for current information relevant to construction projects.
    
    Use this for:
    - Fire marshal office delays and contact info
    - Permit status and requirements  
    - Vendor/supplier current status
    - Weather forecasts affecting construction
    - Industry news and regulatory changes
    
    Args:
        ctx: Agent runtime context with dependencies
        query: Search query (e.g. "fire marshal office delays Chicago")
        max_results: Number of results to return (default: 5)
    
    Returns:
        List of web search results with titles, URLs, and snippets
    """
    try:
        # Use DuckDuckGo Instant Answer API (no API key required)
        async with httpx.AsyncClient() as client:
            
            # DuckDuckGo search
            search_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = await client.get(search_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return [WebSearchResult(
                    title="Search Error",
                    url="",
                    snippet=f"Web search failed with status {response.status_code}",
                    source="system"
                )]
            
            data = response.json()
            results = []
            
            # Extract instant answer if available
            if data.get("Abstract"):
                results.append(WebSearchResult(
                    title=data.get("AbstractText", "Instant Answer")[:100],
                    url=data.get("AbstractURL", ""),
                    snippet=data.get("Abstract", "")[:300],
                    source=data.get("AbstractSource", "DuckDuckGo")
                ))
            
            # Extract related topics
            for topic in data.get("RelatedTopics", [])[:max_results-1]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(WebSearchResult(
                        title=topic.get("Text", "")[:100],
                        url=topic.get("FirstURL", ""),
                        snippet=topic.get("Text", "")[:300],
                        source="DuckDuckGo"
                    ))
            
            # If no results, provide helpful fallback
            if not results:
                results.append(WebSearchResult(
                    title="No current web results",
                    url="",
                    snippet=f"No immediate web results for '{query}'. Consider checking specific agency websites or local government portals for permit/inspection delays.",
                    source="system"
                ))
            
            return results[:max_results]
            
    except asyncio.TimeoutError:
        return [WebSearchResult(
            title="Search Timeout",
            url="",
            snippet="Web search timed out. The information may be available by checking specific government or agency websites directly.",
            source="system"
        )]
        
    except Exception as e:
        return [WebSearchResult(
            title="Search Error",
            url="",
            snippet=f"Web search encountered an error: {str(e)}. Try rephrasing the query or checking specific websites directly.",
            source="system"
        )]


@get_tracer().trace_search_operation("construction_web")
async def search_construction_info(
    ctx: RunContext[AgentDeps], 
    topic: str,
    location: Optional[str] = None
) -> List[WebSearchResult]:
    """
    Search for construction-specific information with veteran PM context.
    
    Args:
        ctx: Agent runtime context
        topic: What to search for (permits, inspections, weather, etc.)
        location: Optional location context (e.g. "Chicago", "Cook County")
    
    Returns:
        Construction-focused search results
    """
    # Build construction-focused query
    query_parts = [topic]
    if location:
        query_parts.append(location)
    
    # Add construction context
    if "permit" in topic.lower():
        query_parts.append("building department delays")
    elif "fire" in topic.lower() and "marshal" in topic.lower():
        query_parts.append("inspection delays timeline")
    elif "weather" in topic.lower():
        query_parts.append("construction forecast")
    
    search_query = " ".join(query_parts)
    return await web_search(ctx, search_query, max_results=5)