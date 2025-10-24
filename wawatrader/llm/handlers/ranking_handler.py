"""
Handler for RANKING format responses.
"""

from typing import Dict, Any, List
from loguru import logger
from .base_handler import ResponseHandler


class RankingHandler(ResponseHandler):
    """
    Handler for portfolio ranking responses.
    
    Expected format:
    {
        "ranked_positions": [
            {
                "symbol": "NVDA",
                "rank": 1,
                "score": 92,
                "action": "keep",
                "reason": "Strong momentum..."
            },
            ...
        ],
        "summary": "Overall portfolio health assessment"
    }
    """
    
    def __init__(self):
        super().__init__()
        self.required_fields = ['ranked_positions', 'summary']
        self.optional_fields = ['rotation_candidates', 'portfolio_health']
    
    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """Validate ranking structure."""
        # Check required fields
        if not self._check_required_fields(data):
            missing = [f for f in self.required_fields if f not in data]
            logger.warning(f"Missing required fields: {missing}")
            return False
        
        # Validate ranked_positions is a list
        if not isinstance(data.get('ranked_positions'), list):
            logger.warning("ranked_positions must be a list")
            return False
        
        # Validate each position entry
        ranked_positions = data['ranked_positions']
        if not ranked_positions:
            logger.warning("ranked_positions cannot be empty")
            return False
        
        for i, position in enumerate(ranked_positions):
            if not isinstance(position, dict):
                logger.warning(f"Position {i} is not a dict")
                return False
            
            required_position_fields = ['symbol', 'rank', 'score', 'action', 'reason']
            for field in required_position_fields:
                if field not in position:
                    logger.warning(f"Position {i} missing field: {field}")
                    return False
        
        # Validate summary is string
        if not isinstance(data.get('summary'), str):
            logger.warning("summary must be a string")
            return False
        
        return True
    
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and normalize ranking data."""
        sanitized = {
            'ranked_positions': [],
            'summary': str(data['summary']).strip(),
        }
        
        # Sanitize each position
        for position in data['ranked_positions']:
            sanitized_position = {
                'symbol': str(position['symbol']).upper().strip(),
                'rank': int(position['rank']),
                'score': self._clamp_score(position['score']),
                'action': self._normalize_ranking_action(position['action']),
                'reason': str(position['reason']).strip(),
            }
            
            # Optional fields
            if 'confidence' in position:
                sanitized_position['confidence'] = self._clamp_confidence(position['confidence'])
            
            if 'technical_score' in position:
                sanitized_position['technical_score'] = self._clamp_score(position['technical_score'])
            
            if 'performance_score' in position:
                sanitized_position['performance_score'] = self._clamp_score(position['performance_score'])
            
            sanitized['ranked_positions'].append(sanitized_position)
        
        # Sort by rank to ensure proper ordering
        sanitized['ranked_positions'].sort(key=lambda x: x['rank'])
        
        # Optional fields
        if 'rotation_candidates' in data:
            sanitized['rotation_candidates'] = data['rotation_candidates']
        
        if 'portfolio_health' in data:
            sanitized['portfolio_health'] = str(data['portfolio_health'])
        
        return sanitized
    
    def _normalize_ranking_action(self, action: str) -> str:
        """
        Normalize ranking action to standard format.
        
        Args:
            action: Raw action string
        
        Returns:
            Normalized action ("keep", "hold", "sell")
        """
        action_lower = str(action).lower().strip()
        
        # Map variations
        if any(word in action_lower for word in ['keep', 'strong', 'maintain', 'top']):
            return 'keep'
        elif any(word in action_lower for word in ['sell', 'exit', 'rotate', 'weak', 'bottom']):
            return 'sell'
        else:
            return 'hold'
    
    def _clamp_score(self, score: Any) -> float:
        """
        Clamp score to valid range [0, 100].
        
        Args:
            score: Raw score value
        
        Returns:
            Clamped score as float
        """
        try:
            s = float(score)
            return max(0.0, min(100.0, s))
        except (ValueError, TypeError):
            return 50.0
    
    def _calculate_quality(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate quality scores for ranking.
        
        Scores:
        - rank_distribution: Are positions well-distributed across ranks?
        - score_separation: Clear score differences between positions?
        - action_clarity: Clear KEEP/HOLD/SELL breakdown?
        - reasoning_quality: Are reasons specific and actionable?
        - overall: Weighted average
        """
        scores = {}
        ranked_positions = data['ranked_positions']
        num_positions = len(ranked_positions)
        
        # 1. Rank Distribution (0-100)
        # Check if ranks are sequential and complete
        ranks = [p['rank'] for p in ranked_positions]
        expected_ranks = list(range(1, num_positions + 1))
        
        if ranks == expected_ranks:
            rank_dist = 100  # Perfect
        else:
            # Penalty for gaps or duplicates
            rank_dist = max(0, 100 - (len(set(ranks) ^ set(expected_ranks)) * 20))
        
        scores['rank_distribution'] = rank_dist
        
        # 2. Score Separation (0-100)
        # Good rankings should have clear score differences
        score_values = [p['score'] for p in ranked_positions]
        
        if num_positions == 1:
            score_sep = 100
        else:
            # Calculate average score gap between adjacent ranks
            gaps = [abs(score_values[i] - score_values[i+1]) 
                   for i in range(len(score_values) - 1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            
            # Good separation: avg gap >= 10 points
            if avg_gap >= 15:
                score_sep = 100
            elif avg_gap >= 10:
                score_sep = 80
            elif avg_gap >= 5:
                score_sep = 60
            else:
                score_sep = 40  # Too similar - not decisive
        
        scores['score_separation'] = score_sep
        
        # 3. Action Clarity (0-100)
        # Should have clear breakdown: top 20-30% KEEP, bottom 20-30% SELL
        actions = [p['action'] for p in ranked_positions]
        keep_count = actions.count('keep')
        sell_count = actions.count('sell')
        hold_count = actions.count('hold')
        
        # Ideal: some KEEP at top, some SELL at bottom, rest HOLD
        keep_pct = (keep_count / num_positions) * 100
        sell_pct = (sell_count / num_positions) * 100
        
        if 20 <= keep_pct <= 40 and 20 <= sell_pct <= 40:
            action_clarity = 100  # Good distribution
        elif 10 <= keep_pct <= 50 and 10 <= sell_pct <= 50:
            action_clarity = 75  # Acceptable
        elif keep_count > 0 and sell_count > 0:
            action_clarity = 50  # At least some decisiveness
        else:
            action_clarity = 25  # Too uniform
        
        scores['action_clarity'] = action_clarity
        
        # 4. Reasoning Quality (0-100)
        reasoning_scores = []
        
        for position in ranked_positions:
            reason = position['reason'].lower()
            reason_score = 0
            
            # Check for specific terms
            specific_terms = [
                'rsi', 'macd', 'momentum', 'trend', 'volume', 
                'support', 'resistance', 'breakout', 'breakdown',
                'profit', 'loss', 'performance'
            ]
            reason_score += sum(10 for term in specific_terms if term in reason)
            
            # Penalty for generic phrases
            generic_phrases = ['monitor', 'uncertain', 'mixed', 'depends']
            reason_score -= sum(10 for phrase in generic_phrases if phrase in reason)
            
            reasoning_scores.append(max(0, min(100, reason_score + 50)))
        
        scores['reasoning_quality'] = sum(reasoning_scores) / len(reasoning_scores)
        
        # 5. Overall Quality
        overall = (
            scores['rank_distribution'] * 0.20 +
            scores['score_separation'] * 0.25 +
            scores['action_clarity'] * 0.30 +
            scores['reasoning_quality'] * 0.25
        )
        
        scores['overall'] = round(overall, 1)
        
        return scores
