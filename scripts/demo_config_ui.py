"""
Configuration UI Demo

Demonstrates the configuration management system.

Features demonstrated:
- Loading default configuration
- Updating configuration values
- Configuration validation
- History tracking
- Persistence across sessions

Run with: python scripts/demo_config_ui.py

Author: WawaTrader Team
Date: October 2025
"""

import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.config_ui import ConfigurationManager
from loguru import logger


def demo_configuration_system():
    """Demonstrate configuration management system"""
    
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║   WawaTrader Configuration System - Feature Demo         ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Use temp database for demo
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    logger.info("1️⃣  CONFIGURATION INITIALIZATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    config_mgr = ConfigurationManager(db_path)
    
    logger.info("✅ Configuration manager initialized")
    logger.info(f"   Database: {db_path}")
    logger.info("")
    
    # Demo 1: View Default Configuration
    logger.info("2️⃣  DEFAULT CONFIGURATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    config = config_mgr.get_config()
    
    logger.info("📋 Risk Management Defaults:")
    for key, value in config.get('risk', {}).items():
        logger.info(f"   • {key}: {value}")
    logger.info("")
    
    logger.info("📋 Trading Settings Defaults:")
    for key, value in config.get('trading', {}).items():
        logger.info(f"   • {key}: {value}")
    logger.info("")
    
    # Demo 2: Update Configuration
    logger.info("3️⃣  UPDATING CONFIGURATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    # Update risk parameters
    logger.info("🔧 Updating risk parameters...")
    config_mgr.save_config('risk.max_position_size_percent', 15.0, 'demo')
    config_mgr.save_config('risk.max_daily_loss_percent', 3.0, 'demo')
    logger.info("✅ Risk limits updated")
    logger.info("   Max position size: 15.0%")
    logger.info("   Max daily loss: 3.0%")
    logger.info("")
    
    # Update symbol watchlist
    logger.info("🔧 Updating symbol watchlist...")
    new_symbols = ["SPY", "QQQ", "IWM", "DIA"]
    config_mgr.save_config('trading.symbols', new_symbols, 'demo')
    logger.info("✅ Watchlist updated")
    logger.info(f"   Symbols: {', '.join(new_symbols)}")
    logger.info("")
    
    # Update LLM settings
    logger.info("🔧 Updating LLM configuration...")
    config_mgr.save_config('llm.model_name', 'gemma-3-7b', 'demo')
    config_mgr.save_config('llm.temperature', 0.5, 'demo')
    logger.info("✅ LLM settings updated")
    logger.info("   Model: gemma-3-7b")
    logger.info("   Temperature: 0.5")
    logger.info("")
    
    # Demo 3: Validation
    logger.info("4️⃣  CONFIGURATION VALIDATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    # Valid value
    is_valid, error = config_mgr.validate_config('risk.max_position_size_percent', 20.0)
    logger.info(f"✅ Valid: max_position_size_percent = 20.0")
    logger.info(f"   Result: {is_valid}, Error: {error}")
    logger.info("")
    
    # Invalid value (too high)
    is_valid, error = config_mgr.validate_config('risk.max_position_size_percent', 150.0)
    logger.info(f"❌ Invalid: max_position_size_percent = 150.0")
    logger.info(f"   Result: {is_valid}")
    logger.info(f"   Error: {error}")
    logger.info("")
    
    # Invalid temperature
    is_valid, error = config_mgr.validate_config('llm.temperature', 2.0)
    logger.info(f"❌ Invalid: llm.temperature = 2.0")
    logger.info(f"   Result: {is_valid}")
    logger.info(f"   Error: {error}")
    logger.info("")
    
    # Demo 4: Configuration History
    logger.info("5️⃣  CONFIGURATION HISTORY")
    logger.info("────────────────────────────────────────────────────────────")
    
    history = config_mgr.get_history(limit=5)
    
    logger.info(f"📜 Recent configuration changes ({len(history)}):")
    for i, entry in enumerate(history[:5], 1):
        logger.info(f"   {i}. {entry['key']}")
        logger.info(f"      Old: {entry['old_value']} → New: {entry['new_value']}")
        logger.info(f"      By: {entry['changed_by']} at {entry['changed_at'][:19]}")
    logger.info("")
    
    # Demo 5: Retrieve Specific Config
    logger.info("6️⃣  RETRIEVING CONFIGURATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    # Get specific value
    position_size = config_mgr.get_config('risk.max_position_size_percent')
    logger.info(f"🔍 Get specific value:")
    logger.info(f"   risk.max_position_size_percent = {position_size}%")
    logger.info("")
    
    # Get category
    risk_config = config_mgr.get_config('risk')
    logger.info(f"🔍 Get entire category (risk):")
    for key, value in risk_config.items():
        logger.info(f"   • {key}: {value}")
    logger.info("")
    
    # Demo 6: Persistence Test
    logger.info("7️⃣  PERSISTENCE VERIFICATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    logger.info("💾 Saving critical value...")
    config_mgr.save_config('risk.min_confidence_threshold', 75.0, 'demo')
    logger.info("   Saved: min_confidence_threshold = 75.0%")
    logger.info("")
    
    logger.info("🔄 Simulating system restart (creating new instance)...")
    config_mgr2 = ConfigurationManager(db_path)
    
    threshold = config_mgr2.get_config('risk.min_confidence_threshold')
    logger.info(f"✅ Value persisted after reload: {threshold}%")
    logger.info("")
    
    # Demo 7: Web UI Information
    logger.info("8️⃣  WEB UI ACCESS")
    logger.info("────────────────────────────────────────────────────────────")
    logger.info("")
    logger.info("🌐 To launch the web UI:")
    logger.info("   python scripts/run_config_ui.py")
    logger.info("")
    logger.info("📱 Then access in browser:")
    logger.info("   http://localhost:5001")
    logger.info("")
    logger.info("✨ Web UI Features:")
    logger.info("   • Visual configuration editor")
    logger.info("   • Real-time validation")
    logger.info("   • Configuration history viewer")
    logger.info("   • Category-based organization")
    logger.info("   • Auto-save with error handling")
    logger.info("")
    
    logger.success("✅ Configuration system demo complete!")
    logger.info("")
    logger.info("Configuration management features:")
    logger.info("  ✅ Database persistence (SQLite)")
    logger.info("  ✅ Default configuration auto-load")
    logger.info("  ✅ Validation rules for all settings")
    logger.info("  ✅ Change history tracking")
    logger.info("  ✅ Category-based organization")
    logger.info("  ✅ Web-based UI (Flask)")
    logger.info("  ✅ No code changes required")
    logger.info("  ✅ Audit trail for compliance")
    logger.info("")
    
    # Clean up
    import os
    os.unlink(db_path)
    logger.info(f"🧹 Demo database cleaned up")


if __name__ == '__main__':
    demo_configuration_system()
