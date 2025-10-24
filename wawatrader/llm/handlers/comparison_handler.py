"""
Handler for COMPARISON format responses.
"""

from typing import Dict, Any, List
from loguru import logger
from .base_handler import ResponseHandler


class ComparisonHandler(ResponseHandler):
    """
    Handler for comparative analysis responses.
    
    Expected format:
    {
        "rankings": [
            {
                "symbol": "NVDA",
                "rank": 1,
                "score": 92,
                "verdict": "best",
                "reason": "..."
            },
            ...
        ],
        "recommendation": "Primary recommendation with reasoning",
        "summary": "Comparative summary"
    }
    """
    
    def __init__(self):
        super().__init__()
        self.required_fields = ['rankings', 'recommendation', 'summary']
        self.optional_fields = ['winner', 'runner_up', 'avoid']
    
    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """Validate comparison structure."""
        # Check required fields
        if not self._check_required_fields(data):
            missing = [f for f in self.required_fields if f not in data]
            logger.warning(f"Missing required fields: {missing}")
            return False
        
        # Validate rankings is a list
        if not isinstance(data.get('rankings'), list):
            logger.warning("rankings must be a list")
            return False
        
        rankings = data['rankings']
        if not rankings:
            logger.warning("rankings cannot be empty")
            return False
        
        # Validate each ranking entry
        for i, item in enumerate(rankings):
            if not isinstance(item, dict):
                logger.warning(f"Ranking {i} is not a dict")
                return False
            
            required_fields = ['symbol', 'rank', 'score', 'verdict', 'reason']
            for field in required_fields:
                if field not in item:
                    logger.warning(f"Ranking {i} missing field: {field}")
                    return False
        
        # Validate strings
        if not isinstance(data.get('recommendation'), str):
            logger.warning("recommendation must be a string")
            return False
        
        if not isinstance(data.get('summary'), str):
            logger.warning("summary must be a string")
            return False
        
        return True
    
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and normalize comparison data."""
        sanitized = {
            'rankings': [],
            'recommendation': str(data['recommendation']).strip(),
            'summary': str(data['summary']).strip(),
        }
        
        # Sanitize rankings
        for item in data['rankings']:
            sanitized_item = {
                'symbol': str(item['symbol']).upper().strip(),
                'rank': int(item['rank']),
                'score': self._clamp_score(item['score']),
                'verdict': self._normalize_verdict(item['verdict']),
                'reason': str(item['reason']).strip(),
            }
            
            # Optional fields
            if 'confidence' in item:
                sanitized_item['confidence'] = self._clamp_confidence(item['confidence'])
            
            if 'technical_score' in item:
                sanitized_item['technical_score'] = self._clamp_score(item['technical_score'])
            
            if 'risk_score' in item:
                sanitized_item['risk_score'] = self._clamp_score(item['risk_score'])
            
            sanitized['rankings'].append(sanitized_item)
        
        # Sort by rank
        sanitized['rankings'].sort(key=lambda x: x['rank'])
        
        # Optional categorical fields
        if 'winner' in data:
            sanitized['winner'] = str(data['winner']).upper().strip()
        
        if 'runner_up' in data:
            sanitized['runner_up'] = str(data['runner_up']).upper().strip()
        
        if 'avoid' in data:
            if isinstance(data['avoid'], list):
                sanitized['avoid'] = [str(s).upper().strip() for s in data['avoid']]
            else:
                sanitized['avoid'] = [str(data['avoid']).upper().strip()]
        
        return sanitized
    
    def _normalize_verdict(self, verdict: str) -> str:
        """
        Normalize verdict to standard format.
        
        Args:
            verdict: Raw verdict string
        
        Returns:
            Normalized verdict ("best", "good", "neutral", "weak", "avoid")
        """
        verdict_lower = str(verdict).lower().strip()
        
        if any(word in verdict_lower for word in ['best', 'winner', 'top', 'strong buy']):
            return 'best'
        elif any(word in verdict_lower for word in ['good', 'runner', 'buy', 'attractive']):
            return 'good'
        elif any(word in verdict_lower for word in ['weak', 'poor', 'sell', 'exit']):
            return 'weak'
        elif any(word in verdict_lower for word in ['avoid', 'worst', 'pass', 'skip']):
            return 'avoid'
        else:
            return 'neutral'
    
    def _clamp_score(self, score: Any) -> float:
        """Clamp score to [0, 100]."""
        try:
            s = float(score)
            return max(0.0, min(100.0, s))
        except (ValueError, TypeError):
            return 50.0
    
    def _calculate_quality(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate quality scores for comparison.
        
        Scores:
        - decisiveness: Clear winner/loser identified?
        - differentiation: Distinct scores and verdicts?
        - reasoning_clarity: Are differences clearly explained?
        - recommendation_strength: Is recommendation specific and actionable?
        - overall: Weighted average
        """
        scores = {}
        rankings = data['rankings']
        num_items = len(rankings)
        
        # 1. Decisiveness (0-100)
        verdicts = [r['verdict'] for r in rankings]
        
        # Good: Has "best" and "avoid"/"weak"
        has_best = 'best' in verdicts
        has_avoid = 'avoid' in verdicts or 'weak' in verdicts
        
        if has_best and has_avoid:
            decisiveness = 100  # Clear winner and loser
        elif has_best or has_avoid:
            decisiveness = 70  # At least some decisiveness
        elif 'good' in verdicts:
            decisiveness = 50  # Some differentiation
        else:
            decisiveness = 30  # All neutral - indecisive
        
        scores['decisiveness'] = decisiveness
        
        # 2. Differentiation (0-100)
        score_values = [r['score'] for r in rankings]
        
        if num_items == 1:
            differentiation = 100
        else:
            # Calculate score spread
            score_range = max(score_values) - min(score_values)
            
            # Good differentiation: >30 point spread
            if score_range >= 40:
                differentiation = 100
            elif score_range >= 30:
                differentiation = 85
            elif score_range >= 20:
                differentiation = 70
            elif score_range >= 10:
                differentiation = 50
            else:
                differentiation = 30  # Too similar
        
        scores['differentiation'] = differentiation
        
        # 3. Reasoning Clarity (0-100)
        reasoning_scores = []
        
        for item in rankings:
            reason = item['reason'].lower()
            clarity_score = 0
            
            # Bonus for comparative terms
            comparative_terms = [
                'better', 'worse', 'stronger', 'weaker',
                'superior', 'inferior', 'outperforms', 'underperforms',
                'compared to', 'versus', 'vs', 'than'
            ]
            clarity_score += sum(15 for term in comparative_terms if term in reason)
            
            # Bonus for specific metrics
            metric_terms = [
                'rsi', 'macd', 'momentum', 'trend', 'volume',
                'profit', 'loss', 'performance', '%', 'percentage'
            ]
            clarity_score += sum(10 for term in metric_terms if term in reason)
            
            # Penalty for vague terms
            vague_terms = ['maybe', 'might', 'could', 'possibly', 'perhaps']
            clarity_score -= sum(15 for term in vague_terms if term in reason)
            
            reasoning_scores.append(max(0, min(100, clarity_score + 50)))
        
        scores['reasoning_clarity'] = sum(reasoning_scores) / len(reasoning_scores)
        
        # 4. Recommendation Strength (0-100)
        recommendation = data['recommendation'].lower()
        
        rec_strength = 0
        
        # Bonus for decisive language
        decisive_terms = ['recommend', 'prefer', 'choose', 'best', 'avoid', 'sell', 'buy']
        rec_strength += sum(15 for term in decisive_terms if term in recommendation)
        
        # Bonus for specific actions
        action_terms = ['enter', 'exit', 'wait', 'rotate', 'take profit', 'cut loss']
        rec_strength += sum(15 for term in action_terms if term in recommendation)
        
        # Penalty for hedging
        hedge_terms = ['however', 'but', 'although', 'depends', 'uncertain']
        rec_strength -= sum(10 for term in hedge_terms if term in recommendation)
        
        scores['recommendation_strength'] = max(0, min(100, rec_strength + 50))
        
        # 5. Overall Quality
        overall = (
            scores['decisiveness'] * 0.30 +
            scores['differentiation'] * 0.25 +
            scores['reasoning_clarity'] * 0.25 +
            scores['recommendation_strength'] * 0.20
        )
        
        scores['overall'] = round(overall, 1)
        
        return scores
