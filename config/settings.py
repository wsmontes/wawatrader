"""
WawaTrader Configuration Management

Loads configuration from environment variables with validation.
All sensitive data (API keys) must be in .env file.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent


class AlpacaConfig(BaseModel):
    """Alpaca API Configuration"""
    api_key: str = Field(..., description="Alpaca API Key")
    secret_key: str = Field(..., description="Alpaca Secret Key")
    base_url: str = Field(default="https://paper-api.alpaca.markets")
    data_url: str = Field(default="https://data.alpaca.markets")
    
    @field_validator('api_key', 'secret_key')
    @classmethod
    def validate_not_placeholder(cls, v):
        if not v or 'your_' in v.lower() or 'here' in v.lower():
            raise ValueError(f"API key is not configured. Please set it in .env file")
        return v


class LMStudioConfig(BaseModel):
    """LM Studio / Gemma 3 Configuration"""
    base_url: str = Field(default="http://localhost:1234/v1")
    model: str = Field(default="google/gemma-3-4b")
    api_key: str = Field(default="not-needed")  # LM Studio doesn't require API key
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=-1)
    timeout: int = Field(default=30, ge=5, le=120)


class RiskConfig(BaseModel):
    """Risk Management Configuration"""
    max_position_size: float = Field(default=0.10, ge=0.01, le=0.50)
    max_daily_loss: float = Field(default=0.02, ge=0.01, le=0.10)
    max_portfolio_risk: float = Field(default=0.30, ge=0.10, le=0.80)


class TradingConfig(BaseModel):
    """Trading Strategy Configuration"""
    technical_weight: float = Field(default=0.70, ge=0.0, le=1.0)
    sentiment_weight: float = Field(default=0.30, ge=0.0, le=1.0)
    min_confidence: int = Field(default=60, ge=0, le=100)
    default_trade_size: int = Field(default=1, ge=1)
    
    @field_validator('sentiment_weight')
    @classmethod
    def validate_weights_sum(cls, v, info):
        if 'technical_weight' in info.data:
            total = info.data['technical_weight'] + v
            if not (0.99 <= total <= 1.01):  # Allow small floating point error
                raise ValueError("technical_weight + sentiment_weight must equal 1.0")
        return v


class SystemConfig(BaseModel):
    """System-wide Configuration"""
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/wawatrader.log")
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=300)  # 5 minutes
    
    market_open_hour: int = Field(default=9, ge=0, le=23)
    market_open_minute: int = Field(default=30, ge=0, le=59)
    market_close_hour: int = Field(default=16, ge=0, le=23)
    market_close_minute: int = Field(default=0, ge=0, le=59)


class Settings:
    """Main Settings Class - Singleton"""
    
    _instance: Optional['Settings'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Load all configurations
        self.alpaca = AlpacaConfig(
            api_key=os.getenv('ALPACA_API_KEY', ''),
            secret_key=os.getenv('ALPACA_SECRET_KEY', ''),
            base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets'),
            data_url=os.getenv('ALPACA_DATA_URL', 'https://data.alpaca.markets')
        )
        
        self.lm_studio = LMStudioConfig(
            base_url=os.getenv('LM_STUDIO_BASE_URL', 'http://localhost:1234/v1'),
            model=os.getenv('LM_STUDIO_MODEL', 'google/gemma-3-4b'),
            api_key=os.getenv('LM_STUDIO_API_KEY', 'not-needed'),
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '-1')),
            timeout=int(os.getenv('LLM_TIMEOUT', '30'))
        )
        
        self.risk = RiskConfig(
            max_position_size=float(os.getenv('MAX_POSITION_SIZE', '0.10')),
            max_daily_loss=float(os.getenv('MAX_DAILY_LOSS', '0.02')),
            max_portfolio_risk=float(os.getenv('MAX_PORTFOLIO_RISK', '0.30'))
        )
        
        self.trading = TradingConfig(
            technical_weight=float(os.getenv('TECHNICAL_WEIGHT', '0.70')),
            sentiment_weight=float(os.getenv('SENTIMENT_WEIGHT', '0.30')),
            min_confidence=int(os.getenv('MIN_CONFIDENCE', '60')),
            default_trade_size=int(os.getenv('DEFAULT_TRADE_SIZE', '1'))
        )
        
        self.system = SystemConfig(
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE', 'logs/wawatrader.log'),
            cache_enabled=os.getenv('CACHE_ENABLED', 'true').lower() == 'true',
            cache_ttl=int(os.getenv('CACHE_TTL', '300')),
            market_open_hour=int(os.getenv('MARKET_OPEN_HOUR', '9')),
            market_open_minute=int(os.getenv('MARKET_OPEN_MINUTE', '30')),
            market_close_hour=int(os.getenv('MARKET_CLOSE_HOUR', '16')),
            market_close_minute=int(os.getenv('MARKET_CLOSE_MINUTE', '0'))
        )
        
        self._initialized = True
    
    @property
    def project_root(self) -> Path:
        """Get project root directory"""
        return PROJECT_ROOT
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory"""
        logs_dir = PROJECT_ROOT / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    @property
    def data_dir(self) -> Path:
        """Get data directory"""
        data_dir = PROJECT_ROOT / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir
    
    @property
    def cache_dir(self) -> Path:
        """Get cache directory"""
        cache_dir = self.data_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir
    
    def validate(self) -> bool:
        """Validate all settings"""
        try:
            # This will raise ValidationError if any setting is invalid
            _ = self.alpaca
            _ = self.lm_studio
            _ = self.risk
            _ = self.trading
            _ = self.system
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False
    
    def __repr__(self) -> str:
        return (
            f"Settings(\n"
            f"  Alpaca: {self.alpaca.base_url}\n"
            f"  LM Studio: {self.lm_studio.base_url} ({self.lm_studio.model})\n"
            f"  Risk: max_pos={self.risk.max_position_size}, max_loss={self.risk.max_daily_loss}\n"
            f"  Trading: tech={self.trading.technical_weight}, sent={self.trading.sentiment_weight}\n"
            f")"
        )


# Global settings instance
settings = Settings()


if __name__ == "__main__":
    # Test configuration loading
    print("WawaTrader Configuration")
    print("=" * 60)
    print(settings)
    print("=" * 60)
    
    if settings.validate():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration validation failed")
