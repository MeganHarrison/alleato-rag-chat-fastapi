"""
Advanced Search Strategies for PM RAG Agent

This module implements sophisticated search strategies including HyDE, multi-query
fusion, and context-aware retrieval for the elite PM business intelligence system.

Author: Alleato AI Team
Last Updated: September 2024
Related Files:
    - intelligence/query_processor.py: Query intent classification
    - tools/search_tools.py: Base search functionality
    - core/prompts.py: System prompts
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic_ai import RunContext
from .dependencies import AgentDependencies
from .query_processor import QueryIntent, QueryProcessor
from tools.search_tools import semantic_search, hybrid_search
import asyncio
import json
from datetime import datetime, timedelta


class HyDEGenerator:
    """
    Hypothetical Document Embedding generator for improved search.
    
    Creates hypothetical answers to user queries to improve semantic search
    by bridging the vocabulary gap between questions and documents.
    """
    
    def __init__(self, deps: AgentDependencies):
        self.deps = deps
    
    async def generate_hypothetical_document(self, query: str, intent: QueryIntent) -> str:
        """
        Generate a hypothetical document that would answer the query.
        
        Args:
            query: User's original query
            intent: Classified query intent
            
        Returns:
            Hypothetical document text optimized for embedding search
        """
        # Intent-specific hypothetical document templates
        templates = {
            QueryIntent.STATUS_UPDATE: """
                Project Status Report for {context}:
                The project is currently {phase} with {completion}% complete.
                Budget status shows {budget_status} with ${amount} remaining.
                Key milestones achieved include {milestones}.
                Active risks include {risks} with mitigation strategies in place.
                Team performance metrics indicate {performance}.
                Next steps involve {next_steps}.
            """,
            
            QueryIntent.RISK_ASSESSMENT: """
                Risk Assessment Analysis for {context}:
                Critical risks identified: {critical_risks}
                Risk probability and impact matrix shows {risk_matrix}.
                Current mitigation strategies include {mitigation}.
                Residual risk exposure estimated at {exposure}.
                Early warning indicators monitored: {indicators}.
                Contingency plans prepared for {contingencies}.
            """,
            
            QueryIntent.BUDGET_TRACKING: """
                Financial Analysis Report for {context}:
                Total budget allocation: ${total_budget}
                Current spend: ${spent} ({spent_percentage}%)
                Committed costs: ${committed}
                Remaining budget: ${remaining}
                Burn rate: ${burn_rate}/month
                Cost optimization opportunities: {optimizations}
                ROI projections: {roi}
            """,
            
            QueryIntent.STRATEGIC_ANALYSIS: """
                Strategic Business Analysis for {context}:
                Market positioning assessment shows {positioning}.
                Competitive advantages include {advantages}.
                Revenue impact projected at ${revenue_impact}.
                Growth opportunities identified in {opportunities}.
                Strategic risks include {strategic_risks}.
                Recommended strategic initiatives: {initiatives}.
                Long-term sustainability factors: {sustainability}.
            """,
            
            QueryIntent.STAKEHOLDER_QUERY: """
                Stakeholder Communication Report for {context}:
                Client satisfaction metrics: {satisfaction}
                Recent stakeholder feedback includes {feedback}.
                Key concerns raised: {concerns}
                Action items for stakeholder management: {actions}.
                Relationship health indicators: {health}.
                Communication touchpoints scheduled: {touchpoints}.
            """
        }
        
        # Generate context-aware hypothetical document
        template = templates.get(intent, templates[QueryIntent.GENERAL_QUERY])
        
        # Fill template with query-specific context
        hypothetical = f"""
        Based on the query: "{query}"
        
        {template}
        
        This document contains specific details about {query} including
        relevant dates, amounts, names, and actionable insights.
        All information is current as of {datetime.now().strftime('%B %d, %Y')}.
        """
        
        return hypothetical
    
    async def generate_multiple_hypotheticals(
        self, 
        query: str, 
        intent: QueryIntent, 
        count: int = 3
    ) -> List[str]:
        """
        Generate multiple hypothetical documents for diverse retrieval.
        
        Args:
            query: User's original query
            intent: Classified query intent
            count: Number of hypothetical documents to generate
            
        Returns:
            List of hypothetical documents with different perspectives
        """
        perspectives = [
            "executive summary perspective",
            "detailed technical perspective",
            "risk and compliance perspective",
            "financial impact perspective",
            "stakeholder value perspective"
        ]
        
        hypotheticals = []
        for i in range(min(count, len(perspectives))):
            hypo = await self.generate_hypothetical_document(query, intent)
            hypo += f"\n\nWritten from {perspectives[i]}."
            hypotheticals.append(hypo)
        
        return hypotheticals


class MultiQueryFusion:
    """
    Multi-query fusion strategy for comprehensive retrieval.
    
    Generates multiple query variations and fuses results for better coverage.
    """
    
    def __init__(self, deps: AgentDependencies):
        self.deps = deps
    
    async def generate_query_variations(self, query: str, intent: QueryIntent) -> List[str]:
        """
        Generate multiple query variations for comprehensive search.
        
        Args:
            query: Original user query
            intent: Classified query intent
            
        Returns:
            List of query variations
        """
        variations = [query]  # Include original
        
        # Intent-specific query expansions
        if intent == QueryIntent.STATUS_UPDATE:
            variations.extend([
                f"{query} progress report milestones",
                f"{query} budget schedule timeline",
                f"{query} completion percentage status"
            ])
        
        elif intent == QueryIntent.RISK_ASSESSMENT:
            variations.extend([
                f"{query} risk mitigation strategies",
                f"{query} probability impact analysis",
                f"{query} contingency plans controls"
            ])
        
        elif intent == QueryIntent.BUDGET_TRACKING:
            variations.extend([
                f"{query} cost analysis financial",
                f"{query} budget variance spending",
                f"{query} ROI profitability margins"
            ])
        
        elif intent == QueryIntent.STRATEGIC_ANALYSIS:
            variations.extend([
                f"{query} competitive advantage market",
                f"{query} growth opportunities revenue",
                f"{query} strategic initiatives positioning"
            ])
        
        # Add temporal variations if relevant
        if any(word in query.lower() for word in ['recent', 'latest', 'current', 'now']):
            variations.append(f"{query} {datetime.now().strftime('%B %Y')}")
        
        # Add entity-specific variations
        entities = self._extract_entities(query)
        for entity in entities:
            variations.append(f"{entity} {query}")
        
        return list(set(variations))[:5]  # Limit to 5 unique variations
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract named entities from query."""
        entities = []
        
        # Project names (basic heuristic - capitalize words)
        words = query.split()
        for i, word in enumerate(words):
            if word[0].isupper() and word.lower() not in ['what', 'how', 'when', 'where', 'why']:
                entities.append(word)
        
        return entities
    
    async def fuse_results(
        self, 
        results_sets: List[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Fuse multiple result sets using reciprocal rank fusion.
        
        Args:
            results_sets: List of result sets from different queries
            
        Returns:
            Fused and re-ranked results
        """
        # Reciprocal Rank Fusion (RRF)
        doc_scores = {}
        k = 60  # Constant for RRF
        
        for results in results_sets:
            for rank, doc in enumerate(results, 1):
                doc_id = doc.get('chunk_id', doc.get('document_id'))
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'doc': doc,
                        'score': 0
                    }
                # RRF score calculation
                doc_scores[doc_id]['score'] += 1 / (k + rank)
        
        # Sort by fused score
        fused_results = sorted(
            doc_scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Return documents with fused scores
        return [
            {**item['doc'], 'fusion_score': item['score']}
            for item in fused_results
        ]


class ContextAwareRetrieval:
    """
    Context-aware retrieval using conversation history and business context.
    """
    
    def __init__(self, deps: AgentDependencies):
        self.deps = deps
    
    async def enhance_with_context(
        self, 
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Enhance query with conversation and business context.
        
        Args:
            query: Original query
            conversation_history: Previous conversation exchanges
            
        Returns:
            Context-enhanced query
        """
        enhanced = query
        
        # Add conversation context
        if conversation_history:
            recent_context = self._extract_conversation_context(conversation_history)
            if recent_context:
                enhanced = f"{query} (Context: {recent_context})"
        
        # Add business context if available
        if hasattr(self.deps, 'business_context'):
            business = self.deps.business_context
            if business.get('current_quarter'):
                enhanced += f" Quarter: {business['current_quarter']}"
            if business.get('priority_clients'):
                enhanced += f" Clients: {', '.join(business['priority_clients'][:2])}"
        
        # Add temporal context
        enhanced += f" As of {datetime.now().strftime('%B %Y')}"
        
        return enhanced
    
    def _extract_conversation_context(
        self, 
        history: List[Dict[str, str]]
    ) -> str:
        """Extract relevant context from conversation history."""
        # Get last 3 exchanges
        recent = history[-3:] if len(history) > 3 else history
        
        # Extract key terms
        key_terms = set()
        for exchange in recent:
            content = exchange.get('content', '')
            # Extract capitalized words (likely entities)
            words = content.split()
            for word in words:
                if word[0].isupper() and len(word) > 3:
                    key_terms.add(word)
        
        return ' '.join(list(key_terms)[:5])


class AdvancedSearchOrchestrator:
    """
    Orchestrates advanced search strategies for optimal retrieval.
    """
    
    def __init__(self, ctx: RunContext[AgentDependencies]):
        self.ctx = ctx
        self.deps = ctx.deps
        self.query_processor = QueryProcessor()
        self.hyde_generator = HyDEGenerator(self.deps)
        self.multi_query = MultiQueryFusion(self.deps)
        self.context_retrieval = ContextAwareRetrieval(self.deps)
    
    async def execute_search(
        self,
        query: str,
        strategy: str = "auto",
        conversation_history: Optional[List[Dict[str, str]]] = None,
        match_count: int = 10
    ) -> Dict[str, Any]:
        """
        Execute advanced search with selected strategy.
        
        Args:
            query: User query
            strategy: Search strategy (auto, hyde, multi_query, hybrid)
            conversation_history: Previous conversation
            match_count: Number of results to return
            
        Returns:
            Search results with metadata
        """
        # Process query
        processed = self.query_processor.process_query(query)
        intent = processed['intent']
        
        # Select strategy
        if strategy == "auto":
            strategy = self._select_strategy(intent)
        
        # Execute strategy
        if strategy == "hyde":
            results = await self._execute_hyde_search(
                query, intent, match_count
            )
        elif strategy == "multi_query":
            results = await self._execute_multi_query_search(
                query, intent, match_count
            )
        else:  # hybrid or default
            results = await self._execute_hybrid_search(
                query, match_count, conversation_history
            )
        
        return {
            'query': query,
            'strategy': strategy,
            'intent': intent.value,
            'results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _select_strategy(self, intent: QueryIntent) -> str:
        """Select optimal strategy based on intent."""
        strategy_map = {
            QueryIntent.STATUS_UPDATE: "hybrid",
            QueryIntent.RISK_ASSESSMENT: "hyde",
            QueryIntent.BUDGET_TRACKING: "multi_query",
            QueryIntent.STRATEGIC_ANALYSIS: "hyde",
            QueryIntent.STAKEHOLDER_QUERY: "hybrid",
            QueryIntent.TECHNICAL_DETAIL: "multi_query",
            QueryIntent.GENERAL_QUERY: "hybrid"
        }
        return strategy_map.get(intent, "hybrid")
    
    async def _execute_hyde_search(
        self,
        query: str,
        intent: QueryIntent,
        match_count: int
    ) -> List[Dict[str, Any]]:
        """Execute HyDE-enhanced search."""
        # Generate hypothetical documents
        hypotheticals = await self.hyde_generator.generate_multiple_hypotheticals(
            query, intent, count=3
        )
        
        # Search with each hypothetical
        all_results = []
        for hypo in hypotheticals:
            results = await semantic_search(
                self.ctx,
                hypo,
                match_count=match_count // len(hypotheticals)
            )
            all_results.append(results)
        
        # Fuse results
        fused = await self.multi_query.fuse_results(all_results)
        
        return fused[:match_count]
    
    async def _execute_multi_query_search(
        self,
        query: str,
        intent: QueryIntent,
        match_count: int
    ) -> List[Dict[str, Any]]:
        """Execute multi-query fusion search."""
        # Generate query variations
        variations = await self.multi_query.generate_query_variations(
            query, intent
        )
        
        # Search with each variation
        search_tasks = [
            hybrid_search(
                self.ctx,
                variation,
                match_count=match_count // len(variations)
            )
            for variation in variations
        ]
        
        results_sets = await asyncio.gather(*search_tasks)
        
        # Fuse results
        fused = await self.multi_query.fuse_results(results_sets)
        
        return fused[:match_count]
    
    async def _execute_hybrid_search(
        self,
        query: str,
        match_count: int,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Execute context-aware hybrid search."""
        # Enhance query with context
        enhanced_query = await self.context_retrieval.enhance_with_context(
            query, conversation_history
        )
        
        # Execute hybrid search
        results = await hybrid_search(
            self.ctx,
            enhanced_query,
            match_count=match_count,
            text_weight=0.3
        )
        
        return results


async def advanced_search(
    ctx: RunContext[AgentDependencies],
    query: str,
    strategy: str = "auto",
    conversation_history: Optional[List[Dict[str, str]]] = None,
    match_count: int = 10
) -> Dict[str, Any]:
    """
    Main entry point for advanced search functionality.
    
    Args:
        ctx: Agent runtime context
        query: User query
        strategy: Search strategy to use
        conversation_history: Previous conversation
        match_count: Number of results
        
    Returns:
        Search results with metadata
    """
    orchestrator = AdvancedSearchOrchestrator(ctx)
    return await orchestrator.execute_search(
        query, strategy, conversation_history, match_count
    )