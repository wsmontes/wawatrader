"""
Overnight Analysis Component

Renders overnight deep analysis results for LLM context.
Shows the iterative analyst's findings from market close.
"""

from typing import Dict, Any, Optional
from .base import PromptComponent


class OvernightAnalysisComponent(PromptComponent):
    """
    Renders overnight analysis results.
    
    This component shows the LLM what our overnight deep analysis
    discovered, including:
    - Final recommendation (BUY/SELL/HOLD)
    - Detailed reasoning
    - Number of iterations performed
    - Analysis depth and confidence
    
    This gives the LLM morning context to either:
    1. Confirm the overnight recommendation with fresh data
    2. Update the recommendation if conditions changed overnight
    """
    
    name = "overnight_analysis"
    category = "context"
    priority = 85  # Higher than technical (80) - show overnight analysis first
    
    def __init__(self, overnight_data: Dict[str, Any]):
        """
        Initialize with overnight analysis results.
        
        Args:
            overnight_data: Dictionary containing overnight analysis for a symbol
                Expected structure:
                {
                    'symbol': 'AAPL',
                    'final_recommendation': 'SELL',
                    'reasoning': '...',
                    'iterations': 3,
                    'confidence_level': 'high',
                    'analyzed_at': '2024-01-15 20:30:00'
                }
        """
        self.overnight_data = overnight_data
    
    def render(self) -> str:
        """
        Render overnight analysis as formatted text.
        
        Returns:
            Formatted string with overnight analysis details
        """
        symbol = self.overnight_data.get('symbol', 'Unknown')
        recommendation = self.overnight_data.get('final_recommendation', 'HOLD')
        reasoning = self.overnight_data.get('reasoning', 'No reasoning provided')
        iterations = self.overnight_data.get('iterations', 1)
        confidence = self.overnight_data.get('confidence_level', 'medium')
        analyzed_at = self.overnight_data.get('analyzed_at', 'Unknown time')
        
        output = []
        output.append("## OVERNIGHT DEEP ANALYSIS")
        output.append("")
        output.append(f"**Symbol**: {symbol}")
        output.append(f"**Analysis Time**: {analyzed_at}")
        output.append(f"**Iterations**: {iterations} (iterative refinement)")
        output.append(f"**Confidence**: {confidence.upper()}")
        output.append("")
        output.append(f"**Overnight Recommendation**: {recommendation}")
        output.append("")
        output.append("**Reasoning**:")
        output.append(reasoning)
        output.append("")
        output.append("---")
        output.append("**Your Task**: Review this overnight analysis against fresh market data.")
        output.append("- If conditions haven't changed, CONFIRM the recommendation")
        output.append("- If new data contradicts it, UPDATE with current assessment")
        output.append("- Explain any changes from overnight to morning")
        output.append("")
        
        return "\n".join(output)
    
    def validate(self) -> bool:
        """
        Validate overnight data structure.
        
        Returns:
            True if data is valid, False otherwise
        """
        required_fields = ['symbol', 'final_recommendation']
        return all(field in self.overnight_data for field in required_fields)
    
    def get_token_estimate(self) -> int:
        """
        Estimate token count for this component.
        
        Returns:
            Estimated number of tokens
        """
        # Header + metadata: ~50 tokens
        # Reasoning: estimate 4 chars per token
        reasoning_tokens = len(self.overnight_data.get('reasoning', '')) // 4
        return 50 + reasoning_tokens
