"""
Context components: Who/What/Why of the query.

These components provide high-level context about the query type,
what triggered it, and the trader's profile.
"""

from typing import Dict, Any
from .base import PromptComponent, QueryContext


class QueryTypeComponent(PromptComponent):
    """
    Declares what type of analysis is needed.
    
    This component renders the query type header, making it clear
    to the LLM what kind of decision or analysis is required.
    """
    
    QUERY_TYPES = {
        'NEW_OPPORTUNITY': {
            'emoji': '🎯',
            'title': 'NEW OPPORTUNITY EVALUATION',
            'description': 'Evaluating potential BUY entry for new position',
        },
        'POSITION_REVIEW': {
            'emoji': '💼',
            'title': 'POSITION REVIEW',
            'description': 'Evaluating existing holding for SELL/HOLD decision',
        },
        'PORTFOLIO_AUDIT': {
            'emoji': '📊',
            'title': 'PORTFOLIO AUDIT',
            'description': 'Ranking all holdings to identify strongest/weakest',
        },
        'COMPARATIVE_ANALYSIS': {
            'emoji': '⚖️',
            'title': 'COMPARATIVE ANALYSIS',
            'description': 'Side-by-side comparison of multiple stocks',
        },
        'TRADE_POSTMORTEM': {
            'emoji': '📝',
            'title': 'TRADE POSTMORTEM',
            'description': 'Analyzing why a trade succeeded or failed',
        },
        'MARKET_REGIME': {
            'emoji': '🌍',
            'title': 'MARKET REGIME ANALYSIS',
            'description': 'Assessing current market environment and trends',
        },
        'SECTOR_ROTATION': {
            'emoji': '🔄',
            'title': 'SECTOR ROTATION ANALYSIS',
            'description': 'Identifying sector trends for capital allocation',
        },
        'RISK_ASSESSMENT': {
            'emoji': '⚠️',
            'title': 'PORTFOLIO RISK ASSESSMENT',
            'description': 'Evaluating portfolio risk exposure and vulnerabilities',
        },
    }
    
    def __init__(self, query_type: str, **kwargs):
        super().__init__(**kwargs)
        self.query_type = query_type
        self.priority = 10  # Always show first
    
    def render(self) -> str:
        config = self.QUERY_TYPES.get(self.query_type, {
            'emoji': '📋',
            'title': 'ANALYSIS',
            'description': 'General market analysis'
        })
        
        emoji = config.get('emoji', '📋')
        title = config.get('title', 'ANALYSIS')
        desc = config.get('description', '')
        
        return f"""
{emoji} QUERY TYPE: {title}
{'=' * 70}
{desc}
"""


class TriggerComponent(PromptComponent):
    """
    Explains what triggered this query.
    
    Provides context about why the analysis is being performed now,
    which can influence the urgency and focus of the decision.
    """
    
    TRIGGERS = {
        'SCHEDULED_CYCLE': 'Regular 5-minute trading cycle',
        'CAPITAL_CONSTRAINT': 'Need to free capital (buying power < 5% of portfolio)',
        'PRICE_ALERT': 'Stock reached price target or stop-loss level',
        'TECHNICAL_SIGNAL': 'Technical indicator generated buy/sell signal',
        'NEWS_EVENT': 'Breaking news event detected',
        'USER_REQUEST': 'Manual analysis requested by user',
        'POSITION_LOSS': 'Position hit loss threshold',
        'POSITION_PROFIT': 'Position hit profit target',
        'VOLATILITY_SPIKE': 'Unusual volatility detected',
    }
    
    def __init__(self, trigger: str, **kwargs):
        super().__init__(**kwargs)
        self.trigger = trigger
        self.priority = 9
    
    def render(self) -> str:
        description = self.TRIGGERS.get(self.trigger, self.trigger)
        
        # Add urgency indicator for certain triggers
        urgency = ""
        if self.trigger in ['CAPITAL_CONSTRAINT', 'POSITION_LOSS', 'PRICE_ALERT']:
            urgency = " ⚡ URGENT"
        
        return f"🔔 TRIGGER: {description}{urgency}\n"
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Triggers are always relevant to provide context"""
        return True
