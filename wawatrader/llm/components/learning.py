"""
Learning Insights Component

Renders yesterday's performance and discovered patterns for LLM context.
This closes the learning feedback loop by showing the LLM what worked/didn't work.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from .base import PromptComponent


class LearningInsightsComponent(PromptComponent):
    """
    Renders learning insights from trading history.
    
    Shows the LLM:
    - Yesterday's performance (win rate, P&L, trade count)
    - Discovered profitable patterns
    - Lessons learned from recent trades
    - What to focus on today
    
    This helps the LLM learn from past decisions and improve over time.
    """
    
    name = "learning_insights"
    category = "context"
    priority = 90  # Highest priority - show learning first
    
    def __init__(self, insights_data: Dict[str, Any]):
        """
        Initialize with learning insights.
        
        Args:
            insights_data: Dictionary containing learning insights
                Expected structure:
                {
                    'yesterday': {
                        'date': '2025-10-26',
                        'total_trades': 5,
                        'winning_trades': 3,
                        'losing_trades': 2,
                        'win_rate': 0.60,
                        'total_pnl': 125.50,
                        'best_trade': 75.00,
                        'worst_trade': -25.00
                    },
                    'patterns': [
                        {
                            'pattern_type': 'time_of_day',
                            'description': 'Morning trades (10-11 AM) show 75% win rate',
                            'confidence': 0.75,
                            'sample_size': 12
                        }
                    ],
                    'lessons': [
                        'High RSI (>70) in downtrend led to losses',
                        'Breakout patterns with volume worked well'
                    ],
                    'focus_areas': [
                        'Look for morning setups',
                        'Avoid overbought conditions in bearish markets'
                    ]
                }
        """
        self.insights = insights_data
    
    def render(self) -> str:
        """
        Render learning insights as formatted text.
        
        Returns:
            Formatted string with learning insights
        """
        output = []
        output.append("## YOUR PERFORMANCE & LEARNING INSIGHTS")
        output.append("")
        output.append("*Learn from your past decisions to make better trades today.*")
        output.append("")
        
        # Yesterday's Performance
        if 'yesterday' in self.insights and self.insights['yesterday']:
            output.append(self._render_yesterday_performance())
        
        # Discovered Patterns
        if 'patterns' in self.insights and self.insights['patterns']:
            output.append(self._render_patterns())
        
        # Lessons Learned
        if 'lessons' in self.insights and self.insights['lessons']:
            output.append(self._render_lessons())
        
        # Focus Areas for Today
        if 'focus_areas' in self.insights and self.insights['focus_areas']:
            output.append(self._render_focus_areas())
        
        output.append("")
        output.append("---")
        output.append("**Your Task**: Use these insights to inform your decision-making today.")
        output.append("- Build on what worked")
        output.append("- Avoid patterns that led to losses")
        output.append("- Apply learned lessons to current market conditions")
        output.append("")
        
        return "\n".join(output)
    
    def _render_yesterday_performance(self) -> str:
        """Render yesterday's performance summary"""
        yesterday = self.insights['yesterday']
        
        lines = []
        lines.append("### Yesterday's Performance")
        lines.append("")
        lines.append(f"**Date**: {yesterday.get('date', 'Unknown')}")
        lines.append(f"**Total Trades**: {yesterday.get('total_trades', 0)}")
        
        if yesterday.get('total_trades', 0) > 0:
            lines.append(f"**Win Rate**: {yesterday.get('win_rate', 0):.1%}")
            lines.append(f"**P&L**: ${yesterday.get('total_pnl', 0):+.2f}")
            lines.append(f"**Best Trade**: ${yesterday.get('best_trade', 0):+.2f}")
            lines.append(f"**Worst Trade**: ${yesterday.get('worst_trade', 0):+.2f}")
            
            # Performance assessment
            win_rate = yesterday.get('win_rate', 0)
            pnl = yesterday.get('total_pnl', 0)
            
            if win_rate >= 0.7 and pnl > 0:
                assessment = "🌟 **Excellent day!** High win rate and positive P&L."
            elif win_rate >= 0.5 and pnl > 0:
                assessment = "✅ **Good day.** Profitable with solid win rate."
            elif pnl > 0:
                assessment = "💰 **Profitable.** Win rate could improve, but made money."
            elif pnl == 0:
                assessment = "➡️ **Break-even.** No gains or losses."
            else:
                assessment = "⚠️ **Losing day.** Review what went wrong."
            
            lines.append("")
            lines.append(assessment)
        else:
            lines.append("")
            lines.append("*No trades executed yesterday.*")
        
        lines.append("")
        return "\n".join(lines)
    
    def _render_patterns(self) -> str:
        """Render discovered profitable patterns"""
        patterns = self.insights['patterns']
        
        lines = []
        lines.append("### Discovered Patterns")
        lines.append("")
        lines.append("*Patterns that showed consistent profitability:*")
        lines.append("")
        
        for i, pattern in enumerate(patterns[:5], 1):  # Show top 5
            pattern_type = pattern.get('pattern_type', 'unknown')
            description = pattern.get('description', 'No description')
            confidence = pattern.get('confidence', 0)
            sample_size = pattern.get('sample_size', 0)
            
            # Icon based on pattern type
            icon = self._get_pattern_icon(pattern_type)
            
            lines.append(f"{i}. {icon} **{description}**")
            lines.append(f"   - Confidence: {confidence:.0%} (based on {sample_size} trades)")
            
            # Add recommendation if available
            if 'recommendation' in pattern:
                lines.append(f"   - *{pattern['recommendation']}*")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _render_lessons(self) -> str:
        """Render lessons learned"""
        lessons = self.insights['lessons']
        
        lines = []
        lines.append("### Lessons Learned")
        lines.append("")
        lines.append("*Key takeaways from recent trades:*")
        lines.append("")
        
        for i, lesson in enumerate(lessons[:5], 1):  # Show top 5
            lines.append(f"{i}. {lesson}")
        
        lines.append("")
        return "\n".join(lines)
    
    def _render_focus_areas(self) -> str:
        """Render focus areas for today"""
        focus_areas = self.insights['focus_areas']
        
        lines = []
        lines.append("### Focus Areas for Today")
        lines.append("")
        lines.append("*What to pay attention to:*")
        lines.append("")
        
        for i, area in enumerate(focus_areas[:5], 1):  # Show top 5
            lines.append(f"- {area}")
        
        lines.append("")
        return "\n".join(lines)
    
    def _get_pattern_icon(self, pattern_type: str) -> str:
        """Get icon for pattern type"""
        icons = {
            'time_of_day': '🕐',
            'market_regime': '📊',
            'confidence_level': '🎯',
            'technical_setup': '📈',
            'momentum': '🚀',
            'mean_reversion': '↩️',
            'breakout': '💥',
            'support_resistance': '🏛️'
        }
        return icons.get(pattern_type, '📌')
    
    def validate(self) -> bool:
        """
        Validate insights data structure.
        
        Returns:
            True if data is valid, False otherwise
        """
        # At minimum, should have some insights
        return bool(self.insights and any([
            self.insights.get('yesterday'),
            self.insights.get('patterns'),
            self.insights.get('lessons'),
            self.insights.get('focus_areas')
        ]))
    
    def get_token_estimate(self) -> int:
        """
        Estimate token count for this component.
        
        Returns:
            Estimated token count
        """
        # Rough estimate: ~300-500 tokens depending on content
        base_tokens = 200
        
        if self.insights.get('yesterday'):
            base_tokens += 100
        
        if self.insights.get('patterns'):
            base_tokens += len(self.insights['patterns']) * 50
        
        if self.insights.get('lessons'):
            base_tokens += len(self.insights['lessons']) * 20
        
        if self.insights.get('focus_areas'):
            base_tokens += len(self.insights['focus_areas']) * 15
        
        return base_tokens
