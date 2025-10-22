"""
Configuration UI for WawaTrader

Web-based interface for managing trading system configuration without code changes.

Features:
- Risk parameter adjustment (position size, daily loss limits, etc.)
- Symbol watchlist management (add/remove symbols)
- LLM model selection and settings
- Alert configuration (email/Slack)
- Trading schedule settings
- Real-time configuration updates
- Settings persistence to database
- Configuration history and rollback

Run with: python -m wawatrader.config_ui

Access at: http://localhost:5001

Author: WawaTrader Team
Date: October 2025
"""

from flask import Flask, render_template_string, request, jsonify, redirect, url_for
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import os
from loguru import logger


class ConfigurationManager:
    """
    Manages system configuration with database persistence.
    
    Features:
    - Load/save configuration from database
    - Validation of configuration values
    - Configuration history tracking
    - Default configuration management
    
    Attributes:
        db_path (str): Path to configuration database
        config (Dict): Current configuration state
    """
    
    def __init__(self, db_path: str = "wawatrader_config.db"):
        """
        Initialize configuration manager.
        
        Args:
            db_path: Path to configuration database file
        """
        self.db_path = db_path
        self.config: Dict[str, Any] = {}
        
        # Initialize database
        self._init_database()
        
        # Load current configuration
        self.load_config()
        
        logger.info(f"Configuration manager initialized: {db_path}")
    
    def _init_database(self) -> None:
        """Create configuration database tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Configuration table (current active config)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Configuration history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT NOT NULL,
                changed_by TEXT,
                changed_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Insert default configuration if empty
        if not self.config:
            self._insert_defaults()
    
    def _insert_defaults(self) -> None:
        """Insert default configuration values"""
        defaults = self._get_default_config()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        for category, settings in defaults.items():
            for key, value_dict in settings.items():
                full_key = f"{category}.{key}"
                cursor.execute("""
                    INSERT OR IGNORE INTO config (key, value, category, description, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    full_key,
                    json.dumps(value_dict['value']),
                    category,
                    value_dict.get('description', ''),
                    timestamp
                ))
        
        conn.commit()
        conn.close()
        
        logger.info("Default configuration inserted")
    
    def _get_default_config(self) -> Dict[str, Dict[str, Any]]:
        """Get default configuration structure"""
        return {
            "risk": {
                "max_position_size_percent": {
                    "value": 10.0,
                    "description": "Maximum position size as percentage of portfolio"
                },
                "max_daily_loss_percent": {
                    "value": 2.0,
                    "description": "Maximum daily loss as percentage of portfolio"
                },
                "max_portfolio_exposure_percent": {
                    "value": 30.0,
                    "description": "Maximum total portfolio exposure"
                },
                "max_trades_per_day": {
                    "value": 10,
                    "description": "Maximum number of trades per day"
                },
                "min_confidence_threshold": {
                    "value": 70.0,
                    "description": "Minimum LLM confidence to execute trade (%)"
                }
            },
            "trading": {
                "symbols": {
                    "value": ["AAPL", "TSLA", "NVDA", "AMD", "MSFT"],
                    "description": "Stock symbols to trade"
                },
                "check_interval_seconds": {
                    "value": 60,
                    "description": "Interval between market checks (seconds)"
                },
                "market_open_hour": {
                    "value": 9,
                    "description": "Market open hour (Eastern Time)"
                },
                "market_open_minute": {
                    "value": 30,
                    "description": "Market open minute"
                },
                "market_close_hour": {
                    "value": 16,
                    "description": "Market close hour (Eastern Time)"
                },
                "market_close_minute": {
                    "value": 0,
                    "description": "Market close minute"
                },
                "dry_run": {
                    "value": True,
                    "description": "Simulate trades without executing (paper trading)"
                }
            },
            "llm": {
                "model_name": {
                    "value": "gemma-3-4b",
                    "description": "LLM model to use for analysis"
                },
                "base_url": {
                    "value": "http://localhost:1234/v1",
                    "description": "LLM Studio base URL"
                },
                "temperature": {
                    "value": 0.7,
                    "description": "LLM temperature (0.0-1.0)"
                },
                "max_tokens": {
                    "value": 500,
                    "description": "Maximum tokens in LLM response"
                },
                "timeout_seconds": {
                    "value": 30,
                    "description": "LLM API timeout (seconds)"
                }
            },
            "alerts": {
                "email_enabled": {
                    "value": False,
                    "description": "Enable email notifications"
                },
                "slack_enabled": {
                    "value": False,
                    "description": "Enable Slack notifications"
                },
                "min_pnl_percent": {
                    "value": 2.0,
                    "description": "Minimum P&L change to trigger alert (%)"
                },
                "daily_summary_time": {
                    "value": "16:00",
                    "description": "Time to send daily summary (HH:MM)"
                }
            },
            "backtesting": {
                "commission_per_share": {
                    "value": 0.0,
                    "description": "Commission per share ($)"
                },
                "slippage_percent": {
                    "value": 0.1,
                    "description": "Slippage as percentage of price"
                }
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from database.
        
        Returns:
            Dictionary of configuration values
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM config")
        rows = cursor.fetchall()
        
        config = {}
        for key, value_json in rows:
            try:
                value = json.loads(value_json)
                # Parse nested keys (e.g., "risk.max_position_size")
                parts = key.split('.')
                current = config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse config value for {key}")
        
        conn.close()
        
        self.config = config
        return config
    
    def save_config(self, key: str, value: Any, changed_by: str = "ui") -> bool:
        """
        Save configuration value to database.
        
        Args:
            key: Configuration key (e.g., "risk.max_position_size_percent")
            value: New value
            changed_by: Who changed the configuration
        
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get old value for history
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            old_value = row[0] if row else None
            
            # Update configuration
            timestamp = datetime.now().isoformat()
            category = key.split('.')[0]
            
            cursor.execute("""
                INSERT OR REPLACE INTO config (key, value, category, description, updated_at)
                VALUES (?, ?, ?, 
                    (SELECT description FROM config WHERE key = ?),
                    ?)
            """, (key, json.dumps(value), category, key, timestamp))
            
            # Add to history
            cursor.execute("""
                INSERT INTO config_history (key, old_value, new_value, changed_by, changed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (key, old_value, json.dumps(value), changed_by, timestamp))
            
            conn.commit()
            conn.close()
            
            # Reload configuration
            self.load_config()
            
            logger.info(f"Configuration updated: {key} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_config(self, key: Optional[str] = None) -> Any:
        """
        Get configuration value(s).
        
        Args:
            key: Specific key to get (returns all if None)
        
        Returns:
            Configuration value or entire config dict
        """
        if key is None:
            return self.config
        
        # Navigate nested dict
        parts = key.split('.')
        current = self.config
        for part in parts:
            if part not in current:
                return None
            current = current[part]
        
        return current
    
    def get_history(self, key: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get configuration change history.
        
        Args:
            key: Filter by specific key (all if None)
            limit: Maximum number of history entries
        
        Returns:
            List of history entries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if key:
            cursor.execute("""
                SELECT id, key, old_value, new_value, changed_by, changed_at
                FROM config_history
                WHERE key = ?
                ORDER BY changed_at DESC
                LIMIT ?
            """, (key, limit))
        else:
            cursor.execute("""
                SELECT id, key, old_value, new_value, changed_by, changed_at
                FROM config_history
                ORDER BY changed_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'key': row[1],
                'old_value': json.loads(row[2]) if row[2] else None,
                'new_value': json.loads(row[3]),
                'changed_by': row[4],
                'changed_at': row[5]
            })
        
        return history
    
    def validate_config(self, key: str, value: Any) -> tuple[bool, Optional[str]]:
        """
        Validate configuration value.
        
        Args:
            key: Configuration key
            value: Value to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Risk parameter validation
        if key == "risk.max_position_size_percent":
            if not (0 < value <= 100):
                return False, "Position size must be between 0 and 100%"
        
        elif key == "risk.max_daily_loss_percent":
            if not (0 < value <= 100):
                return False, "Daily loss limit must be between 0 and 100%"
        
        elif key == "risk.max_portfolio_exposure_percent":
            if not (0 < value <= 100):
                return False, "Portfolio exposure must be between 0 and 100%"
        
        elif key == "risk.max_trades_per_day":
            if not (1 <= value <= 1000):
                return False, "Trades per day must be between 1 and 1000"
        
        elif key == "risk.min_confidence_threshold":
            if not (0 <= value <= 100):
                return False, "Confidence threshold must be between 0 and 100%"
        
        # Trading parameter validation
        elif key == "trading.symbols":
            if not isinstance(value, list) or len(value) == 0:
                return False, "Symbols must be a non-empty list"
            if not all(isinstance(s, str) for s in value):
                return False, "All symbols must be strings"
        
        elif key == "trading.check_interval_seconds":
            if not (1 <= value <= 3600):
                return False, "Check interval must be between 1 and 3600 seconds"
        
        # LLM parameter validation
        elif key == "llm.temperature":
            if not (0.0 <= value <= 1.0):
                return False, "Temperature must be between 0.0 and 1.0"
        
        elif key == "llm.max_tokens":
            if not (1 <= value <= 4096):
                return False, "Max tokens must be between 1 and 4096"
        
        return True, None


# Flask application
app = Flask(__name__)
config_manager = ConfigurationManager()


# HTML template for configuration UI
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WawaTrader Configuration</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header p {
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .tabs {
            display: flex;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        
        .tab {
            flex: 1;
            padding: 15px 20px;
            text-align: center;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            font-weight: 600;
            color: #6c757d;
            transition: all 0.3s;
        }
        
        .tab:hover {
            background: #e9ecef;
            color: #495057;
        }
        
        .tab.active {
            color: #667eea;
            border-bottom: 3px solid #667eea;
            background: white;
        }
        
        .tab-content {
            display: none;
            padding: 30px;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .config-group {
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        
        .config-group h3 {
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #dee2e6;
        }
        
        .config-item {
            margin-bottom: 20px;
        }
        
        .config-item label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #495057;
        }
        
        .config-item .description {
            font-size: 0.9em;
            color: #6c757d;
            margin-bottom: 8px;
        }
        
        .config-item input,
        .config-item select,
        .config-item textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 6px;
            font-size: 1em;
            transition: border-color 0.3s;
        }
        
        .config-item input:focus,
        .config-item select:focus,
        .config-item textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .config-item input[type="checkbox"] {
            width: auto;
            margin-right: 8px;
        }
        
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .alert {
            padding: 15px 20px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }
        
        .alert.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        
        .alert.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }
        
        .history-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .history-table th,
        .history-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        
        .history-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }
        
        .history-table tr:hover {
            background: #f8f9fa;
        }
        
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        
        .status-badge.active {
            background: #d4edda;
            color: #155724;
        }
        
        .status-badge.inactive {
            background: #f8d7da;
            color: #721c24;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚙️ WawaTrader Configuration</h1>
            <p>Manage your trading system settings without code changes</p>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('risk')">🛡️ Risk Management</button>
            <button class="tab" onclick="switchTab('trading')">📈 Trading Settings</button>
            <button class="tab" onclick="switchTab('llm')">🤖 LLM Configuration</button>
            <button class="tab" onclick="switchTab('alerts')">🔔 Alerts</button>
            <button class="tab" onclick="switchTab('history')">📜 History</button>
        </div>
        
        <div id="alert-container"></div>
        
        <!-- Risk Management Tab -->
        <div id="risk-tab" class="tab-content active">
            <div class="config-group">
                <h3>Position & Exposure Limits</h3>
                
                <div class="config-item">
                    <label>Maximum Position Size (%)</label>
                    <div class="description">Maximum position size as percentage of portfolio value</div>
                    <input type="number" id="risk.max_position_size_percent" step="0.1" min="0" max="100">
                </div>
                
                <div class="config-item">
                    <label>Maximum Daily Loss (%)</label>
                    <div class="description">Maximum daily loss as percentage of portfolio value</div>
                    <input type="number" id="risk.max_daily_loss_percent" step="0.1" min="0" max="100">
                </div>
                
                <div class="config-item">
                    <label>Maximum Portfolio Exposure (%)</label>
                    <div class="description">Maximum total portfolio exposure across all positions</div>
                    <input type="number" id="risk.max_portfolio_exposure_percent" step="0.1" min="0" max="100">
                </div>
                
                <div class="config-item">
                    <label>Maximum Trades Per Day</label>
                    <div class="description">Maximum number of trades allowed per day</div>
                    <input type="number" id="risk.max_trades_per_day" min="1" max="1000">
                </div>
                
                <div class="config-item">
                    <label>Minimum Confidence Threshold (%)</label>
                    <div class="description">Minimum LLM confidence required to execute trade</div>
                    <input type="number" id="risk.min_confidence_threshold" step="1" min="0" max="100">
                </div>
                
                <div class="button-group">
                    <button class="btn-primary" onclick="saveCategory('risk')">💾 Save Risk Settings</button>
                    <button class="btn-secondary" onclick="loadConfig()">🔄 Reset</button>
                </div>
            </div>
        </div>
        
        <!-- Trading Settings Tab -->
        <div id="trading-tab" class="tab-content">
            <div class="config-group">
                <h3>Symbol Watchlist</h3>
                
                <div class="config-item">
                    <label>Trading Symbols</label>
                    <div class="description">Stock symbols to monitor and trade (comma-separated)</div>
                    <input type="text" id="trading.symbols" placeholder="AAPL, TSLA, NVDA, AMD, MSFT">
                </div>
                
                <div class="config-item">
                    <label>Check Interval (seconds)</label>
                    <div class="description">How often to check market conditions</div>
                    <input type="number" id="trading.check_interval_seconds" min="1" max="3600">
                </div>
                
                <div class="config-item">
                    <label>
                        <input type="checkbox" id="trading.dry_run">
                        Dry Run Mode (Paper Trading)
                    </label>
                    <div class="description">Simulate trades without real execution</div>
                </div>
                
                <div class="button-group">
                    <button class="btn-primary" onclick="saveCategory('trading')">💾 Save Trading Settings</button>
                    <button class="btn-secondary" onclick="loadConfig()">🔄 Reset</button>
                </div>
            </div>
        </div>
        
        <!-- LLM Configuration Tab -->
        <div id="llm-tab" class="tab-content">
            <div class="config-group">
                <h3>LLM Model Settings</h3>
                
                <div class="config-item">
                    <label>Model Name</label>
                    <div class="description">LLM model to use for market analysis</div>
                    <select id="llm.model_name">
                        <option value="gemma-3-4b">Gemma 3 4B</option>
                        <option value="gemma-3-7b">Gemma 3 7B</option>
                        <option value="llama-3-8b">Llama 3 8B</option>
                        <option value="mistral-7b">Mistral 7B</option>
                    </select>
                </div>
                
                <div class="config-item">
                    <label>Base URL</label>
                    <div class="description">LLM Studio API base URL</div>
                    <input type="text" id="llm.base_url" placeholder="http://localhost:1234/v1">
                </div>
                
                <div class="config-item">
                    <label>Temperature</label>
                    <div class="description">Creativity vs consistency (0.0 = consistent, 1.0 = creative)</div>
                    <input type="number" id="llm.temperature" step="0.1" min="0" max="1">
                </div>
                
                <div class="config-item">
                    <label>Max Tokens</label>
                    <div class="description">Maximum tokens in LLM response</div>
                    <input type="number" id="llm.max_tokens" min="1" max="4096">
                </div>
                
                <div class="button-group">
                    <button class="btn-primary" onclick="saveCategory('llm')">💾 Save LLM Settings</button>
                    <button class="btn-secondary" onclick="loadConfig()">🔄 Reset</button>
                </div>
            </div>
        </div>
        
        <!-- Alerts Tab -->
        <div id="alerts-tab" class="tab-content">
            <div class="config-group">
                <h3>Notification Settings</h3>
                
                <div class="config-item">
                    <label>
                        <input type="checkbox" id="alerts.email_enabled">
                        Enable Email Notifications
                    </label>
                    <div class="description">Send alerts via email (configure SMTP in environment)</div>
                </div>
                
                <div class="config-item">
                    <label>
                        <input type="checkbox" id="alerts.slack_enabled">
                        Enable Slack Notifications
                    </label>
                    <div class="description">Send alerts to Slack (configure webhook in environment)</div>
                </div>
                
                <div class="config-item">
                    <label>Minimum P&L Alert Threshold (%)</label>
                    <div class="description">Minimum P&L change to trigger alert</div>
                    <input type="number" id="alerts.min_pnl_percent" step="0.1" min="0" max="100">
                </div>
                
                <div class="config-item">
                    <label>Daily Summary Time</label>
                    <div class="description">Time to send daily summary (HH:MM format)</div>
                    <input type="time" id="alerts.daily_summary_time">
                </div>
                
                <div class="button-group">
                    <button class="btn-primary" onclick="saveCategory('alerts')">💾 Save Alert Settings</button>
                    <button class="btn-secondary" onclick="loadConfig()">🔄 Reset</button>
                </div>
            </div>
        </div>
        
        <!-- History Tab -->
        <div id="history-tab" class="tab-content">
            <div class="config-group">
                <h3>Configuration Change History</h3>
                <table class="history-table" id="history-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Setting</th>
                            <th>Old Value</th>
                            <th>New Value</th>
                            <th>Changed By</th>
                        </tr>
                    </thead>
                    <tbody id="history-body">
                        <tr><td colspan="5" style="text-align:center;">Loading...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let currentConfig = {};
        
        // Switch between tabs
        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabName + '-tab').classList.add('active');
            
            // Load history if history tab
            if (tabName === 'history') {
                loadHistory();
            }
        }
        
        // Load configuration from server
        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                currentConfig = await response.json();
                populateForm();
            } catch (error) {
                showAlert('Failed to load configuration', 'error');
            }
        }
        
        // Populate form with config values
        function populateForm() {
            for (const [category, settings] of Object.entries(currentConfig)) {
                for (const [key, value] of Object.entries(settings)) {
                    const fullKey = `${category}.${key}`;
                    const element = document.getElementById(fullKey);
                    
                    if (!element) continue;
                    
                    if (element.type === 'checkbox') {
                        element.checked = value;
                    } else if (fullKey === 'trading.symbols') {
                        element.value = Array.isArray(value) ? value.join(', ') : value;
                    } else {
                        element.value = value;
                    }
                }
            }
        }
        
        // Save category configuration
        async function saveCategory(category) {
            const updates = {};
            const categoryConfig = currentConfig[category] || {};
            
            for (const key of Object.keys(categoryConfig)) {
                const fullKey = `${category}.${key}`;
                const element = document.getElementById(fullKey);
                
                if (!element) continue;
                
                let value;
                if (element.type === 'checkbox') {
                    value = element.checked;
                } else if (element.type === 'number') {
                    value = parseFloat(element.value);
                } else if (fullKey === 'trading.symbols') {
                    value = element.value.split(',').map(s => s.trim()).filter(s => s);
                } else {
                    value = element.value;
                }
                
                updates[fullKey] = value;
            }
            
            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updates)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showAlert(`${category.charAt(0).toUpperCase() + category.slice(1)} settings saved successfully!`, 'success');
                    loadConfig();
                } else {
                    showAlert(result.message || 'Failed to save configuration', 'error');
                }
            } catch (error) {
                showAlert('Failed to save configuration: ' + error.message, 'error');
            }
        }
        
        // Load configuration history
        async function loadHistory() {
            try {
                const response = await fetch('/api/history');
                const history = await response.json();
                
                const tbody = document.getElementById('history-body');
                tbody.innerHTML = '';
                
                if (history.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No history yet</td></tr>';
                    return;
                }
                
                for (const entry of history) {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${new Date(entry.changed_at).toLocaleString()}</td>
                        <td><strong>${entry.key}</strong></td>
                        <td>${JSON.stringify(entry.old_value)}</td>
                        <td>${JSON.stringify(entry.new_value)}</td>
                        <td>${entry.changed_by}</td>
                    `;
                }
            } catch (error) {
                showAlert('Failed to load history', 'error');
            }
        }
        
        // Show alert message
        function showAlert(message, type) {
            const container = document.getElementById('alert-container');
            const alert = document.createElement('div');
            alert.className = `alert ${type}`;
            alert.textContent = message;
            alert.style.display = 'block';
            
            container.innerHTML = '';
            container.appendChild(alert);
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                alert.style.display = 'none';
            }, 5000);
        }
        
        // Load config on page load
        window.addEventListener('DOMContentLoaded', loadConfig);
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Render main configuration page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(config_manager.get_config())


@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration updates"""
    try:
        updates = request.json
        
        for key, value in updates.items():
            # Validate
            is_valid, error = config_manager.validate_config(key, value)
            if not is_valid:
                return jsonify({'success': False, 'message': error}), 400
            
            # Save
            success = config_manager.save_config(key, value, changed_by='ui')
            if not success:
                return jsonify({'success': False, 'message': f'Failed to save {key}'}), 500
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """Get configuration change history"""
    history = config_manager.get_history()
    return jsonify(history)


def run_config_ui(host: str = '0.0.0.0', port: int = 5001, debug: bool = False):
    """
    Start the configuration UI server.
    
    Args:
        host: Host to bind to (default: 0.0.0.0)
        port: Port to listen on (default: 5001)
        debug: Enable debug mode
    """
    logger.info(f"Starting configuration UI on http://{host}:{port}")
    logger.info("Access the UI in your browser to manage settings")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_config_ui(debug=True)
