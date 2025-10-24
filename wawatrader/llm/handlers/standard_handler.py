"""
Handler for STANDARD_DECISION format responses.
"""

from typing import Dict, Any, List
from loguru import logger
from .base_handler import ResponseHandler


class StandardDecisionHandler(ResponseHandler):
    """
    Handler for standard trading decision responses.
    
    Expected format:
    {
        "sentiment": "bullish|bearish|neutral",
        "confidence": 0-100,
        "action": "buy|sell|hold",
        "reasoning": "Detailed explanation...",
        "risk_factors": ["[SEVERITY]: risk description", ...]
    }
    """
    
    def __init__(self):
        super().__init__()
        self.required_fields = ['sentiment', 'confidence', 'action', 'reasoning']
        self.optional_fields = ['risk_factors', 'price_targets', 'stop_loss', 'timeframe']
    
    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """Validate standard decision structure."""
        # Check required fields
        if not self._check_required_fields(data):
            missing = [f for f in self.required_fields if f not in data]
            logger.warning(f"Missing required fields: {missing}")
            return False
        
        # Validate types
        if not isinstance(data.get('sentiment'), str):
            logger.warning("Invalid sentiment type")
            return False
        
        if not isinstance(data.get('action'), str):
            logger.warning("Invalid action type")
            return False
        
        if not isinstance(data.get('reasoning'), str):
            logger.warning("Invalid reasoning type")
            return False
        
        # Confidence can be int or float
        try:
            float(data.get('confidence', 0))
        except (ValueError, TypeError):
            logger.warning("Invalid confidence type")
            return False
        
        return True
    
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and normalize standard decision data."""
        sanitized = {
            'sentiment': self._normalize_sentiment(data['sentiment']),
            'confidence': self._clamp_confidence(data['confidence']),
            'action': self._normalize_action(data['action']),
            'reasoning': str(data['reasoning']).strip(),
        }
        
        # Handle optional fields
        if 'risk_factors' in data:
            sanitized['risk_factors'] = self._sanitize_risk_factors(data['risk_factors'])
        else:
            sanitized['risk_factors'] = []
        
        if 'price_targets' in data:
            sanitized['price_targets'] = data['price_targets']
        
        if 'stop_loss' in data:
            try:
                sanitized['stop_loss'] = float(data['stop_loss'])
            except (ValueError, TypeError):
                pass
        
        if 'timeframe' in data:
            sanitized['timeframe'] = str(data['timeframe'])
        
        return sanitized
    
    def _sanitize_risk_factors(self, risk_factors: Any) -> List[str]:
        """
        Sanitize risk factors list.
        
        Args:
            risk_factors: Raw risk factors (list or string)
        
        Returns:
            List of sanitized risk factor strings
        """
        if isinstance(risk_factors, str):
            # Single string - split by common delimiters
            risk_factors = [risk_factors]
        
        if not isinstance(risk_factors, list):
            return []
        
        sanitized = []
        for risk in risk_factors:
            risk_str = str(risk).strip()
            if risk_str:
                sanitized.append(risk_str)
        
        return sanitized
    
    def _calculate_quality(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate quality scores for standard decision.
        
        Scores:
        - decisiveness: How clear and actionable is the decision?
        - specificity: Does reasoning include specific levels/targets?
        - risk_awareness: Are risks properly identified and categorized?
        - reasoning_depth: Is reasoning detailed and substantive?
        - overall: Weighted average
        """
        scores = {}
        
        # 1. Decisiveness (0-100)
        action = data['action']
        confidence = data['confidence']
        
        if action in ['buy', 'sell']:
            # Strong action - good
            decisiveness = 70 + min(30, confidence / 3.33)
        elif action == 'hold':
            # HOLD should have lower confidence or be justified
            if confidence < 60:
                decisiveness = 60  # Uncertain HOLD is OK
            else:
                decisiveness = 40  # High-confidence HOLD is often indecisive
        else:
            decisiveness = 50
        
        scores['decisiveness'] = round(decisiveness, 1)
        
        # 2. Specificity (0-100)
        reasoning = data['reasoning'].lower()
        specificity = 0
        
        # Check for specific price levels
        price_terms = ['$', 'support', 'resistance', 'target', 'stop', 'level']
        specificity += sum(10 for term in price_terms if term in reasoning)
        
        # Check for specific indicators
        indicator_terms = ['rsi', 'macd', 'sma', 'ema', 'volume', 'atr', 'bollinger']
        specificity += sum(8 for term in indicator_terms if term in reasoning)
        
        # Check for timeframes
        timeframe_terms = ['day', 'week', 'month', 'short-term', 'medium-term', 'long-term']
        specificity += sum(5 for term in timeframe_terms if term in reasoning)
        
        scores['specificity'] = min(100, specificity)
        
        # 3. Risk Awareness (0-100)
        risk_factors = data.get('risk_factors', [])
        
        if not risk_factors:
            risk_score = 20  # No risks identified - poor
        else:
            risk_score = 40  # Base score for having risks
            
            # Bonus for severity tags
            severity_tags = ['[CRITICAL]', '[HIGH]', '[MEDIUM]', '[LOW]']
            tagged_risks = sum(1 for risk in risk_factors 
                             if any(tag in risk for tag in severity_tags))
            risk_score += min(40, tagged_risks * 20)
            
            # Bonus for multiple risks (shows comprehensive analysis)
            risk_score += min(20, len(risk_factors) * 5)
        
        scores['risk_awareness'] = min(100, risk_score)
        
        # 4. Reasoning Depth (0-100)
        reasoning_length = len(data['reasoning'])
        
        if reasoning_length < 50:
            depth = 20  # Too brief
        elif reasoning_length < 150:
            depth = 50  # Minimal
        elif reasoning_length < 300:
            depth = 70  # Good
        else:
            depth = 90  # Comprehensive
        
        # Penalty for generic phrases
        generic_phrases = [
            'market volatility', 'uncertain', 'mixed signals', 
            'wait and see', 'monitor closely', 'depends on'
        ]
        generic_count = sum(1 for phrase in generic_phrases if phrase in reasoning)
        depth -= min(30, generic_count * 10)
        
        scores['reasoning_depth'] = max(0, depth)
        
        # 5. Overall Quality (weighted average)
        overall = (
            scores['decisiveness'] * 0.30 +
            scores['specificity'] * 0.30 +
            scores['risk_awareness'] * 0.20 +
            scores['reasoning_depth'] * 0.20
        )
        
        scores['overall'] = round(overall, 1)
        
        return scores
