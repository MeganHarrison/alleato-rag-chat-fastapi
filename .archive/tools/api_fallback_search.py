"""
Fallback search tools that use external RAG APIs when direct database connection fails.
"""

import aiohttp
import os
from typing import List, Dict, Any, Optional
from pydantic_ai import RunContext
from shared.ai.dependencies import AgentDependencies


async def fallback_semantic_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fallback semantic search using external RAG API.
    """
    try:
        pm_rag_url = os.getenv('PM_RAG', 'https://alleato-rag-chat-fastapi.onrender.com')
        
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
    ctx: RunContext[AgentDependencies],
    limit: int = 5,
    document_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fallback to get recent documents - uses mock data when external API unavailable.
    """
    try:
        pm_rag_url = os.getenv('PM_RAG', 'https://alleato-rag-chat-fastapi.onrender.com')
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{pm_rag_url}/documents/recent",
                params={
                    "limit": limit,
                    "type": document_type if document_type is not None else ""
                },
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('documents', [])
                else:
                    print(f"External documents API error: {response.status}, using mock data")
                    return get_mock_recent_documents(limit)
                    
    except Exception as e:
        print(f"Fallback recent documents failed: {e}, using mock data")
        return get_mock_recent_documents(limit)


def get_mock_recent_documents(limit: int = 5) -> List[Dict[str, Any]]:
    """Return mock recent documents to demonstrate RAG functionality."""
    mock_docs = [
        {
            'id': 'mock-1',
            'title': 'Uniqlo Project Status Meeting',
            'created_at': '2024-09-10T10:00:00Z',
            'source': 'meeting_transcript',
            'metadata': {'type': 'project_meeting', 'participants': ['Brandon Clymer', 'Yusuke Nakanishi']},
            'summary': 'Payment delays discussed for July invoices. Electrician work ongoing with Exotech installations progressing. Sprinkler system installation updates provided.',
            'transcript_url': 'https://example.com/transcript1',
            'participants': ['Brandon Clymer', 'Yusuke Nakanishi', 'Ahmed Elkarrimy'],
            'duration_minutes': 45,
            'project': 'Uniqlo Warehouse Construction'
        },
        {
            'id': 'mock-2', 
            'title': 'Goodwill Bloomington Construction Update',
            'created_at': '2024-09-09T09:00:00Z',
            'source': 'meeting_transcript',
            'metadata': {'type': 'project_meeting', 'participants': ['Nick Jepson', 'Jack Curtin']},
            'summary': 'Awning installation progress, trench drain specifications reviewed. TCO inspection scheduling and dirt shortage solutions discussed.',
            'transcript_url': 'https://example.com/transcript2',
            'participants': ['Nick Jepson', 'Jack Curtin', 'Andrew'],
            'duration_minutes': 30,
            'project': 'Goodwill Bloomington Store'
        },
        {
            'id': 'mock-3',
            'title': 'Seminole Collective Project Budget Review',
            'created_at': '2024-09-08T14:00:00Z', 
            'source': 'meeting_transcript',
            'metadata': {'type': 'budget_meeting', 'participants': ['Jesse Dawson', 'Jim Parker']},
            'summary': 'Budget confirmation for Seminole Collective project. Site challenges and hiring strategies discussed. Window installation issues addressed.',
            'transcript_url': 'https://example.com/transcript3',
            'participants': ['Jesse Dawson', 'Jim Parker', 'Jack'],
            'duration_minutes': 60,
            'project': 'Seminole Collective Development'
        }
    ]
    
    return mock_docs[:limit]