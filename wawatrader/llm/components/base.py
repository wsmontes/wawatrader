"""
Base classes for modular prompt system.

This module provides the foundation for composable, context-aware LLM prompts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class QueryContext:
    """
    Complete context for an LLM query.
    
    This defines WHAT we want to ask the LLM and HOW to ask it.
    The PromptBuilder uses this to select and configure components.
    
    Attributes:
        query_type: Type of analysis (NEW_OPPORTUNITY, POSITION_REVIEW, etc.)
        trigger: What caused this query (SCHEDULED_CYCLE, CAPITAL_CONSTRAINT, etc.)
        profile: Trading profile (conservative, aggressive, rotator, etc.)
        primary_symbol: Main stock being analyzed
        comparison_symbols: Additional symbols for comparative analysis
        portfolio_state: Overall portfolio information
        include_news: Whether to include news data
        include_market_regime: Whether to include broader market context
        detail_level: How much detail to include (minimal, standard, detailed)
        expected_format: Expected response structure
        allow_data_requests: Whether LLM can request additional data
        overnight_analysis: Optional overnight deep analysis results
        extra_data: Additional context-specific data
    """
    query_type: str
    trigger: str
    profile: str
    primary_symbol: Optional[str] = None
    comparison_symbols: Optional[List[str]] = None
    portfolio_state: Optional[Dict[str, Any]] = None
    include_news: bool = True
    include_market_regime: bool = False
    detail_level: str = 'standard'  # minimal, standard, detailed
    expected_format: str = 'STANDARD_DECISION'
    allow_data_requests: bool = False
    overnight_analysis: Optional[Dict[str, Any]] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    # Query type constants
    NEW_OPPORTUNITY = 'NEW_OPPORTUNITY'
    POSITION_REVIEW = 'POSITION_REVIEW'
    PORTFOLIO_AUDIT = 'PORTFOLIO_AUDIT'
    COMPARATIVE_ANALYSIS = 'COMPARATIVE_ANALYSIS'
    TRADE_POSTMORTEM = 'TRADE_POSTMORTEM'
    MARKET_REGIME = 'MARKET_REGIME'
    SECTOR_ROTATION = 'SECTOR_ROTATION'
    RISK_ASSESSMENT = 'RISK_ASSESSMENT'
    
    # Trigger constants
    SCHEDULED_CYCLE = 'SCHEDULED_CYCLE'
    CAPITAL_CONSTRAINT = 'CAPITAL_CONSTRAINT'
    PRICE_ALERT = 'PRICE_ALERT'
    TECHNICAL_SIGNAL = 'TECHNICAL_SIGNAL'
    NEWS_EVENT = 'NEWS_EVENT'
    USER_REQUEST = 'USER_REQUEST'
    
    # Response format constants
    STANDARD_DECISION = 'STANDARD_DECISION'
    RANKING = 'RANKING'
    COMPARISON = 'COMPARISON'
    DATA_REQUEST = 'DATA_REQUEST'


class PromptComponent(ABC):
    """
    Base class for all prompt components.
    
    Components are modular building blocks that render specific sections
    of a prompt. They can be combined in different ways to create
    context-aware prompts.
    
    Attributes:
        data: Component-specific data (technical indicators, position info, etc.)
        priority: Rendering priority (higher = shown first in prompt)
        context: Query context (set by PromptBuilder)
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None, priority: int = 5):
        """
        Initialize component.
        
        Args:
            data: Component-specific data
            priority: Rendering priority (1-10, higher = more important)
        """
        self.data = data or {}
        self.priority = priority
        self.context: Optional[QueryContext] = None
    
    def set_context(self, context: QueryContext):
        """
        Set the query context.
        
        Args:
            context: Query context from PromptBuilder
        """
        self.context = context
    
    @abstractmethod
    def render(self) -> str:
        """
        Convert component data to prompt text.
        
        Returns:
            Rendered prompt section as string
        """
        pass
    
    def is_relevant(self, context: QueryContext) -> bool:
        """
        Check if this component should be included for this query.
        
        Args:
            context: Query context to check against
        
        Returns:
            True if component is relevant, False otherwise
        """
        return True
    
    def validate_data(self) -> bool:
        """
        Check if component has required data.
        
        Returns:
            True if data is valid, False otherwise
        """
        return bool(self.data)
