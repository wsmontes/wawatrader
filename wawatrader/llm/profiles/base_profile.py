"""
Trading profile components.

Defines trader personality, risk tolerance, and decision-making style.
"""

from typing import Dict, Any
from ..components.base import PromptComponent, QueryContext


class TradingProfileComponent(PromptComponent):
    """
    Describes trader personality and risk preferences.
    
    Different profiles have different confidence thresholds,
    risk tolerance, and decision-making styles.
    """
    
    PROFILES = {
        'conservative': {
            'name': 'Conservative Investor',
            'risk_tolerance': 'LOW',
            'decision_style': 'Cautious, requires strong confirmation',
            'hold_preference': 'Prefer HOLD over risky action',
            'min_confidence_buy': 75,
            'min_confidence_sell': 70,
            'description': 'Focus on capital preservation and high-probability trades',
        },
        'moderate': {
            'name': 'Balanced Trader',
            'risk_tolerance': 'MEDIUM',
            'decision_style': 'Evidence-based with reasonable risk acceptance',
            'hold_preference': 'Use HOLD when signals are mixed',
            'min_confidence_buy': 65,
            'min_confidence_sell': 60,
            'description': 'Balance risk and reward with systematic approach',
        },
        'aggressive': {
            'name': 'Aggressive Trader',
            'risk_tolerance': 'HIGH',
            'decision_style': 'Quick decisions, accept volatility for returns',
            'hold_preference': 'Prefer action over waiting',
            'min_confidence_buy': 50,
            'min_confidence_sell': 45,
            'description': 'Maximum returns with corresponding risk acceptance',
        },
        'rotator': {
            'name': 'Active Capital Rotator',
            'risk_tolerance': 'MEDIUM-HIGH',
            'decision_style': 'Continuously reallocate to best opportunities',
            'hold_preference': 'HOLD only if still best option, otherwise rotate',
            'min_confidence_buy': 60,
            'min_confidence_sell': 40,  # Lower bar for SELL to enable rotation
            'description': 'Prioritize portfolio rotation over buy-and-hold',
            'special_rules': [
                'When evaluating existing positions, prioritize SELL decisions',
                'Compare positions against each other, not just absolute merit',
                'Small profits are valid - rotate capital early and often',
                'Don\'t marry positions - treat portfolio as liquid capital pool',
            ]
        },
        'momentum': {
            'name': 'Momentum Trader',
            'risk_tolerance': 'HIGH',
            'decision_style': 'Chase strong trends, exit weak momentum',
            'hold_preference': 'Exit when momentum fades',
            'min_confidence_buy': 55,
            'min_confidence_sell': 50,
            'description': 'Follow strength, avoid weakness',
            'special_rules': [
                'Buy breakouts with strong volume confirmation',
                'Sell on first signs of momentum weakening',
                'Focus on relative strength vs market',
            ]
        },
        'value': {
            'name': 'Value Investor',
            'risk_tolerance': 'LOW-MEDIUM',
            'decision_style': 'Buy oversold quality, sell overbought',
            'hold_preference': 'Hold for mean reversion',
            'min_confidence_buy': 70,
            'min_confidence_sell': 65,
            'description': 'Contrarian approach seeking mispricing',
            'special_rules': [
                'Buy when RSI < 30 with solid fundamentals',
                'Sell when RSI > 70 regardless of trend',
                'Patient with losers if fundamentals intact',
            ]
        },
    }
    
    def __init__(self, profile: str, **kwargs):
        super().__init__(**kwargs)
        self.profile = profile
        self.priority = 9
    
    def render(self) -> str:
        config = self.PROFILES.get(self.profile, self.PROFILES['moderate'])
        
        output = f"""
🎯 TRADING PROFILE: {config['name']}
{'=' * 70}
Strategy: {config['description']}
Risk Tolerance: {config['risk_tolerance']}
Decision Style: {config['decision_style']}
HOLD Preference: {config['hold_preference']}
Min Confidence Thresholds: BUY ≥{config['min_confidence_buy']}%, SELL ≥{config['min_confidence_sell']}%
"""
        
        # Add special rules if they exist
        if 'special_rules' in config:
            output += "\n⚠️  PROFILE-SPECIFIC RULES:\n"
            for i, rule in enumerate(config['special_rules'], 1):
                output += f"   {i}. {rule}\n"
        
        return output + "\n"
    
    def get_min_confidence(self, action: str) -> int:
        """
        Get minimum confidence threshold for an action.
        
        Args:
            action: 'buy' or 'sell'
        
        Returns:
            Minimum confidence percentage
        """
        config = self.PROFILES.get(self.profile, self.PROFILES['moderate'])
        
        if action.lower() == 'buy':
            return config['min_confidence_buy']
        elif action.lower() == 'sell':
            return config['min_confidence_sell']
        else:
            return config['min_confidence_buy']  # Default
    
    def is_relevant(self, context: QueryContext) -> bool:
        """Profiles are always relevant"""
        return True
