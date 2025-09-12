"""Web search tools for real-time information lookup."""

from typing import Optional, List, Dict, Any
from pydantic_ai import RunContext
from pydantic import BaseModel, Field
import httpx
import asyncio
import os
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
        # Get Brave Search API key
        brave_api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if not brave_api_key:
            return [WebSearchResult(
                title="Search Configuration Error",
                url="",
                snippet="Brave Search API key not configured. Unable to perform web search.",
                source="system"
            )]
        
        async with httpx.AsyncClient() as client:
            
            # Brave Search API
            search_url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": brave_api_key
            }
            params = {
                "q": query,
                "count": max_results,
                "text_decorations": "0",
                "search_lang": "en",
                "country": "US",
                "safesearch": "moderate",
                "freshness": "pw"  # Past week for fresh results
            }
            
            response = await client.get(search_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                return [WebSearchResult(
                    title="Search Error",
                    url="",
                    snippet=f"Brave Search API failed with status {response.status_code}. {response.text[:200]}",
                    source="system"
                )]
            
            data = response.json()
            results = []
            
            # Extract web results
            web_results = data.get("web", {}).get("results", [])
            
            for result in web_results[:max_results]:
                results.append(WebSearchResult(
                    title=result.get("title", "No title")[:150],
                    url=result.get("url", ""),
                    snippet=result.get("description", "No description available")[:400],
                    source="Brave Search"
                ))
            
            # If no results, provide helpful fallback
            if not results:
                results.append(WebSearchResult(
                    title="No current web results",
                    url="",
                    snippet=f"No web results found for '{query}'. The information may be available by checking specific agency websites or local government portals.",
                    source="system"
                ))
            
            return results
            
    except asyncio.TimeoutError:
        return [WebSearchResult(
            title="Search Timeout",
            url="",
            snippet="Web search timed out. This could be due to network issues or high API load.",
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