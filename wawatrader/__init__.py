"""
WawaTrader - LLM-Powered Algorithmic Trading System

A hybrid trading system that combines:
- Technical indicators (NumPy/Pandas) for precise numerical analysis
- LLM sentiment analysis (Gemma 3 via LM Studio) for qualitative context
- Alpaca Markets API for paper trading execution

Architecture:
    LLM Layer (Gemma 3) → Orchestration Layer → NumPy/Pandas → Alpaca API
"""

__version__ = "0.1.0"
__author__ = "Wagner Montes"
__description__ = "LLM-Powered Algorithmic Trading System"

# Core components
from .alpaca_client import AlpacaClient, get_client

# Components being built:
# from .indicators import TechnicalIndicators
# from .llm_bridge import LLMBridge
# from .risk_manager import RiskManager
# from .trading_agent import TradingAgent

# Market intelligence
from .enhanced_intelligence import get_enhanced_intelligence_engine

__all__ = [
    'AlpacaClient',
    'get_client',
    'get_enhanced_intelligence_engine',
]
