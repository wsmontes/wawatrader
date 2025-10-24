"""
Prompt builder: Assembles prompts from components based on context.

The PromptBuilder is the core of the modular prompt system. It:
1. Selects relevant components based on QueryContext
2. Configures components with appropriate data
3. Sorts components by priority
4. Renders final prompt by combining component outputs
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from ..components.base import PromptComponent, QueryContext
from ..components.context import QueryTypeComponent, TriggerComponent
from ..components.data import (
    TechnicalDataComponent,
    PositionDataComponent,
    PortfolioSummaryComponent,
    NewsComponent,
)
from ..components.instructions import TaskInstructionComponent, ResponseFormatComponent
from ..components.overnight import OvernightAnalysisComponent
from ..profiles.base_profile import TradingProfileComponent


class PromptBuilder:
    """
    Assembles prompts from components based on context.
    
    Usage:
        builder = PromptBuilder()
        
        context = QueryContext(
            query_type='POSITION_REVIEW',
            trigger='CAPITAL_CONSTRAINT',
            profile='rotator',
            primary_symbol='AAPL',
        )
        
        data = {
            'technical': {...},
            'position': {...},
            'portfolio': {...},
        }
        
        prompt = builder.build(context, data)
    """
    
    def __init__(self):
        """Initialize prompt builder"""
        logger.debug("PromptBuilder initialized")
    
    def build(self, context: QueryContext, data: Dict[str, Any]) -> str:
        """
        Build prompt from context and data.
        
        Args:
            context: Query context defining what to ask
            data: All available data (technical, portfolio, news, etc.)
        
        Returns:
            Complete prompt string ready for LLM
        """
        try:
            # 1. Select and instantiate relevant components
            components = self._select_components(context, data)
            
            # 2. Set context on all components
            for component in components:
                component.set_context(context)
            
            # 3. Filter by relevance
            relevant = [c for c in components if c.is_relevant(context)]
            
            if not relevant:
                logger.warning("No relevant components found for context")
                return ""
            
            # 4. Sort by priority (higher = more important = shown first)
            relevant.sort(key=lambda c: c.priority, reverse=True)
            
            # 5. Render each component
            sections = []
            for component in relevant:
                try:
                    rendered = component.render()
                    if rendered and rendered.strip():
                        sections.append(rendered.strip())
                except Exception as e:
                    logger.warning(f"Component {component.__class__.__name__} failed to render: {e}")
                    continue
            
            if not sections:
                logger.error("No components rendered successfully")
                return ""
            
            # 6. Assemble final prompt
            prompt = "\n\n".join(sections)
            
            # Log stats
            logger.debug(f"Built prompt: {len(sections)} sections, {len(prompt)} chars")
            
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to build prompt: {e}")
            raise
    
    def _select_components(
        self,
        context: QueryContext,
        data: Dict[str, Any]
    ) -> List[PromptComponent]:
        """
        Choose which components to include based on query type and data.
        
        Args:
            context: Query context
            data: Available data
        
        Returns:
            List of instantiated components
        """
        components = []
        
        # === ALWAYS INCLUDE THESE ===
        
        # 1. Query type (what we're asking)
        components.append(QueryTypeComponent(context.query_type))
        
        # 2. Trigger (why we're asking now)
        components.append(TriggerComponent(context.trigger))
        
        # 3. Trading profile (how to make decisions)
        components.append(TradingProfileComponent(context.profile))
        
        # === CONDITIONALLY INCLUDE DATA COMPONENTS ===
        
        # Overnight analysis (if available) - HIGH PRIORITY
        # Show this BEFORE technical data so LLM sees deep analysis first
        if context.overnight_analysis:
            components.append(OvernightAnalysisComponent(context.overnight_analysis))
        
        # Technical data (for stock-specific queries)
        if context.query_type in [
            QueryContext.NEW_OPPORTUNITY,
            QueryContext.POSITION_REVIEW,
            QueryContext.COMPARATIVE_ANALYSIS,
        ]:
            if 'technical' in data and data['technical']:
                components.append(TechnicalDataComponent(data['technical']))
        
        # Position data (for position reviews only)
        if context.query_type == QueryContext.POSITION_REVIEW:
            if 'position' in data and data['position']:
                components.append(PositionDataComponent(data['position']))
        
        # Portfolio summary (for portfolio-level decisions)
        if context.query_type in [
            QueryContext.PORTFOLIO_AUDIT,
            QueryContext.RISK_ASSESSMENT,
        ] or context.trigger == QueryContext.CAPITAL_CONSTRAINT:
            if 'portfolio' in data and data['portfolio']:
                components.append(PortfolioSummaryComponent(data['portfolio']))
        
        # News (if enabled and relevant)
        if context.include_news:
            if 'news' in data and data['news']:
                components.append(NewsComponent(data['news']))
        
        # === ALWAYS INCLUDE INSTRUCTIONS ===
        
        # Task instructions (what to do)
        components.append(TaskInstructionComponent(context.query_type))
        
        # Response format (how to respond)
        components.append(ResponseFormatComponent(context.expected_format))
        
        logger.debug(f"Selected {len(components)} components for {context.query_type}")
        
        return components
    
    def preview_components(self, context: QueryContext, data: Dict[str, Any]) -> List[str]:
        """
        Preview which components would be used (for debugging).
        
        Args:
            context: Query context
            data: Available data
        
        Returns:
            List of component class names
        """
        components = self._select_components(context, data)
        
        for component in components:
            component.set_context(context)
        
        relevant = [c for c in components if c.is_relevant(context)]
        relevant.sort(key=lambda c: c.priority, reverse=True)
        
        return [
            f"{c.__class__.__name__} (priority={c.priority})"
            for c in relevant
        ]
