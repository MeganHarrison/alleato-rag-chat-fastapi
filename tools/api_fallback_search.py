"""
Fallback search tools that use external RAG APIs when direct database connection fails.
"""

import aiohttp
import os
from typing import List, Dict, Any, Optional
from pydantic_ai import RunContext
from shared.ai.agent_deps import AgentDeps


async def fallback_semantic_search(
    ctx: RunContext[AgentDeps],
    query: str,
    match_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fallback semantic search using external RAG API.
    """
    try:
        pm_rag_url = os.getenv('RAILWAY_PM_RAG', 'https://rag-agent-api-production.up.railway.app')
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{pm_rag_url}/search",
                json={
                    "query": query,
                    "limit": match_count or 10,
                    "search_type": "semantic"
                },
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Transform external API response to match expected format
                    return [
                        {
                            'content': item.get('content', ''),
                            'similarity': item.get('similarity', 0.0),
                            'metadata': item.get('metadata', {}),
                            'document_title': item.get('document_title', ''),
                            'document_source': item.get('document_source', 'External API')
                        }
                        for item in data.get('results', [])
                    ]
                else:
                    print(f"External RAG API error: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"Fallback semantic search failed: {e}")
        return []


async def fallback_recent_documents(
    ctx: RunContext[AgentDeps],
    limit: int = 5,
    document_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fallback to get recent documents using external API.
    """
    try:
        pm_rag_url = os.getenv('RAILWAY_PM_RAG', 'https://rag-agent-api-production.up.railway.app')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{pm_rag_url}/documents/recent",
                params={
                    "limit": limit,
                    "type": document_type
                },
                timeout=30
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('documents', [])
                else:
                    print(f"External documents API error: {response.status}")
                    return []
                    
    except Exception as e:
        print(f"Fallback recent documents failed: {e}")
        return []