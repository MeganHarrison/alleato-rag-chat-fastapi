"""
Conversation Memory Management for RAG System

This module provides sophisticated conversation memory handling including:
- Short-term working memory (recent messages)
- Long-term memory (important facts and summaries)
- Sliding window with importance-based retention
- Automatic summarization and compression
- Context-aware retrieval
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import logging

import asyncpg
import numpy as np
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FactType(Enum):
    ENTITY = "entity"
    PREFERENCE = "preference"
    CONSTRAINT = "constraint"
    GOAL = "goal"
    CONTEXT = "context"


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: MessageRole
    content: str
    message_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.5
    embedding: Optional[List[float]] = None
    retrieved_chunks: Optional[List[str]] = None


@dataclass
class ConversationFact:
    """Represents an extracted fact from the conversation."""
    fact_type: FactType
    fact_key: str
    fact_value: Any
    confidence: float = 1.0
    source_message_id: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class ConversationContext:
    """Complete context for a conversation."""
    conversation_id: str
    messages: List[ConversationMessage]
    facts: List[ConversationFact]
    summary: Optional[str] = None
    project_id: Optional[int] = None
    total_messages: int = 0


class ConversationMemoryManager:
    """Manages conversation memory with sophisticated retrieval and compression."""
    
    def __init__(
        self,
        db_pool: asyncpg.Pool,
        embedding_function: callable,
        max_working_memory: int = 20,  # Max messages in working memory
        importance_threshold: float = 0.7,  # Threshold for long-term retention
        compression_threshold: int = 50,  # Messages before compression
        summarization_threshold: int = 100,  # Messages before summarization
    ):
        self.db_pool = db_pool
        self.embedding_function = embedding_function
        self.max_working_memory = max_working_memory
        self.importance_threshold = importance_threshold
        self.compression_threshold = compression_threshold
        self.summarization_threshold = summarization_threshold
        
        # In-memory cache for active conversations
        self._memory_cache: Dict[str, ConversationContext] = {}
    
    async def create_or_get_conversation(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> str:
        """Create a new conversation or get existing one."""
        async with self.db_pool.acquire() as conn:
            # Check if conversation exists
            existing = await conn.fetchrow(
                """
                SELECT id FROM conversations
                WHERE session_id = $1 AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                session_id
            )
            
            if existing:
                return str(existing['id'])
            
            # Create new conversation
            result = await conn.fetchrow(
                """
                INSERT INTO conversations (session_id, user_id, project_id)
                VALUES ($1, $2, $3)
                RETURNING id::text
                """,
                session_id, user_id, project_id
            )
            
            return result['id']
    
    async def add_message(
        self,
        conversation_id: str,
        message: ConversationMessage,
        retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Add a message to the conversation with intelligent processing."""
        
        # Generate embedding if not provided
        if message.embedding is None and self.embedding_function:
            message.embedding = await self.embedding_function(message.content)
        
        # Calculate importance score
        importance = await self._calculate_importance(message, conversation_id)
        message.importance_score = importance
        
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Get next message index
                next_index = await conn.fetchval(
                    """
                    SELECT COALESCE(MAX(message_index), -1) + 1
                    FROM conversation_messages
                    WHERE conversation_id = $1::uuid
                    """,
                    conversation_id
                )
                
                # Insert message
                embedding_str = None
                if message.embedding:
                    embedding_str = '[' + ','.join(map(str, message.embedding)) + ']'
                
                message_result = await conn.fetchrow(
                    """
                    INSERT INTO conversation_messages (
                        conversation_id, role, content, message_index,
                        metadata, importance_score, embedding, retrieved_chunks
                    )
                    VALUES ($1::uuid, $2, $3, $4, $5, $6, $7::vector, $8)
                    RETURNING id::text
                    """,
                    conversation_id,
                    message.role.value,
                    message.content,
                    next_index,
                    json.dumps(message.metadata),
                    importance,
                    embedding_str,
                    json.dumps(message.retrieved_chunks) if message.retrieved_chunks else None
                )
                
                message_id = message_result['id']
                
                # Store retrieval information if provided
                if retrieved_chunks:
                    for chunk in retrieved_chunks:
                        await conn.execute(
                            """
                            INSERT INTO conversation_retrievals (
                                conversation_id, message_id, chunk_id, document_id,
                                relevance_score, was_cited
                            )
                            VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, $5, $6)
                            """,
                            conversation_id,
                            message_id,
                            chunk.get('chunk_id'),
                            chunk.get('document_id'),
                            chunk.get('similarity', 0.0),
                            chunk.get('was_cited', False)
                        )
                
                # Extract and store facts
                if message.role == MessageRole.USER:
                    facts = await self._extract_facts(message, conversation_id)
                    for fact in facts:
                        await self._store_fact(conn, conversation_id, message_id, fact)
                
                # Check if compression or summarization needed
                total_messages = await conn.fetchval(
                    "SELECT total_messages FROM conversations WHERE id = $1::uuid",
                    conversation_id
                )
                
                if total_messages > 0:
                    if total_messages % self.compression_threshold == 0:
                        await self._compress_old_messages(conn, conversation_id)
                    
                    if total_messages % self.summarization_threshold == 0:
                        await self._create_summary(conn, conversation_id)
                
                return message_id
    
    async def get_conversation_context(
        self,
        conversation_id: str,
        include_facts: bool = True,
        max_messages: Optional[int] = None
    ) -> ConversationContext:
        """Get the full context for a conversation."""
        
        # Check cache first
        if conversation_id in self._memory_cache:
            cached = self._memory_cache[conversation_id]
            if len(cached.messages) < self.max_working_memory:
                return cached
        
        max_messages = max_messages or self.max_working_memory
        
        async with self.db_pool.acquire() as conn:
            # Get conversation metadata
            conv_data = await conn.fetchrow(
                """
                SELECT project_id, summary, total_messages
                FROM conversations
                WHERE id = $1::uuid
                """,
                conversation_id
            )
            
            # Get relevant messages using the smart context function
            messages_data = await conn.fetch(
                """
                SELECT * FROM get_conversation_context($1::uuid, $2, $3)
                """,
                conversation_id, max_messages, self.importance_threshold
            )
            
            messages = []
            for msg in messages_data:
                messages.append(ConversationMessage(
                    message_id=str(msg['message_id']),
                    role=MessageRole(msg['role']),
                    content=msg['content'],
                    timestamp=msg['timestamp'],
                    metadata=json.loads(msg['metadata']) if msg['metadata'] else {},
                    importance_score=msg['importance_score']
                ))
            
            facts = []
            if include_facts:
                facts_data = await conn.fetch(
                    """
                    SELECT fact_type, fact_key, fact_value, confidence
                    FROM conversation_facts
                    WHERE conversation_id = $1::uuid
                        AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    ORDER BY confidence DESC
                    """,
                    conversation_id
                )
                
                for fact in facts_data:
                    facts.append(ConversationFact(
                        fact_type=FactType(fact['fact_type']),
                        fact_key=fact['fact_key'],
                        fact_value=json.loads(fact['fact_value']),
                        confidence=fact['confidence']
                    ))
            
            context = ConversationContext(
                conversation_id=conversation_id,
                messages=messages,
                facts=facts,
                summary=conv_data['summary'],
                project_id=conv_data['project_id'],
                total_messages=conv_data['total_messages']
            )
            
            # Update cache
            self._memory_cache[conversation_id] = context
            
            return context
    
    async def find_similar_conversations(
        self,
        query: str,
        current_conversation_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past conversations."""
        
        # Generate query embedding
        query_embedding = await self.embedding_function(query)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        async with self.db_pool.acquire() as conn:
            results = await conn.fetch(
                """
                SELECT * FROM find_similar_conversations($1::vector, $2::uuid, $3)
                """,
                embedding_str,
                current_conversation_id,
                limit
            )
            
            return [
                {
                    'conversation_id': str(row['conversation_id']),
                    'title': row['title'],
                    'summary': row['summary'],
                    'similarity': row['similarity'],
                    'last_active': row['last_active']
                }
                for row in results
            ]
    
    async def get_relevant_history(
        self,
        conversation_id: str,
        current_query: str,
        max_messages: int = 10
    ) -> List[ConversationMessage]:
        """Get conversation history most relevant to current query."""
        
        # Get query embedding
        query_embedding = await self.embedding_function(current_query)
        
        async with self.db_pool.acquire() as conn:
            # Find most relevant past messages
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            relevant_messages = await conn.fetch(
                """
                WITH ranked_messages AS (
                    SELECT 
                        id::text as message_id,
                        role,
                        content,
                        timestamp,
                        metadata,
                        importance_score,
                        1 - (embedding <=> $2::vector) as similarity
                    FROM conversation_messages
                    WHERE conversation_id = $1::uuid
                        AND embedding IS NOT NULL
                    ORDER BY similarity DESC
                    LIMIT $3
                )
                SELECT * FROM ranked_messages
                WHERE similarity > 0.5
                ORDER BY timestamp DESC
                """,
                conversation_id,
                embedding_str,
                max_messages * 2  # Get more to filter
            )
            
            messages = []
            for msg in relevant_messages[:max_messages]:
                messages.append(ConversationMessage(
                    message_id=msg['message_id'],
                    role=MessageRole(msg['role']),
                    content=msg['content'],
                    timestamp=msg['timestamp'],
                    metadata=json.loads(msg['metadata']) if msg['metadata'] else {},
                    importance_score=msg['importance_score']
                ))
            
            return messages
    
    async def _calculate_importance(
        self,
        message: ConversationMessage,
        conversation_id: str
    ) -> float:
        """Calculate importance score for a message."""
        
        importance = 0.5  # Base importance
        
        # User messages are inherently more important
        if message.role == MessageRole.USER:
            importance += 0.2
        
        # Check for key indicators
        indicators = {
            'question': ['?', 'what', 'why', 'how', 'when', 'where'],
            'action': ['need', 'want', 'must', 'should', 'will', 'please'],
            'decision': ['decide', 'choose', 'select', 'approve', 'reject'],
            'important': ['important', 'critical', 'urgent', 'priority', 'asap'],
            'summary': ['summary', 'conclusion', 'overall', 'total', 'final']
        }
        
        content_lower = message.content.lower()
        for category, keywords in indicators.items():
            if any(keyword in content_lower for keyword in keywords):
                if category in ['important', 'decision']:
                    importance += 0.3
                else:
                    importance += 0.1
        
        # Length-based importance (very short or very long messages)
        word_count = len(message.content.split())
        if word_count < 10:
            importance -= 0.1
        elif word_count > 100:
            importance += 0.1
        
        # Recency boost (newer messages slightly more important)
        importance += 0.05
        
        return min(1.0, max(0.0, importance))
    
    async def _extract_facts(
        self,
        message: ConversationMessage,
        conversation_id: str
    ) -> List[ConversationFact]:
        """Extract facts from a message."""
        
        facts = []
        content_lower = message.content.lower()
        
        # Extract preferences
        preference_patterns = [
            ('prefer', 'preference'),
            ('like', 'preference'),
            ('want', 'preference'),
            ('need', 'constraint')
        ]
        
        for pattern, fact_type in preference_patterns:
            if pattern in content_lower:
                # Simple extraction - can be enhanced with NLP
                facts.append(ConversationFact(
                    fact_type=FactType(fact_type),
                    fact_key=f"{pattern}_statement",
                    fact_value={"statement": message.content, "timestamp": datetime.now().isoformat()},
                    confidence=0.7
                ))
        
        # Extract entities (simplified - enhance with NER)
        if 'project' in content_lower:
            # Extract project references
            facts.append(ConversationFact(
                fact_type=FactType.ENTITY,
                fact_key="mentioned_project",
                fact_value={"content": message.content, "timestamp": datetime.now().isoformat()},
                confidence=0.8
            ))
        
        # Extract temporal constraints
        temporal_keywords = ['deadline', 'by', 'before', 'after', 'until']
        if any(keyword in content_lower for keyword in temporal_keywords):
            facts.append(ConversationFact(
                fact_type=FactType.CONSTRAINT,
                fact_key="temporal_constraint",
                fact_value={"content": message.content, "timestamp": datetime.now().isoformat()},
                confidence=0.6,
                expires_at=datetime.now() + timedelta(days=30)  # Temporal facts expire
            ))
        
        return facts
    
    async def _store_fact(
        self,
        conn: asyncpg.Connection,
        conversation_id: str,
        message_id: str,
        fact: ConversationFact
    ):
        """Store a fact in the database."""
        await conn.execute(
            """
            INSERT INTO conversation_facts (
                conversation_id, message_id, fact_type, fact_key, 
                fact_value, confidence, expires_at
            )
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7)
            ON CONFLICT (conversation_id, fact_type, fact_key) DO UPDATE
            SET 
                fact_value = EXCLUDED.fact_value,
                confidence = GREATEST(conversation_facts.confidence, EXCLUDED.confidence),
                message_id = EXCLUDED.message_id,
                expires_at = EXCLUDED.expires_at
            """,
            conversation_id,
            message_id,
            fact.fact_type.value,
            fact.fact_key,
            json.dumps(fact.fact_value),
            fact.confidence,
            fact.expires_at
        )
    
    async def _compress_old_messages(
        self,
        conn: asyncpg.Connection,
        conversation_id: str
    ):
        """Compress old messages to save space."""
        compressed_count = await conn.fetchval(
            "SELECT compress_old_messages($1::uuid, $2)",
            conversation_id,
            self.compression_threshold
        )
        
        if compressed_count > 0:
            logger.info(f"Compressed {compressed_count} messages in conversation {conversation_id}")
    
    async def _create_summary(
        self,
        conn: asyncpg.Connection,
        conversation_id: str
    ):
        """Create a summary of the conversation."""
        # This would integrate with your LLM to generate summaries
        # For now, we'll create a placeholder
        
        # Get recent messages for summarization
        messages = await conn.fetch(
            """
            SELECT role, content
            FROM conversation_messages
            WHERE conversation_id = $1::uuid
                AND is_compressed = FALSE
            ORDER BY message_index DESC
            LIMIT 50
            """,
            conversation_id
        )
        
        # TODO: Call LLM to generate summary
        # summary = await generate_summary(messages)
        summary = f"Conversation summary pending for {len(messages)} messages"
        
        # Store summary
        await conn.execute(
            """
            UPDATE conversations
            SET summary = $2
            WHERE id = $1::uuid
            """,
            conversation_id,
            summary
        )
    
    async def clear_cache(self, conversation_id: Optional[str] = None):
        """Clear memory cache."""
        if conversation_id:
            self._memory_cache.pop(conversation_id, None)
        else:
            self._memory_cache.clear()
    
    async def archive_conversation(self, conversation_id: str):
        """Archive a conversation."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations
                SET status = 'archived'
                WHERE id = $1::uuid
                """,
                conversation_id
            )
        
        # Remove from cache
        self._memory_cache.pop(conversation_id, None)