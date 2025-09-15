"""Simple search functions that actually work."""

from database import db
from typing import List, Dict, Any

async def search_recent_documents(limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent documents from database."""
    try:
        documents = await db.get_recent_documents(limit)
        print(f"Found {len(documents)} recent documents")
        return documents
    except Exception as e:
        print(f"Search failed: {e}")
        return []

async def search_documents_by_text(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search documents by text content."""
    try:
        documents = await db.search_documents(query, limit)
        print(f"Found {len(documents)} documents for query: {query}")
        return documents
    except Exception as e:
        print(f"Search failed: {e}")
        return []

async def search_meetings(query: str = None, limit: int = 10) -> List[Dict[str, Any]]:
    """Search meeting documents specifically."""
    try:
        if query:
            # Search for specific meeting content
            documents = await db.search_documents(f"meeting {query}", limit)
        else:
            # Get recent meetings
            documents = await db.execute_query("""
                SELECT id, title, content, created_at, source
                FROM documents 
                WHERE title ILIKE '%meeting%' OR content ILIKE '%meeting%'
                ORDER BY created_at DESC 
                LIMIT $1
            """, limit)
        
        print(f"Found {len(documents)} meeting documents")
        return documents
    except Exception as e:
        print(f"Meeting search failed: {e}")
        return []