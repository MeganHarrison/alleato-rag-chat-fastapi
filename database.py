"""Simple database connection that actually works."""

import asyncpg
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.pool = None
        # Try connection pooler first, then direct connection
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL not set")
        
        # Keep the same URL but we'll use different SSL settings for Render
        if os.getenv("RENDER"):
            print("🔄 Render detected - will use custom SSL settings")
    
    async def connect(self):
        """Connect to database."""
        if not self.pool:
            # Add SSL and connection settings for cloud deployment
            ssl_context = None
            if os.getenv("RENDER"):
                # Try different connection approaches for Render
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
                ssl=ssl_context
            )
            print("✅ Database connected successfully")
    
    async def execute_query(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return results."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_one(self, query: str, *args) -> Dict[str, Any]:
        """Execute a query and return one result."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else {}
    
    async def get_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent documents."""
        query = """
        SELECT id, title, content, created_at, source
        FROM documents 
        ORDER BY created_at DESC 
        LIMIT $1
        """
        return await self.execute_query(query, limit)
    
    async def search_documents(self, search_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents by text."""
        query = """
        SELECT d.id, d.title, d.content, d.created_at, d.source,
               c.content as chunk_content
        FROM documents d
        JOIN chunks c ON d.id = c.document_id
        WHERE d.content ILIKE $1 OR c.content ILIKE $1
        ORDER BY d.created_at DESC
        LIMIT $2
        """
        search_pattern = f"%{search_text}%"
        return await self.execute_query(query, search_pattern, limit)

# Global database instance
db = Database()