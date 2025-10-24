"""
Modular LLM Analysis System - V2

This is the new modular prompt system that replaces hardcoded prompts
with composable, context-aware components.

Usage:
    from wawatrader.llm_v2 import ModularLLMAnalyzer
    
    analyzer = ModularLLMAnalyzer()
    
    # Analyze new opportunity
    result = analyzer.analyze_new_opportunity(
        symbol='AAPL',
        technical_data={...},
        news=[...],
        profile='aggressive'
    )
    
    # Review existing position
    result = analyzer.analyze_position(
        symbol='AAPL',
        technical_data={...},
        position_data={...},
        portfolio_data={...},
        trigger='CAPITAL_CONSTRAINT',
        profile='rotator'
    )
    
    # Audit portfolio
    result = analyzer.audit_portfolio(
        positions_data={...},
        portfolio_data={...},
        profile='rotator'
    )
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from openai import OpenAI

from config.settings import settings
from wawatrader.llm.components.base import QueryContext
from wawatrader.llm.builders.prompt_builder import PromptBuilder
from wawatrader.llm.handlers import StandardDecisionHandler, RankingHandler, ComparisonHandler


class ModularLLMAnalyzer:
    """
    New modular LLM analyzer with context-aware prompts.
    
    This replaces the hardcoded prompt system in LLMBridge with
    a composable component-based architecture.
    """
    
    def __init__(self):
        """Initialize modular analyzer."""
        # LLM client (same as LLMBridge)
        self.client = OpenAI(
            base_url=settings.lm_studio.base_url,
            api_key="not-needed"
        )
        
        self.model = settings.lm_studio.model
        self.temperature = settings.lm_studio.temperature
        self.max_tokens = settings.lm_studio.max_tokens
        
        # Component system
        self.prompt_builder = PromptBuilder()
        
        # Response handlers
        self.handlers = {
            QueryContext.STANDARD_DECISION: StandardDecisionHandler(),
            QueryContext.RANKING: RankingHandler(),
            QueryContext.COMPARISON: ComparisonHandler(),
        }
        
        # Conversation logging
        self.conversation_log = settings.project_root / "logs" / "llm_conversations_v2.jsonl"
        self.conversation_log.parent.mkdir(exist_ok=True)
        
        logger.info("Modular LLM Analyzer initialized")
    
    def analyze_new_opportunity(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        news: Optional[List[Dict[str, Any]]] = None,
        profile: str = 'moderate',
        trigger: str = QueryContext.SCHEDULED_CYCLE,
        overnight_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a NEW trading opportunity (not currently held).
        
        Args:
            symbol: Stock symbol
            technical_data: Technical indicators and price data
            news: Optional news articles
            profile: Trading profile (conservative, moderate, aggressive, rotator, etc.)
            trigger: What triggered this analysis
            overnight_context: Optional overnight deep analysis results
        
        Returns:
            Parsed LLM analysis with action recommendation
        """
        context = QueryContext(
            query_type=QueryContext.NEW_OPPORTUNITY,
            trigger=trigger,
            profile=profile,
            primary_symbol=symbol,
            include_news=bool(news),
            expected_format=QueryContext.STANDARD_DECISION,
            overnight_analysis=overnight_context,
        )
        
        data = {
            'technical': technical_data,
            'news': news or [],
        }
        
        return self._execute_query(context, data)
    
    def analyze_position(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        position_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],
        trigger: str = QueryContext.SCHEDULED_CYCLE,
        profile: str = 'moderate',
        news: Optional[List[Dict[str, Any]]] = None,
        overnight_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an EXISTING position for SELL/HOLD decision.
        
        This is critical for capital rotation - the prompt explicitly
        reminds LLM that position is already owned.
        
        Args:
            symbol: Stock symbol
            technical_data: Technical indicators
            position_data: Current position info (qty, entry price, P&L)
            portfolio_data: Portfolio context (buying power, total value)
            trigger: What triggered this analysis
            profile: Trading profile
            news: Optional news
            overnight_context: Optional overnight deep analysis results
        
        Returns:
            Parsed LLM analysis with SELL/HOLD/BUY recommendation
        """
        context = QueryContext(
            query_type=QueryContext.POSITION_REVIEW,
            trigger=trigger,
            profile=profile,
            primary_symbol=symbol,
            include_news=bool(news),
            expected_format=QueryContext.STANDARD_DECISION,
            overnight_analysis=overnight_context,
        )
        
        data = {
            'technical': technical_data,
            'position': position_data,
            'portfolio': portfolio_data,
            'news': news or [],
        }
        
        return self._execute_query(context, data)
    
    def audit_portfolio(
        self,
        positions_data: List[Dict[str, Any]],
        portfolio_data: Dict[str, Any],
        trigger: str = QueryContext.SCHEDULED_CYCLE,
        profile: str = 'moderate',
    ) -> Dict[str, Any]:
        """
        Audit entire portfolio and rank all positions.
        
        Identifies top performers to KEEP and weak positions to SELL
        for capital rotation.
        
        Args:
            positions_data: List of all positions with technical + P&L data
            portfolio_data: Portfolio summary
            trigger: What triggered this audit
            profile: Trading profile
        
        Returns:
            Ranked positions with KEEP/HOLD/SELL recommendations
        """
        context = QueryContext(
            query_type=QueryContext.PORTFOLIO_AUDIT,
            trigger=trigger,
            profile=profile,
            expected_format=QueryContext.RANKING,
        )
        
        data = {
            'positions': positions_data,
            'portfolio': portfolio_data,
        }
        
        return self._execute_query(context, data)
    
    def compare_opportunities(
        self,
        symbols: List[str],
        technical_data: Dict[str, Dict[str, Any]],
        profile: str = 'moderate',
        trigger: str = QueryContext.SCHEDULED_CYCLE,
        news: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple stocks to identify best opportunity.
        
        Args:
            symbols: List of stock symbols to compare
            technical_data: Dict mapping symbol -> technical indicators
            profile: Trading profile
            trigger: What triggered this comparison
            news: Optional dict mapping symbol -> news articles
        
        Returns:
            Comparative ranking with winner/runner-up/avoid
        """
        context = QueryContext(
            query_type=QueryContext.COMPARATIVE_ANALYSIS,
            trigger=trigger,
            profile=profile,
            comparison_symbols=symbols,
            include_news=bool(news),
            expected_format=QueryContext.COMPARISON,
        )
        
        data = {
            'comparisons': {
                symbol: {
                    'technical': technical_data.get(symbol, {}),
                    'news': news.get(symbol, []) if news else [],
                }
                for symbol in symbols
            }
        }
        
        return self._execute_query(context, data)
    
    def _execute_query(
        self,
        context: QueryContext,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute LLM query: build prompt → call LLM → parse response.
        
        Args:
            context: Query context
            data: Data for components
        
        Returns:
            Parsed and validated LLM response
        """
        try:
            # 1. Build prompt using component system
            prompt = self.prompt_builder.build(context, data)
            
            logger.info(f"Executing {context.query_type} query for {context.primary_symbol or 'portfolio'}")
            
            # 2. Get system prompt from profile
            system_prompt = self._get_system_prompt(context.profile)
            
            # 3. Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            raw_response = response.choices[0].message.content
            
            # 4. Log conversation
            self._log_conversation(context, prompt, raw_response)
            
            # 5. Parse response
            handler = self.handlers.get(context.expected_format)
            if not handler:
                logger.error(f"No handler for format: {context.expected_format}")
                return self._create_error_response("No handler available")
            
            parsed = handler.parse(raw_response)
            
            if not parsed:
                logger.warning("Failed to parse LLM response")
                return self._create_error_response("Failed to parse response")
            
            # Add metadata
            parsed['query_type'] = context.query_type
            parsed['profile'] = context.profile
            parsed['trigger'] = context.trigger
            parsed['timestamp'] = datetime.now().isoformat()
            
            logger.info(f"Query successful (quality: {parsed.get('quality_scores', {}).get('overall', 0):.1f})")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error executing LLM query: {e}")
            return self._create_error_response(str(e))
    
    def _get_system_prompt(self, profile: str) -> str:
        """
        Get system prompt for trading profile.
        
        This uses the same profiles as LLMBridge for consistency.
        
        Args:
            profile: Profile name
        
        Returns:
            System prompt string
        """
        # Import from LLMBridge for consistency
        from wawatrader.llm_bridge import LLMBridge
        
        profile_config = LLMBridge.TRADING_PROFILES.get(
            profile,
            LLMBridge.TRADING_PROFILES['moderate']
        )
        
        return profile_config['system_prompt']
    
    def _log_conversation(
        self,
        context: QueryContext,
        prompt: str,
        response: str
    ):
        """Log conversation to JSONL file."""
        try:
            import json
            
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'query_type': context.query_type,
                'profile': context.profile,
                'trigger': context.trigger,
                'symbol': context.primary_symbol,
                'prompt': prompt,
                'response': response,
            }
            
            with open(self.conversation_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.warning(f"Failed to log conversation: {e}")
    
    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'error': True,
            'error_message': error_msg,
            'sentiment': 'neutral',
            'confidence': 0,
            'action': 'hold',
            'reasoning': f'Analysis failed: {error_msg}',
            'risk_factors': ['[CRITICAL]: LLM analysis unavailable'],
            'timestamp': datetime.now().isoformat(),
        }
