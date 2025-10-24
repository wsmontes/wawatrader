"""
Base response handler for parsing and validating LLM responses.
"""

import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from loguru import logger


class ResponseHandler(ABC):
    """
    Base class for parsing and validating LLM responses.
    
    Each response format (STANDARD_DECISION, RANKING, COMPARISON) has its own handler.
    Handlers validate structure, sanitize data, and calculate quality scores.
    """
    
    def __init__(self):
        self.required_fields: list[str] = []
        self.optional_fields: list[str] = []
    
    def parse(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """
        Parse raw LLM response into structured data.
        
        Args:
            raw_response: Raw text from LLM
        
        Returns:
            Parsed and validated dict, or None if invalid
        """
        try:
            # Try to extract JSON from response
            data = self._extract_json(raw_response)
            if not data:
                logger.warning("Failed to extract JSON from response")
                return None
            
            # Validate structure
            if not self._validate_structure(data):
                logger.warning("Response structure validation failed")
                return None
            
            # Sanitize and normalize
            sanitized = self._sanitize(data)
            
            # Calculate quality score
            quality_scores = self._calculate_quality(sanitized)
            sanitized['quality_scores'] = quality_scores
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
    
    def _extract_json(self, raw_response: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from raw response (handles markdown code blocks, etc.)
        
        Args:
            raw_response: Raw text from LLM
        
        Returns:
            Parsed JSON dict or None
        """
        try:
            # Try direct JSON parse
            return json.loads(raw_response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        if '```json' in raw_response:
            try:
                start = raw_response.index('```json') + 7
                end = raw_response.index('```', start)
                json_str = raw_response[start:end].strip()
                return json.loads(json_str)
            except (ValueError, json.JSONDecodeError):
                pass
        
        # Try to find any JSON-like structure
        import re
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, raw_response, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    @abstractmethod
    def _validate_structure(self, data: Dict[str, Any]) -> bool:
        """
        Validate that response has required fields and correct types.
        
        Args:
            data: Parsed JSON data
        
        Returns:
            True if valid, False otherwise
        """
        pass
    
    @abstractmethod
    def _sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize and normalize response data.
        
        Args:
            data: Raw parsed data
        
        Returns:
            Sanitized data with normalized values
        """
        pass
    
    @abstractmethod
    def _calculate_quality(self, data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate quality scores for the response.
        
        Args:
            data: Sanitized response data
        
        Returns:
            Dict of quality scores (0-100)
        """
        pass
    
    def _check_required_fields(self, data: Dict[str, Any]) -> bool:
        """
        Check if all required fields are present.
        
        Args:
            data: Parsed data
        
        Returns:
            True if all required fields present
        """
        return all(field in data for field in self.required_fields)
    
    def _normalize_action(self, action: str) -> str:
        """
        Normalize action string to standard format.
        
        Args:
            action: Raw action string
        
        Returns:
            Normalized action ("buy", "sell", "hold", "keep", "avoid")
        """
        action_lower = str(action).lower().strip()
        
        # Map variations to standard actions
        action_map = {
            'buy': 'buy',
            'long': 'buy',
            'enter': 'buy',
            'sell': 'sell',
            'short': 'sell',
            'exit': 'sell',
            'close': 'sell',
            'hold': 'hold',
            'wait': 'hold',
            'neutral': 'hold',
            'keep': 'keep',
            'maintain': 'keep',
            'avoid': 'avoid',
            'pass': 'avoid',
            'skip': 'avoid',
        }
        
        return action_map.get(action_lower, 'hold')
    
    def _normalize_sentiment(self, sentiment: str) -> str:
        """
        Normalize sentiment string to standard format.
        
        Args:
            sentiment: Raw sentiment string
        
        Returns:
            Normalized sentiment ("bullish", "bearish", "neutral")
        """
        sentiment_lower = str(sentiment).lower().strip()
        
        if any(word in sentiment_lower for word in ['bull', 'positive', 'up', 'strong']):
            return 'bullish'
        elif any(word in sentiment_lower for word in ['bear', 'negative', 'down', 'weak']):
            return 'bearish'
        else:
            return 'neutral'
    
    def _clamp_confidence(self, confidence: Any) -> float:
        """
        Clamp confidence to valid range [0, 100].
        
        Args:
            confidence: Raw confidence value
        
        Returns:
            Clamped confidence as float
        """
        try:
            conf = float(confidence)
            return max(0.0, min(100.0, conf))
        except (ValueError, TypeError):
            return 50.0  # Default to neutral confidence
