"""
Query Processor with Intent Classification for PM RAG Agent

This module provides intelligent query processing including intent classification,
entity extraction, query expansion, and search strategy selection. It's designed
to understand business and project management queries in depth.

Author: Alleato AI Team
Last Updated: September 2024
Related Files:
    - core/prompts.py: System prompts and context
    - tools/search_tools.py: Search implementation
    - intelligence/search_strategies.py: Advanced search strategies
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime, timedelta
import asyncio


class QueryIntent(Enum):
    """Classification of query intents for the PM RAG system."""
    
    # Project Management Intents
    STATUS_UPDATE = "status_update"          # Project status, progress updates
    RISK_ASSESSMENT = "risk_assessment"      # Risk identification and analysis
    ACTION_TRACKING = "action_tracking"      # Tasks, assignments, responsibilities
    TIMELINE_QUERY = "timeline_query"        # Schedule, deadlines, milestones
    RESOURCE_PLANNING = "resource_planning"  # Team, equipment, materials
    
    # Financial Intents
    BUDGET_ANALYSIS = "budget_analysis"      # Budget status, cost tracking
    FINANCIAL_FORECAST = "financial_forecast" # Projections, estimates
    COST_OPTIMIZATION = "cost_optimization"  # Savings opportunities
    
    # Business Strategy Intents
    STRATEGIC_ANALYSIS = "strategic_analysis" # Business strategy, competitive analysis
    MARKET_INTELLIGENCE = "market_intelligence" # Market trends, opportunities
    STAKEHOLDER_MGMT = "stakeholder_mgmt"   # Client, vendor, partner relations
    
    # Technical Intents
    TECHNICAL_SPEC = "technical_spec"        # Specifications, requirements
    COMPLIANCE_CHECK = "compliance_check"    # Standards, regulations
    ENGINEERING_DETAIL = "engineering_detail" # Technical details, calculations
    
    # General Intents
    INFORMATION_RETRIEVAL = "information_retrieval" # General information lookup
    DOCUMENT_SEARCH = "document_search"      # Find specific documents
    HISTORICAL_ANALYSIS = "historical_analysis" # Past project analysis


@dataclass
class ExtractedEntity:
    """Represents an extracted entity from the query."""
    entity_type: str  # project, person, date, money, company, etc.
    value: Any
    confidence: float
    context: str  # Surrounding text for context


@dataclass
class ProcessedQuery:
    """Complete processed query with all extracted information."""
    original_query: str
    cleaned_query: str
    intent: QueryIntent
    sub_intents: List[QueryIntent]
    entities: List[ExtractedEntity]
    temporal_context: Optional[Dict[str, Any]]
    search_filters: Dict[str, Any]
    expanded_terms: List[str]
    search_strategy: Dict[str, Any]
    confidence_scores: Dict[str, float]


class QueryProcessor:
    """
    Advanced query processor for PM RAG Agent.
    Handles intent classification, entity extraction, and query optimization.
    """
    
    def __init__(self):
        """Initialize the query processor with pattern definitions."""
        self._init_intent_patterns()
        self._init_entity_patterns()
        self._init_expansion_rules()
    
    def _init_intent_patterns(self):
        """Initialize patterns for intent classification."""
        self.intent_patterns = {
            QueryIntent.STATUS_UPDATE: [
                r'\b(status|progress|update|where|how far|current state)\b',
                r'\b(project status|status report|progress report)\b',
                r'\b(where are we|where do we stand)\b'
            ],
            QueryIntent.RISK_ASSESSMENT: [
                r'\b(risk|issue|problem|concern|challenge|threat)\b',
                r'\b(what could go wrong|potential problems|risk factors)\b',
                r'\b(mitigation|contingency|risk management)\b'
            ],
            QueryIntent.ACTION_TRACKING: [
                r'\b(who|assigned|responsible|owner|task|action)\b',
                r'\b(action items|to-do|tasks|assignments)\b',
                r'\b(what needs to be done|outstanding items)\b'
            ],
            QueryIntent.BUDGET_ANALYSIS: [
                r'\b(budget|cost|expense|spend|financial|money)\b',
                r'\b(over budget|under budget|cost overrun|savings)\b',
                r'\b(financial status|budget status|cost tracking)\b'
            ],
            QueryIntent.TIMELINE_QUERY: [
                r'\b(when|deadline|schedule|timeline|milestone|date)\b',
                r'\b(due date|completion date|target date)\b',
                r'\b(behind schedule|ahead of schedule|on track)\b'
            ],
            QueryIntent.STRATEGIC_ANALYSIS: [
                r'\b(strategy|strategic|competitive|market position)\b',
                r'\b(business plan|growth|expansion|opportunity)\b',
                r'\b(competitive advantage|market share)\b'
            ],
            QueryIntent.COMPLIANCE_CHECK: [
                r'\b(compliance|regulation|standard|requirement|code)\b',
                r'\b(FM Global|NFPA|OSHA|building code)\b',
                r'\b(meet requirements|compliance status)\b'
            ],
            QueryIntent.STAKEHOLDER_MGMT: [
                r'\b(client|customer|stakeholder|vendor|partner)\b',
                r'\b(satisfaction|feedback|relationship|communication)\b',
                r'\b(stakeholder concerns|client requirements)\b'
            ]
        }
    
    def _init_entity_patterns(self):
        """Initialize patterns for entity extraction."""
        self.entity_patterns = {
            'project_id': r'\b(?:project|proj|p)[\s#-]?(\d+)\b',
            'project_name': r'(?:project|for|on|regarding)\s+([A-Z][A-Za-z\s]+(?:Project|Collective|Event))',
            'person': r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:is|was|will|has|should|must)',
            'date': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|today|tomorrow|yesterday|next\s+\w+|last\s+\w+)\b',
            'money': r'\$[\d,]+(?:\.\d{2})?(?:[KMB])?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD)\b',
            'percentage': r'\b\d+(?:\.\d+)?%\b',
            'company': r'\b(?:Alleato|FM Global|[A-Z][A-Za-z]+\s+(?:Inc|Corp|LLC|Company|Group))\b',
            'technical_term': r'\b(?:ASRS|MEP|HVAC|sprinkler|rack|warehouse|construction)\b'
        }
    
    def _init_expansion_rules(self):
        """Initialize query expansion rules."""
        self.expansion_rules = {
            'status': ['progress', 'update', 'current state', 'report'],
            'budget': ['cost', 'expense', 'financial', 'spending', 'money'],
            'risk': ['issue', 'problem', 'concern', 'challenge', 'threat'],
            'timeline': ['schedule', 'deadline', 'milestone', 'date', 'timeframe'],
            'client': ['customer', 'stakeholder', 'end-user'],
            'asrs': ['automated storage', 'retrieval system', 'warehouse automation'],
            'compliance': ['regulation', 'standard', 'requirement', 'code']
        }
    
    async def process_query(self, 
                           query: str, 
                           context: Optional[Dict[str, Any]] = None) -> ProcessedQuery:
        """
        Process a query through the full pipeline.
        
        Args:
            query: The raw user query
            context: Optional context (project, user, conversation history)
            
        Returns:
            ProcessedQuery with all extracted information
            
        Related Files:
            - intelligence/search_strategies.py: Search strategy implementation
        """
        # Clean and normalize query
        cleaned_query = self._clean_query(query)
        
        # Classify intent
        intent, sub_intents, confidence_scores = await self._classify_intent(cleaned_query)
        
        # Extract entities
        entities = await self._extract_entities(query, cleaned_query)
        
        # Extract temporal context
        temporal_context = self._extract_temporal_context(query, entities)
        
        # Build search filters
        search_filters = self._build_search_filters(entities, temporal_context, context)
        
        # Expand query terms
        expanded_terms = self._expand_query(cleaned_query, intent)
        
        # Select search strategy
        search_strategy = self._select_search_strategy(intent, entities, expanded_terms)
        
        return ProcessedQuery(
            original_query=query,
            cleaned_query=cleaned_query,
            intent=intent,
            sub_intents=sub_intents,
            entities=entities,
            temporal_context=temporal_context,
            search_filters=search_filters,
            expanded_terms=expanded_terms,
            search_strategy=search_strategy,
            confidence_scores=confidence_scores
        )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query."""
        # Remove extra whitespace
        cleaned = ' '.join(query.split())
        
        # Normalize case for common terms
        cleaned = cleaned.replace('ASRS', 'asrs')
        cleaned = cleaned.replace('MEP', 'mep')
        
        # Remove common filler words
        filler_words = ['please', 'could you', 'can you', 'I need', 'show me']
        for filler in filler_words:
            cleaned = cleaned.replace(filler, '')
        
        return cleaned.strip()
    
    async def _classify_intent(self, query: str) -> Tuple[QueryIntent, List[QueryIntent], Dict[str, float]]:
        """
        Classify the primary and secondary intents of the query.
        
        Returns:
            Tuple of (primary_intent, secondary_intents, confidence_scores)
        """
        intent_scores = {}
        query_lower = query.lower()
        
        # Score each intent
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1.0
            
            if score > 0:
                # Normalize score
                intent_scores[intent] = min(score / len(patterns), 1.0)
        
        # If no specific intent found, default to information retrieval
        if not intent_scores:
            return (QueryIntent.INFORMATION_RETRIEVAL, [], {'default': 0.5})
        
        # Sort by score
        sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Primary intent is the highest scoring
        primary_intent = sorted_intents[0][0]
        
        # Secondary intents are those with score > 0.3
        sub_intents = [intent for intent, score in sorted_intents[1:] if score > 0.3]
        
        # Convert scores to dict
        confidence_scores = {str(intent): score for intent, score in sorted_intents}
        
        return primary_intent, sub_intents, confidence_scores
    
    async def _extract_entities(self, original: str, cleaned: str) -> List[ExtractedEntity]:
        """Extract entities from the query."""
        entities = []
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, original, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                
                # Get surrounding context
                start = max(0, match.start() - 20)
                end = min(len(original), match.end() + 20)
                context = original[start:end]
                
                # Process value based on type
                if entity_type == 'date':
                    value = self._parse_date(value)
                elif entity_type == 'money':
                    value = self._parse_money(value)
                elif entity_type == 'project_id':
                    value = int(value)
                
                entities.append(ExtractedEntity(
                    entity_type=entity_type,
                    value=value,
                    confidence=0.9,  # Simple pattern matching gives high confidence
                    context=context
                ))
        
        return entities
    
    def _extract_temporal_context(self, query: str, entities: List[ExtractedEntity]) -> Optional[Dict[str, Any]]:
        """Extract temporal context from query."""
        temporal_context = {}
        
        # Check for date entities
        date_entities = [e for e in entities if e.entity_type == 'date']
        if date_entities:
            temporal_context['dates'] = [e.value for e in date_entities]
        
        # Check for relative time references
        query_lower = query.lower()
        now = datetime.now()
        
        if 'last week' in query_lower:
            temporal_context['start_date'] = now - timedelta(weeks=1)
            temporal_context['end_date'] = now
        elif 'last month' in query_lower:
            temporal_context['start_date'] = now - timedelta(days=30)
            temporal_context['end_date'] = now
        elif 'this quarter' in query_lower:
            # Calculate current quarter
            quarter = (now.month - 1) // 3
            temporal_context['quarter'] = f"Q{quarter + 1} {now.year}"
        elif 'ytd' in query_lower or 'year to date' in query_lower:
            temporal_context['start_date'] = datetime(now.year, 1, 1)
            temporal_context['end_date'] = now
        
        # Check for urgency indicators
        if any(word in query_lower for word in ['urgent', 'asap', 'immediately', 'critical']):
            temporal_context['urgency'] = 'high'
        elif any(word in query_lower for word in ['soon', 'upcoming', 'next']):
            temporal_context['urgency'] = 'medium'
        
        return temporal_context if temporal_context else None
    
    def _build_search_filters(self, 
                             entities: List[ExtractedEntity],
                             temporal_context: Optional[Dict],
                             context: Optional[Dict]) -> Dict[str, Any]:
        """Build search filters from extracted information."""
        filters = {}
        
        # Add entity-based filters
        for entity in entities:
            if entity.entity_type == 'project_id':
                filters['project_id'] = entity.value
            elif entity.entity_type == 'project_name':
                filters['project_name'] = entity.value
            elif entity.entity_type == 'person':
                filters['assignee'] = entity.value
            elif entity.entity_type == 'company':
                filters['company'] = entity.value
        
        # Add temporal filters
        if temporal_context:
            if 'start_date' in temporal_context:
                filters['date_from'] = temporal_context['start_date']
            if 'end_date' in temporal_context:
                filters['date_to'] = temporal_context['end_date']
            if 'urgency' in temporal_context:
                filters['priority'] = temporal_context['urgency']
        
        # Add context-based filters
        if context:
            if 'current_project' in context:
                filters.setdefault('project_id', context['current_project'])
            if 'user_role' in context:
                filters['relevant_to_role'] = context['user_role']
        
        return filters
    
    def _expand_query(self, query: str, intent: QueryIntent) -> List[str]:
        """Expand query with synonyms and related terms."""
        expanded = []
        query_words = query.lower().split()
        
        # Add original terms
        expanded.extend(query_words)
        
        # Add expansions based on rules
        for word in query_words:
            if word in self.expansion_rules:
                expanded.extend(self.expansion_rules[word])
        
        # Add intent-specific expansions
        if intent == QueryIntent.BUDGET_ANALYSIS:
            expanded.extend(['financial', 'cost', 'expense', 'budget'])
        elif intent == QueryIntent.RISK_ASSESSMENT:
            expanded.extend(['risk', 'issue', 'mitigation', 'impact'])
        elif intent == QueryIntent.STATUS_UPDATE:
            expanded.extend(['progress', 'status', 'complete', 'milestone'])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_expanded = []
        for term in expanded:
            if term not in seen:
                seen.add(term)
                unique_expanded.append(term)
        
        return unique_expanded
    
    def _select_search_strategy(self, 
                               intent: QueryIntent,
                               entities: List[ExtractedEntity],
                               expanded_terms: List[str]) -> Dict[str, Any]:
        """
        Select optimal search strategy based on query analysis.
        
        Returns:
            Dictionary with search strategy configuration
        """
        strategy = {
            'primary_method': 'hybrid',
            'text_weight': 0.3,
            'match_count': 10,
            'rerank': True,
            'use_hyde': False,
            'multi_query': False
        }
        
        # Adjust based on intent
        if intent in [QueryIntent.STATUS_UPDATE, QueryIntent.ACTION_TRACKING]:
            # Recent, specific information needed
            strategy['text_weight'] = 0.5
            strategy['match_count'] = 15
            strategy['filters'] = {'recency_boost': True}
            
        elif intent in [QueryIntent.STRATEGIC_ANALYSIS, QueryIntent.MARKET_INTELLIGENCE]:
            # Broad, conceptual search needed
            strategy['primary_method'] = 'semantic'
            strategy['text_weight'] = 0.2
            strategy['match_count'] = 20
            strategy['use_hyde'] = True  # Generate hypothetical answer for better retrieval
            
        elif intent in [QueryIntent.TECHNICAL_SPEC, QueryIntent.COMPLIANCE_CHECK]:
            # Exact matching more important
            strategy['text_weight'] = 0.7
            strategy['match_count'] = 10
            
        elif intent == QueryIntent.FINANCIAL_FORECAST:
            # Need multiple perspectives
            strategy['multi_query'] = True
            strategy['match_count'] = 25
        
        # Adjust based on entities
        if len(entities) > 3:
            # Complex query with multiple entities
            strategy['multi_query'] = True
            strategy['match_count'] = min(strategy['match_count'] + 10, 30)
        
        # If we have specific project/person, can be more targeted
        if any(e.entity_type in ['project_id', 'person'] for e in entities):
            strategy['match_count'] = max(strategy['match_count'] - 5, 10)
        
        return strategy
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        date_str_lower = date_str.lower()
        now = datetime.now()
        
        if date_str_lower == 'today':
            return now.date()
        elif date_str_lower == 'yesterday':
            return (now - timedelta(days=1)).date()
        elif date_str_lower == 'tomorrow':
            return (now + timedelta(days=1)).date()
        elif 'next' in date_str_lower:
            # Simple next week/month parsing
            if 'week' in date_str_lower:
                return (now + timedelta(weeks=1)).date()
            elif 'month' in date_str_lower:
                return (now + timedelta(days=30)).date()
        elif 'last' in date_str_lower:
            if 'week' in date_str_lower:
                return (now - timedelta(weeks=1)).date()
            elif 'month' in date_str_lower:
                return (now - timedelta(days=30)).date()
        
        # Try standard date parsing
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return now.date()  # Default to today if can't parse
    
    def _parse_money(self, money_str: str) -> float:
        """Parse money string to float value."""
        # Remove currency symbols and commas
        cleaned = money_str.replace('$', '').replace(',', '').strip()
        
        # Handle K, M, B suffixes
        multiplier = 1
        if cleaned.endswith('K'):
            multiplier = 1000
            cleaned = cleaned[:-1]
        elif cleaned.endswith('M'):
            multiplier = 1000000
            cleaned = cleaned[:-1]
        elif cleaned.endswith('B'):
            multiplier = 1000000000
            cleaned = cleaned[:-1]
        
        try:
            return float(cleaned) * multiplier
        except ValueError:
            return 0.0


# Convenience function for quick processing
async def process_query(query: str, context: Optional[Dict] = None) -> ProcessedQuery:
    """
    Quick function to process a query.
    
    Args:
        query: The user's query
        context: Optional context information
        
    Returns:
        ProcessedQuery object with all extracted information
    """
    processor = QueryProcessor()
    return await processor.process_query(query, context)