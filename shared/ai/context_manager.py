"""
Context and Conversation Memory Manager for PM RAG Agent

This module manages conversation history, business context, and session state
for the elite PM business intelligence system, enabling contextual responses
and personalized interactions.

Author: Alleato AI Team
Last Updated: September 2024
Related Files:
    - intelligence/search_strategies.py: Advanced search with context
    - core/prompts.py: Dynamic context injection
    - dependencies.py: Context storage dependencies
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json
import asyncio
from enum import Enum


class MemoryType(Enum):
    """Types of memory storage."""
    SHORT_TERM = "short_term"  # Current conversation
    WORKING = "working"  # Current session
    EPISODIC = "episodic"  # Specific project/task memories
    SEMANTIC = "semantic"  # General knowledge and patterns
    PROCEDURAL = "procedural"  # How-to knowledge


class ConversationMemory:
    """
    Manages conversation history and context for continuous interactions.
    """
    
    def __init__(self, max_turns: int = 10, max_tokens: int = 4000):
        """
        Initialize conversation memory.
        
        Args:
            max_turns: Maximum conversation turns to keep
            max_tokens: Maximum tokens to retain in memory
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.history = deque(maxlen=max_turns)
        self.context_stack = []
        self.entity_memory = defaultdict(list)
        self.topic_transitions = []
    
    def add_exchange(self, user_message: str, assistant_response: str, metadata: Optional[Dict] = None):
        """
        Add a conversation exchange to memory.
        
        Args:
            user_message: User's input
            assistant_response: Assistant's response
            metadata: Additional context (intent, entities, etc.)
        """
        exchange = {
            'timestamp': datetime.now().isoformat(),
            'user': user_message,
            'assistant': assistant_response,
            'metadata': metadata or {}
        }
        
        self.history.append(exchange)
        
        # Extract and store entities
        if metadata and 'entities' in metadata:
            for entity_type, entities in metadata['entities'].items():
                self.entity_memory[entity_type].extend(entities)
        
        # Track topic transitions
        if metadata and 'topic' in metadata:
            self._track_topic_transition(metadata['topic'])
        
        # Manage token limits
        self._compress_if_needed()
    
    def _track_topic_transition(self, topic: str):
        """Track topic changes in conversation."""
        if not self.topic_transitions or self.topic_transitions[-1]['topic'] != topic:
            self.topic_transitions.append({
                'topic': topic,
                'timestamp': datetime.now().isoformat(),
                'turn_number': len(self.history)
            })
    
    def _compress_if_needed(self):
        """Compress memory if approaching token limits."""
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        total_chars = sum(
            len(ex['user']) + len(ex['assistant']) 
            for ex in self.history
        )
        estimated_tokens = total_chars // 4
        
        if estimated_tokens > self.max_tokens:
            # Keep most recent and summarize older
            recent = list(self.history)[-5:]
            older = list(self.history)[:-5]
            
            if older:
                summary = self._summarize_exchanges(older)
                self.history = deque([summary] + recent, maxlen=self.max_turns)
    
    def _summarize_exchanges(self, exchanges: List[Dict]) -> Dict:
        """Summarize multiple exchanges into a single summary."""
        topics = set()
        entities = defaultdict(set)
        decisions = []
        
        for ex in exchanges:
            if 'metadata' in ex:
                if 'topic' in ex['metadata']:
                    topics.add(ex['metadata']['topic'])
                if 'entities' in ex['metadata']:
                    for entity_type, ents in ex['metadata']['entities'].items():
                        entities[entity_type].update(ents)
                if 'decisions' in ex['metadata']:
                    decisions.extend(ex['metadata']['decisions'])
        
        summary_text = f"Previous discussion covered: {', '.join(topics)}. "
        if entities:
            summary_text += f"Entities mentioned: {dict(entities)}. "
        if decisions:
            summary_text += f"Decisions made: {', '.join(decisions)}."
        
        return {
            'timestamp': exchanges[0]['timestamp'],
            'user': '[Summary of earlier conversation]',
            'assistant': summary_text,
            'metadata': {
                'is_summary': True,
                'exchanges_summarized': len(exchanges)
            }
        }
    
    def get_context(self, last_n: int = 5) -> str:
        """
        Get formatted conversation context.
        
        Args:
            last_n: Number of recent exchanges to include
            
        Returns:
            Formatted conversation history
        """
        recent = list(self.history)[-last_n:]
        context_parts = []
        
        for exchange in recent:
            if exchange.get('metadata', {}).get('is_summary'):
                context_parts.append(exchange['assistant'])
            else:
                context_parts.append(f"User: {exchange['user']}")
                context_parts.append(f"Assistant: {exchange['assistant']}")
        
        return "\n".join(context_parts)
    
    def get_entities(self, entity_type: Optional[str] = None) -> Dict[str, List]:
        """
        Get remembered entities from conversation.
        
        Args:
            entity_type: Specific entity type to retrieve
            
        Returns:
            Dictionary of entities by type
        """
        if entity_type:
            return {entity_type: list(set(self.entity_memory[entity_type]))}
        
        return {
            etype: list(set(entities))
            for etype, entities in self.entity_memory.items()
        }
    
    def get_topic_flow(self) -> List[Dict]:
        """Get the flow of topics through the conversation."""
        return self.topic_transitions


class BusinessContextManager:
    """
    Manages business context including projects, stakeholders, and strategic focus.
    """
    
    def __init__(self):
        """Initialize business context manager."""
        self.current_project = None
        self.active_projects = []
        self.stakeholder_context = {}
        self.strategic_context = {
            'current_quarter': None,
            'strategic_focus': [],
            'priority_clients': [],
            'key_initiatives': []
        }
        self.temporal_context = {
            'upcoming_deadlines': [],
            'overdue_items': [],
            'recent_completions': []
        }
    
    def set_project_context(self, project: Dict[str, Any]):
        """
        Set current project context.
        
        Args:
            project: Project information dictionary
        """
        self.current_project = {
            'id': project.get('id'),
            'name': project.get('name'),
            'phase': project.get('phase', 'Unknown'),
            'stakeholders': project.get('stakeholders', []),
            'budget': project.get('budget'),
            'timeline': project.get('timeline'),
            'risks': project.get('active_risks', []),
            'last_updated': datetime.now().isoformat()
        }
    
    def add_active_project(self, project: Dict[str, Any]):
        """Add a project to active monitoring."""
        project_summary = {
            'id': project.get('id'),
            'name': project.get('name'),
            'priority': project.get('priority', 'medium'),
            'status': project.get('status'),
            'next_milestone': project.get('next_milestone')
        }
        
        # Remove if already exists, then add updated
        self.active_projects = [
            p for p in self.active_projects 
            if p['id'] != project_summary['id']
        ]
        self.active_projects.append(project_summary)
        
        # Sort by priority
        priority_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
        self.active_projects.sort(
            key=lambda p: priority_order.get(p['priority'], 4)
        )
    
    def update_strategic_context(self, updates: Dict[str, Any]):
        """
        Update strategic business context.
        
        Args:
            updates: Dictionary of strategic updates
        """
        for key, value in updates.items():
            if key in self.strategic_context:
                if isinstance(self.strategic_context[key], list):
                    # For lists, merge and deduplicate
                    existing = self.strategic_context[key]
                    self.strategic_context[key] = list(set(existing + value))
                else:
                    self.strategic_context[key] = value
    
    def update_temporal_context(self, deadlines: List[Dict] = None, 
                               overdue: List[Dict] = None,
                               completions: List[Dict] = None):
        """
        Update time-sensitive context.
        
        Args:
            deadlines: Upcoming deadline items
            overdue: Overdue items
            completions: Recently completed items
        """
        if deadlines:
            self.temporal_context['upcoming_deadlines'] = sorted(
                deadlines, 
                key=lambda x: x.get('due_date', '')
            )[:5]  # Keep top 5
        
        if overdue:
            self.temporal_context['overdue_items'] = sorted(
                overdue,
                key=lambda x: x.get('days_overdue', 0),
                reverse=True
            )[:5]
        
        if completions:
            self.temporal_context['recent_completions'] = sorted(
                completions,
                key=lambda x: x.get('completion_date', ''),
                reverse=True
            )[:5]
    
    def get_context_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive business context summary.
        
        Returns:
            Dictionary with all business context
        """
        return {
            'current_project': self.current_project,
            'active_projects_count': len(self.active_projects),
            'top_priority_projects': self.active_projects[:3],
            'strategic_focus': self.strategic_context,
            'temporal_alerts': {
                'has_overdue': len(self.temporal_context['overdue_items']) > 0,
                'upcoming_deadlines_count': len(self.temporal_context['upcoming_deadlines']),
                'overdue_count': len(self.temporal_context['overdue_items'])
            }
        }


class SessionStateManager:
    """
    Manages session state including user preferences and interaction patterns.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize session state manager.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.session_start = datetime.now()
        self.user_preferences = {
            'detail_level': 'balanced',  # concise, balanced, detailed
            'focus_areas': [],
            'preferred_format': 'structured',  # structured, narrative, bullet_points
            'technical_level': 'business'  # business, technical, executive
        }
        self.interaction_stats = {
            'queries_count': 0,
            'topics_covered': set(),
            'average_response_satisfaction': None,
            'most_accessed_projects': defaultdict(int)
        }
        self.learning_insights = []
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """Update user preferences based on interactions."""
        self.user_preferences.update(preferences)
    
    def track_interaction(self, query: str, topic: str, project_id: Optional[str] = None):
        """
        Track user interaction patterns.
        
        Args:
            query: User query
            topic: Identified topic
            project_id: Related project if applicable
        """
        self.interaction_stats['queries_count'] += 1
        self.interaction_stats['topics_covered'].add(topic)
        
        if project_id:
            self.interaction_stats['most_accessed_projects'][project_id] += 1
        
        # Learn from patterns
        self._learn_from_interaction(query, topic)
    
    def _learn_from_interaction(self, query: str, topic: str):
        """Learn user patterns from interactions."""
        # Detect preference for detail level
        if len(query.split()) > 50:
            self.user_preferences['detail_level'] = 'detailed'
        elif len(query.split()) < 10:
            self.user_preferences['detail_level'] = 'concise'
        
        # Detect technical vs business focus
        technical_keywords = ['api', 'code', 'implementation', 'technical', 'architecture']
        business_keywords = ['roi', 'budget', 'strategy', 'stakeholder', 'revenue']
        
        query_lower = query.lower()
        if any(kw in query_lower for kw in technical_keywords):
            self.user_preferences['technical_level'] = 'technical'
        elif any(kw in query_lower for kw in business_keywords):
            self.user_preferences['technical_level'] = 'business'
    
    def get_session_insights(self) -> Dict[str, Any]:
        """
        Get insights about the current session.
        
        Returns:
            Session insights and patterns
        """
        session_duration = (datetime.now() - self.session_start).seconds / 60
        
        # Get most accessed projects
        top_projects = sorted(
            self.interaction_stats['most_accessed_projects'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            'session_id': self.session_id,
            'duration_minutes': round(session_duration, 1),
            'queries_count': self.interaction_stats['queries_count'],
            'topics_covered': list(self.interaction_stats['topics_covered']),
            'top_projects': top_projects,
            'user_preferences': self.user_preferences,
            'queries_per_minute': round(
                self.interaction_stats['queries_count'] / max(session_duration, 1), 
                2
            )
        }


class IntegratedContextManager:
    """
    Integrates all context managers for comprehensive context handling.
    """
    
    def __init__(self, session_id: str):
        """
        Initialize integrated context manager.
        
        Args:
            session_id: Session identifier
        """
        self.conversation = ConversationMemory()
        self.business = BusinessContextManager()
        self.session = SessionStateManager(session_id)
    
    def process_interaction(
        self,
        user_message: str,
        assistant_response: str,
        metadata: Dict[str, Any]
    ):
        """
        Process a complete interaction updating all context.
        
        Args:
            user_message: User's input
            assistant_response: Assistant's response
            metadata: Interaction metadata
        """
        # Update conversation memory
        self.conversation.add_exchange(user_message, assistant_response, metadata)
        
        # Update session tracking
        topic = metadata.get('topic', 'general')
        project_id = metadata.get('project_id')
        self.session.track_interaction(user_message, topic, project_id)
        
        # Update business context if project mentioned
        if project_id and 'project_data' in metadata:
            self.business.set_project_context(metadata['project_data'])
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Get complete integrated context.
        
        Returns:
            Comprehensive context dictionary
        """
        return {
            'conversation': {
                'recent_context': self.conversation.get_context(),
                'entities': self.conversation.get_entities(),
                'topic_flow': self.conversation.get_topic_flow()
            },
            'business': self.business.get_context_summary(),
            'session': self.session.get_session_insights()
        }
    
    def generate_contextual_prompt_extension(self) -> str:
        """
        Generate dynamic prompt extension based on current context.
        
        Returns:
            Context-aware prompt extension
        """
        parts = []
        
        # Add conversation context
        recent = self.conversation.get_context(last_n=3)
        if recent:
            parts.append(f"Recent Conversation:\n{recent}")
        
        # Add business context
        business = self.business.get_context_summary()
        if business['current_project']:
            project = business['current_project']
            parts.append(f"Current Project: {project['name']} (Phase: {project['phase']})")
        
        if business['temporal_alerts']['has_overdue']:
            parts.append(f"⚠️ Alert: {business['temporal_alerts']['overdue_count']} overdue items")
        
        # Add user preferences
        prefs = self.session.user_preferences
        parts.append(f"User Preferences: Detail level: {prefs['detail_level']}, "
                    f"Technical level: {prefs['technical_level']}")
        
        # Add session insights
        insights = self.session.get_session_insights()
        if insights['top_projects']:
            top_proj = insights['top_projects'][0]
            parts.append(f"Session Focus: Project {top_proj[0]} ({top_proj[1]} queries)")
        
        return "\n\n".join(parts) if parts else ""


# Export main context manager
def create_context_manager(session_id: str) -> IntegratedContextManager:
    """
    Factory function to create an integrated context manager.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Configured IntegratedContextManager instance
    """
    return IntegratedContextManager(session_id)