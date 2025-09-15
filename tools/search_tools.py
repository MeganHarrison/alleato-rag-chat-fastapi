"""
Advanced Search Tools for PM RAG Agent

This module provides semantic, hybrid, and document search capabilities
for the Alleato PM RAG system.

Author: Alleato AI Team
Last Updated: September 2024
"""

import asyncio
from typing import List, Dict, Any, Optional
from pydantic_ai import RunContext

# Import database and search modules
from database import db
from search import search_recent_documents as _search_recent_documents
from search import search_documents_by_text as _search_documents_by_text
from search import search_meetings as _search_meetings

# TODO: Add vector search capabilities when embeddings are implemented
# from vector_search import semantic_similarity_search


async def semantic_search(
    ctx: RunContext, 
    query: str, 
    match_count: int = 5,
    relevance_threshold: float = 0.7
) -> str:
    """
    Perform semantic search using vector embeddings.
    
    Args:
        ctx: Agent runtime context
        query: Search query for semantic matching
        match_count: Number of results to return
        relevance_threshold: Minimum relevance score
        
    Returns:
        Formatted search results with context
    """
    try:
        # For now, fall back to text search until vector embeddings are implemented
        # TODO: Replace with actual vector similarity search
        results = await _search_documents_by_text(query, match_count)
        
        if not results:
            return f"No semantic matches found for: {query}"
        
        formatted_results = []
        formatted_results.append(f"🔍 SEMANTIC SEARCH RESULTS for '{query}':")
        formatted_results.append("=" * 50)
        
        for i, doc in enumerate(results, 1):
            title = doc.get('title', 'No title')[:60]
            content = doc.get('content', '')[:200]
            source = doc.get('source', 'Unknown')
            created_at = doc.get('created_at', 'Unknown date')
            
            formatted_results.append(f"\n{i}. {title}")
            formatted_results.append(f"   Source: {source}")
            formatted_results.append(f"   Date: {created_at}")
            formatted_results.append(f"   Content: {content}...")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Semantic search failed: {str(e)}"


async def hybrid_search(
    ctx: RunContext, 
    query: str, 
    match_count: int = 5,
    text_weight: float = 0.5,
    semantic_weight: float = 0.5
) -> str:
    """
    Perform hybrid search combining text and semantic matching.
    
    Args:
        ctx: Agent runtime context
        query: Search query
        match_count: Number of results to return
        text_weight: Weight for text search results (0.0-1.0)
        semantic_weight: Weight for semantic search results (0.0-1.0)
        
    Returns:
        Formatted hybrid search results
    """
    try:
        # For now, use advanced text search with meeting-specific logic
        # TODO: Implement true hybrid text+vector search
        
        # Try meeting search first if query mentions meetings
        meeting_keywords = ['meeting', 'discuss', 'agenda', 'minutes', 'call', 'conference']
        if any(keyword in query.lower() for keyword in meeting_keywords):
            meeting_results = await _search_meetings(query, match_count // 2)
            doc_results = await _search_documents_by_text(query, match_count // 2)
            results = meeting_results + doc_results
        else:
            results = await _search_documents_by_text(query, match_count)
        
        if not results:
            return f"No hybrid search results found for: {query}"
        
        formatted_results = []
        formatted_results.append(f"⚡ HYBRID SEARCH RESULTS for '{query}':")
        formatted_results.append(f"Text Weight: {text_weight:.1f} | Semantic Weight: {semantic_weight:.1f}")
        formatted_results.append("=" * 55)
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_results = []
        for doc in results:
            doc_id = doc.get('id')
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                unique_results.append(doc)
        
        for i, doc in enumerate(unique_results[:match_count], 1):
            title = doc.get('title', 'No title')[:60]
            content = doc.get('content', '')[:200]
            source = doc.get('source', 'Unknown')
            created_at = doc.get('created_at', 'Unknown date')
            
            formatted_results.append(f"\n{i}. {title}")
            formatted_results.append(f"   Source: {source}")
            formatted_results.append(f"   Date: {created_at}")
            formatted_results.append(f"   Content: {content}...")
            
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Hybrid search failed: {str(e)}"


async def get_recent_documents(
    ctx: RunContext, 
    limit: int = 10,
    source_filter: Optional[str] = None
) -> str:
    """
    Get recent documents with optional source filtering.
    
    Args:
        ctx: Agent runtime context
        limit: Maximum number of documents to return
        source_filter: Optional source filter (e.g., 'meeting', 'email', 'report')
        
    Returns:
        Formatted recent documents list
    """
    try:
        results = await _search_recent_documents(limit * 2)  # Get extra for filtering
        
        if source_filter:
            filtered_results = [
                doc for doc in results 
                if source_filter.lower() in doc.get('source', '').lower() or
                   source_filter.lower() in doc.get('title', '').lower()
            ]
            results = filtered_results[:limit]
        else:
            results = results[:limit]
        
        if not results:
            filter_msg = f" matching '{source_filter}'" if source_filter else ""
            return f"No recent documents found{filter_msg}"
        
        formatted_results = []
        formatted_results.append(f"📅 RECENT DOCUMENTS ({len(results)} found):")
        if source_filter:
            formatted_results.append(f"Filtered by: {source_filter}")
        formatted_results.append("=" * 50)
        
        for i, doc in enumerate(results, 1):
            title = doc.get('title', 'No title')[:60]
            content = doc.get('content', '')[:150]
            source = doc.get('source', 'Unknown')
            created_at = doc.get('created_at', 'Unknown date')
            
            formatted_results.append(f"\n{i}. {title}")
            formatted_results.append(f"   Source: {source}")
            formatted_results.append(f"   Date: {created_at}")
            formatted_results.append(f"   Preview: {content}...")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Recent documents search failed: {str(e)}"


async def search_by_project(
    ctx: RunContext,
    project_name: str,
    match_count: int = 5
) -> str:
    """
    Search for documents related to a specific project.
    
    Args:
        ctx: Agent runtime context
        project_name: Name of the project to search for
        match_count: Number of results to return
        
    Returns:
        Formatted project-specific search results
    """
    try:
        # Search for project name in both title and content
        query = f"{project_name} project"
        results = await _search_documents_by_text(query, match_count)
        
        if not results:
            return f"No documents found for project: {project_name}"
        
        formatted_results = []
        formatted_results.append(f"🏗️ PROJECT SEARCH RESULTS for '{project_name}':")
        formatted_results.append("=" * 55)
        
        for i, doc in enumerate(results, 1):
            title = doc.get('title', 'No title')[:60]
            content = doc.get('content', '')[:200]
            source = doc.get('source', 'Unknown')
            created_at = doc.get('created_at', 'Unknown date')
            
            formatted_results.append(f"\n{i}. {title}")
            formatted_results.append(f"   Source: {source}")
            formatted_results.append(f"   Date: {created_at}")
            formatted_results.append(f"   Content: {content}...")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Project search failed: {str(e)}"


# Additional utility functions for advanced search

async def get_document_summary(doc_id: str) -> Dict[str, Any]:
    """Get detailed summary of a specific document."""
    try:
        result = await db.execute_one(
            "SELECT id, title, content, source, created_at FROM documents WHERE id = $1",
            doc_id
        )
        return result if result else {}
    except Exception:
        return {}


async def search_by_date_range(
    start_date: str, 
    end_date: str, 
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search documents within a specific date range."""
    try:
        results = await db.execute_query(
            """
            SELECT id, title, content, source, created_at 
            FROM documents 
            WHERE created_at >= $1 AND created_at <= $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            start_date, end_date, limit
        )
        return results
    except Exception:
        return []