"""
Unit tests for Configuration UI

Tests configuration management functionality:
- Configuration loading/saving
- Validation rules
- History tracking
- Default configuration
- Database persistence

Run with: pytest tests/test_config_ui.py -v
"""

import pytest
import os
import tempfile
import json
from pathlib import Path

from wawatrader.config_ui import ConfigurationManager


class TestConfigurationSetup:
    """Test configuration manager initialization"""
    
    def test_initialization(self, tmp_path):
        """Test configuration manager initialization"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        assert config_mgr.db_path == str(db_path)
        assert os.path.exists(db_path)
        assert config_mgr.config is not None
    
    def test_default_config_loaded(self, tmp_path):
        """Test default configuration is loaded"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        config = config_mgr.get_config()
        
        # Check main categories exist
        assert 'risk' in config
        assert 'trading' in config
        assert 'llm' in config
        assert 'alerts' in config
        
        # Check some specific defaults
        assert config['risk']['max_position_size_percent'] == 10.0
        assert config['risk']['max_daily_loss_percent'] == 2.0
        assert config['trading']['symbols'] == ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"]
        assert config['llm']['model_name'] == "gemma-3-4b"


class TestConfigurationCRUD:
    """Test configuration create, read, update operations"""
    
    def test_get_config_all(self, tmp_path):
        """Test getting all configuration"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        config = config_mgr.get_config()
        assert isinstance(config, dict)
        assert len(config) > 0
    
    def test_get_config_specific_key(self, tmp_path):
        """Test getting specific configuration key"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        value = config_mgr.get_config('risk.max_position_size_percent')
        assert value == 10.0
        
        value = config_mgr.get_config('trading.symbols')
        assert isinstance(value, list)
    
    def test_get_config_nested_category(self, tmp_path):
        """Test getting entire category"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        risk_config = config_mgr.get_config('risk')
        assert isinstance(risk_config, dict)
        assert 'max_position_size_percent' in risk_config
        assert 'max_daily_loss_percent' in risk_config
    
    def test_save_config(self, tmp_path):
        """Test saving configuration"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Save new value
        success = config_mgr.save_config(
            'risk.max_position_size_percent',
            15.0,
            changed_by='test'
        )
        
        assert success is True
        
        # Verify saved
        value = config_mgr.get_config('risk.max_position_size_percent')
        assert value == 15.0
    
    def test_save_config_list(self, tmp_path):
        """Test saving list configuration"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        new_symbols = ["SPY", "QQQ", "IWM"]
        success = config_mgr.save_config(
            'trading.symbols',
            new_symbols,
            changed_by='test'
        )
        
        assert success is True
        
        value = config_mgr.get_config('trading.symbols')
        assert value == new_symbols
    
    def test_save_config_boolean(self, tmp_path):
        """Test saving boolean configuration"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        success = config_mgr.save_config(
            'trading.dry_run',
            False,
            changed_by='test'
        )
        
        assert success is True
        
        value = config_mgr.get_config('trading.dry_run')
        assert value is False


class TestConfigurationValidation:
    """Test configuration validation"""
    
    def test_valid_position_size(self, tmp_path):
        """Test valid position size validation"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'risk.max_position_size_percent',
            15.0
        )
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_position_size_too_high(self, tmp_path):
        """Test invalid position size (too high)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'risk.max_position_size_percent',
            150.0
        )
        
        assert is_valid is False
        assert error is not None
        assert "between 0 and 100" in error
    
    def test_invalid_position_size_zero(self, tmp_path):
        """Test invalid position size (zero)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'risk.max_position_size_percent',
            0.0
        )
        
        assert is_valid is False
    
    def test_valid_symbols_list(self, tmp_path):
        """Test valid symbols list"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'trading.symbols',
            ["AAPL", "TSLA"]
        )
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_symbols_empty(self, tmp_path):
        """Test invalid symbols (empty list)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'trading.symbols',
            []
        )
        
        assert is_valid is False
        assert "non-empty" in error
    
    def test_invalid_symbols_not_list(self, tmp_path):
        """Test invalid symbols (not a list)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'trading.symbols',
            "AAPL,TSLA"
        )
        
        assert is_valid is False
    
    def test_valid_temperature(self, tmp_path):
        """Test valid LLM temperature"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'llm.temperature',
            0.7
        )
        
        assert is_valid is True
    
    def test_invalid_temperature_too_high(self, tmp_path):
        """Test invalid temperature (too high)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'llm.temperature',
            1.5
        )
        
        assert is_valid is False
        assert "between 0.0 and 1.0" in error
    
    def test_valid_check_interval(self, tmp_path):
        """Test valid check interval"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'trading.check_interval_seconds',
            60
        )
        
        assert is_valid is True
    
    def test_invalid_check_interval_too_low(self, tmp_path):
        """Test invalid check interval (too low)"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        is_valid, error = config_mgr.validate_config(
            'trading.check_interval_seconds',
            0
        )
        
        assert is_valid is False


class TestConfigurationHistory:
    """Test configuration change history"""
    
    def test_history_empty_initially(self, tmp_path):
        """Test history is empty for new database"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Clear any initialization history
        history = config_mgr.get_history()
        # Should be empty or only contain defaults
        assert isinstance(history, list)
    
    def test_history_records_change(self, tmp_path):
        """Test history records configuration changes"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Make a change
        config_mgr.save_config(
            'risk.max_position_size_percent',
            20.0,
            changed_by='test_user'
        )
        
        # Check history
        history = config_mgr.get_history(key='risk.max_position_size_percent')
        
        assert len(history) > 0
        latest = history[0]
        assert latest['key'] == 'risk.max_position_size_percent'
        assert latest['new_value'] == 20.0
        assert latest['changed_by'] == 'test_user'
    
    def test_history_tracks_multiple_changes(self, tmp_path):
        """Test history tracks multiple changes"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Make multiple changes
        config_mgr.save_config('risk.max_position_size_percent', 15.0)
        config_mgr.save_config('risk.max_position_size_percent', 20.0)
        config_mgr.save_config('risk.max_position_size_percent', 25.0)
        
        history = config_mgr.get_history(key='risk.max_position_size_percent')
        
        # Should have 3 changes
        assert len(history) >= 3
        
        # Latest should be 25.0
        assert history[0]['new_value'] == 25.0
    
    def test_history_limit(self, tmp_path):
        """Test history respects limit parameter"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Make many changes
        for i in range(10):
            config_mgr.save_config('risk.max_position_size_percent', 10.0 + i)
        
        # Get limited history
        history = config_mgr.get_history(limit=5)
        
        assert len(history) <= 5
    
    def test_history_includes_old_value(self, tmp_path):
        """Test history includes old value"""
        db_path = tmp_path / "test_config.db"
        config_mgr = ConfigurationManager(str(db_path))
        
        # Make a change
        config_mgr.save_config('risk.max_position_size_percent', 20.0)
        
        # Make another change
        config_mgr.save_config('risk.max_position_size_percent', 30.0)
        
        history = config_mgr.get_history(key='risk.max_position_size_percent')
        
        # Latest change should have old_value of 20.0
        latest = history[0]
        assert latest['old_value'] == 20.0
        assert latest['new_value'] == 30.0


class TestConfigurationPersistence:
    """Test configuration persistence across instances"""
    
    def test_persistence_after_reload(self, tmp_path):
        """Test configuration persists after manager reload"""
        db_path = tmp_path / "test_config.db"
        
        # Create first instance and save config
        config_mgr1 = ConfigurationManager(str(db_path))
        config_mgr1.save_config('risk.max_position_size_percent', 25.0)
        
        # Create second instance (simulates restart)
        config_mgr2 = ConfigurationManager(str(db_path))
        
        # Should have same value
        value = config_mgr2.get_config('risk.max_position_size_percent')
        assert value == 25.0
    
    def test_multiple_updates_persist(self, tmp_path):
        """Test multiple updates persist correctly"""
        db_path = tmp_path / "test_config.db"
        
        config_mgr = ConfigurationManager(str(db_path))
        
        # Update multiple values
        config_mgr.save_config('risk.max_position_size_percent', 15.0)
        config_mgr.save_config('risk.max_daily_loss_percent', 3.0)
        config_mgr.save_config('trading.symbols', ["SPY", "QQQ"])
        
        # Reload
        config_mgr2 = ConfigurationManager(str(db_path))
        
        # All should be persisted
        assert config_mgr2.get_config('risk.max_position_size_percent') == 15.0
        assert config_mgr2.get_config('risk.max_daily_loss_percent') == 3.0
        assert config_mgr2.get_config('trading.symbols') == ["SPY", "QQQ"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
