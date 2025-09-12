"""Search tools for Semantic Search Agent."""

from typing import Optional, List, Dict, Any
from pydantic_ai import RunContext
from pydantic import BaseModel, Field
import asyncpg
import json
from shared.ai.dependencies import AgentDependencies
try:
    from shared.monitoring.tracing import get_tracer
    ADVANCED_TRACING = True
except ImportError:
    from shared.monitoring.simple_tracing import get_simple_tracer as get_tracer
    ADVANCED_TRACING = False


class SearchResult(BaseModel):
    """Model for search results."""
    chunk_id: str
    document_id: str
    content: str
    similarity: float
    metadata: Dict[str, Any]
    document_title: str
    document_source: str


@get_tracer().trace_search_operation("semantic")
async def semantic_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None
) -> List[SearchResult]:
    """
    Perform pure semantic search using vector similarity.
    
    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
    
    Returns:
        List of search results ordered by similarity
    """
    try:
        deps = ctx.deps
        
        # Check if database is available, use fallback if not
        if not deps.db_pool or not hasattr(deps.db_pool, 'acquire'):
            print("Database not available, using fallback API for semantic search")
            from tools.api_fallback_search import fallback_semantic_search
            results = await fallback_semantic_search(ctx, query, match_count)
            # Convert to SearchResult objects if we got results
            return [
                SearchResult(
                    chunk_id=f"fallback_{i}",
                    document_id=f"fallback_doc_{i}",
                    content=result['content'],
                    similarity=result['similarity'],
                    metadata=result['metadata'],
                    document_title=result['document_title'],
                    document_source=result['document_source']
                )
                for i, result in enumerate(results)
            ]
        
        # Use default if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count
        
        # Validate match count
        match_count = min(match_count, deps.settings.max_match_count)
        
        # Generate embedding for query
        query_embedding = await deps.get_embedding(query)
        
        # Convert embedding to PostgreSQL vector string format
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Execute semantic search
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT * FROM match_chunks($1::vector, $2)
                """,
                embedding_str,
                match_count
            )
        
        # Convert to SearchResult objects
        return [
            SearchResult(
                chunk_id=str(row['chunk_id']),
                document_id=str(row['document_id']),
                content=row['content'],
                similarity=row['similarity'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {},
                document_title=row['document_title'],
                document_source=row['document_source']
            )
            for row in results
        ]
    except Exception as e:
        print(f"Semantic search error: {e}")
        return []


@get_tracer().trace_search_operation("hybrid")
async def hybrid_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    match_count: Optional[int] = None,
    text_weight: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining semantic and keyword matching.
    
    Args:
        ctx: Agent runtime context with dependencies
        query: Search query text
        match_count: Number of results to return (default: 10)
        text_weight: Weight for text matching (0-1, default: 0.3)
    
    Returns:
        List of search results with combined scores
    """
    try:
        deps = ctx.deps
        
        # Check if database is available
        if not deps.db_pool or not hasattr(deps.db_pool, 'acquire'):
            print("Database not available for hybrid search")
            return []
        
        # Use defaults if not specified
        if match_count is None:
            match_count = deps.settings.default_match_count
        if text_weight is None:
            text_weight = deps.user_preferences.get('text_weight', deps.settings.default_text_weight)
        
        # Validate parameters
        match_count = min(match_count, deps.settings.max_match_count)
        text_weight = max(0.0, min(1.0, text_weight))
        
        # Generate embedding for query
        query_embedding = await deps.get_embedding(query)
        
        # Convert embedding to PostgreSQL vector string format
        # PostgreSQL vector format: '[1.0,2.0,3.0]' (no spaces after commas)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Execute hybrid search
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT * FROM hybrid_search($1::vector, $2, $3, $4)
                """,
                embedding_str,
                query,
                match_count,
                text_weight
            )
        
        # Convert to dictionaries with additional scores
        return [
            {
                'chunk_id': str(row['chunk_id']),
                'document_id': str(row['document_id']),
                'content': row['content'],
                'combined_score': row['combined_score'],
                'vector_similarity': row['vector_similarity'],
                'text_similarity': row['text_similarity'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'document_title': row['document_title'],
                'document_source': row['document_source']
            }
            for row in results
        ]
    except Exception as e:
        print(f"Hybrid search error: {e}")
        return []


@get_tracer().trace_search_operation("recent_documents")
async def get_recent_documents(
    ctx: RunContext[AgentDependencies],
    limit: int = 5,
    document_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get the most recent documents ordered by creation date.
    
    Args:
        ctx: Agent runtime context with dependencies
        limit: Number of recent documents to return (default: 5)
        document_type: Optional filter by document type/category
    
    Returns:
        List of recent documents ordered by date (newest first)
    """
    try:
        deps = ctx.deps
        
        # Check if database is available, use fallback if not
        if not deps.db_pool or not hasattr(deps.db_pool, 'acquire'):
            print("Database not available, using fallback API for recent documents")
            from tools.api_fallback_search import fallback_recent_documents
            return await fallback_recent_documents(ctx, limit, document_type)
        
        # Build query with optional type filter
        base_query = """
        SELECT id, title, created_at, source, metadata, summary, 
               transcript_url, participants, duration_minutes, project
        FROM documents 
        """
        
        params = []
        if document_type:
            base_query += "WHERE category = $1 OR source = $1 "
            params.append(document_type)
        
        base_query += "ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        # Execute query
        async with deps.db_pool.acquire() as conn:
            results = await conn.fetch(base_query, *params)
        
        # Convert to dictionaries
        return [
            {
                'id': str(row['id']),
                'title': row['title'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'source': row['source'],
                'metadata': row['metadata'] if row['metadata'] else {},
                'summary': row['summary'],
                'transcript_url': row['transcript_url'],
                'participants': row['participants'] if row['participants'] else [],
                'duration_minutes': row['duration_minutes'],
                'project': row['project']
            }
            for row in results
        ]
    except Exception as e:
        print(f"Error getting recent documents: {e}")
        return []
