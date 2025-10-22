"""
WawaTrader Beta Dashboard

Elite daytrading interface with comprehensive LLM transparency and real-time market intelligence.
Inspired by TradingView Pro, Bloomberg Terminal, and Interactive Brokers TWS.

Features:
- Dark professional theme optimized for trading
- Real-time LLM thought process visualization
- Advanced candlestick charts with AI annotations
- Market screener with opportunity detection
- Performance analytics with AI decision tracking
- Interactive conversation analysis
- Professional order management interface
- Alert system with sound notifications

Architecture:
- Header Bar: Status, P&L, System Health
- Main Panel: Live charts with LLM reasoning overlay
- Side Panels: Market intel, positions, conversations
- Bottom Bar: Performance metrics, alerts

Usage:
    from wawatrader.dashboard import Dashboard
    
    dash = Dashboard()
    dash.app.run(port=8050)
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from loguru import logger
import asyncio

try:
    from dash import Dash, html, dcc, Input, Output, dash_table, callback, ctx, State, ALL
    import dash_bootstrap_components as dbc
    import plotly.express as px
    DASH_AVAILABLE = True
    MODAL_AVAILABLE = True
except ImportError:
    try:
        # Try importing just the core components
        from dash import Dash, html, dcc, Input, Output, callback, ctx, State, ALL
        import plotly.express as px
        DASH_AVAILABLE = True
        MODAL_AVAILABLE = False
    except ImportError:
        DASH_AVAILABLE = False
        MODAL_AVAILABLE = False
except ImportError:
    logger.warning("Dash not installed. Dashboard features unavailable.")
    logger.info("Install with: pip install dash dash-bootstrap-components plotly")
    DASH_AVAILABLE = False

from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals


class Dashboard:
    """
    Elite professional trading dashboard with LLM transparency.
    
    Designed for serious daytraders who need:
    - Maximum information density
    - Real-time LLM decision insights
    - Professional dark theme
    - Responsive layout that fits any screen
    - Advanced analytics and monitoring
    """
    
    def __init__(self, data_dir: str = "trading_data"):
        """Initialize professional dashboard"""
        if not DASH_AVAILABLE:
            raise ImportError("Dash required: pip install dash dash-bootstrap-components plotly")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.alpaca = get_client()
        
        # Create Dash app with custom styling
        self.app = Dash(
            __name__,
            external_stylesheets=[
                dbc.themes.CYBORG,  # Dark base theme
                "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap",
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"
            ],
            title="WawaTrader Beta",
            meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
        )
        
        # Add custom CSS
        self._add_custom_styles()
        
        # Build professional layout
        self._build_professional_layout()
        
        # Register advanced callbacks
        self._register_professional_callbacks()
        
        logger.info("🚀 Professional Dashboard initialized")
    
    def _add_custom_styles(self):
        """Add custom CSS for professional trading interface"""
        self.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <style>
                    /* Professional Dark Trading Theme */
                    :root {
                        --bg-primary: #0a0a0a;
                        --bg-secondary: #1a1a1a;
                        --bg-tertiary: #2a2a2a;
                        --border-color: #333333;
                        --text-primary: #ffffff;
                        --text-secondary: #cccccc;
                        --text-muted: #888888;
                        --accent-green: #00ff88;
                        --accent-red: #ff4444;
                        --accent-blue: #00aaff;
                        --accent-orange: #ffaa00;
                        --accent-purple: #aa44ff;
                        --glass-bg: rgba(42, 42, 42, 0.8);
                        --glass-border: rgba(255, 255, 255, 0.1);
                    }
                    
                    body {
                        background: var(--bg-primary);
                        color: var(--text-primary);
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                    }
                    
                    /* Professional Container */
                    .professional-container {
                        background: var(--bg-primary);
                        min-height: 100vh;
                        padding: 0;
                        max-width: 100% !important;
                        margin: 0;
                    }
                    
                    /* Glass Cards */
                    .glass-card {
                        background: var(--glass-bg);
                        border: 1px solid var(--glass-border);
                        border-radius: 8px;
                        backdrop-filter: blur(10px);
                        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                    }
                    
                    /* Header Bar */
                    .header-bar {
                        background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
                        border-bottom: 2px solid var(--accent-blue);
                        padding: 14px 24px;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        position: sticky;
                        top: 0;
                        z-index: 1000;
                        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
                        min-height: 60px;
                    }
                    
                    .header-title {
                        font-size: 24px;
                        font-weight: bold;
                        color: var(--accent-blue);
                        text-shadow: 0 0 10px rgba(0, 170, 255, 0.3);
                    }
                    
                    .header-status {
                        display: flex;
                        gap: 20px;
                        align-items: center;
                    }
                    
                    .status-badge {
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 500;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    
                    .status-live {
                        background: linear-gradient(45deg, var(--accent-green), #00cc66);
                        color: var(--bg-primary);
                        animation: pulse 2s infinite;
                    }
                    
                    @keyframes pulse {
                        0%, 100% { opacity: 1; }
                        50% { opacity: 0.7; }
                    }
                    
                    /* Main Grid Layout - Optimized for laptop screens */
                    .main-grid {
                        display: grid;
                        grid-template-columns: minmax(300px, 24%) 1fr minmax(260px, 19%);
                        grid-template-rows: minmax(380px, 60%) minmax(200px, 40%);
                        gap: 12px;
                        padding: 12px;
                        height: calc(100vh - 90px);
                        max-width: 100vw;
                        overflow: hidden;
                    }
                    
                    @media (max-width: 1400px) {
                        .main-grid {
                            grid-template-columns: minmax(280px, 25%) 1fr minmax(240px, 21%);
                            grid-template-rows: minmax(340px, 62%) minmax(180px, 38%);
                            gap: 10px;
                            padding: 10px;
                        }
                    }
                    
                    @media (max-width: 1200px) {
                        .main-grid {
                            grid-template-columns: 1fr 1fr;
                            grid-template-rows: minmax(300px, 40%) minmax(200px, 30%) minmax(200px, 30%);
                            height: auto;
                        }
                    }
                    
                    @media (max-width: 768px) {
                        .main-grid {
                            grid-template-columns: 1fr;
                            grid-template-rows: auto;
                            padding: 8px;
                            gap: 8px;
                            height: auto;
                        }
                    }
                    
                    /* LLM Mind Panel */
                    .llm-mind {
                        grid-column: 1;
                        grid-row: 1 / -1;
                        background: var(--glass-bg);
                        border: 1px solid var(--glass-border);
                        border-radius: 8px;
                        padding: 20px;
                        overflow: hidden;
                        min-height: 0;
                        max-height: calc(100vh - 130px);
                        position: relative;
                        display: flex;
                        flex-direction: column;
                    }
                    
                    .llm-thought {
                        background: rgba(0, 170, 255, 0.1);
                        border-left: 3px solid var(--accent-blue);
                        padding: 12px;
                        margin: 8px 0;
                        border-radius: 0 6px 6px 0;
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 11px;
                        line-height: 1.4;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        white-space: pre-wrap;
                        /* Removed max-height to show full text */
                    }
                    
                    .confidence-bar {
                        background: var(--bg-tertiary);
                        height: 6px;
                        border-radius: 3px;
                        margin: 8px 0;
                        overflow: hidden;
                    }
                    
                    .confidence-fill {
                        height: 100%;
                        border-radius: 3px;
                        transition: width 0.3s ease;
                    }
                    
                    /* LLM Mind Panel specific styling */
                    .llm-mind-header {
                        position: sticky;
                        top: 0;
                        background: var(--glass-bg);
                        padding-bottom: 8px;
                        margin-bottom: 12px;
                        border-bottom: 1px solid var(--glass-border);
                        z-index: 10;
                    }
                    
                    .llm-thoughts-container {
                        height: calc(100% - 60px);
                        overflow-y: auto;
                        overflow-x: hidden;
                        padding-right: 8px;
                        scrollbar-width: thin;
                        scrollbar-color: var(--accent-blue) var(--bg-secondary);
                    }
                    
                    .llm-thoughts-container::-webkit-scrollbar {
                        width: 8px;
                    }
                    
                    .llm-thoughts-container::-webkit-scrollbar-track {
                        background: var(--bg-secondary);
                        border-radius: 4px;
                    }
                    
                    .llm-thoughts-container::-webkit-scrollbar-thumb {
                        background: var(--accent-blue);
                        border-radius: 4px;
                        border: 1px solid var(--bg-secondary);
                    }
                    
                    .llm-thoughts-container::-webkit-scrollbar-thumb:hover {
                        background: var(--accent-green);
                    }
                    
                    /* Chart Panel */
                    .chart-panel {
                        background: var(--glass-bg);
                        border: 1px solid var(--glass-border);
                        border-radius: 8px;
                        overflow: hidden;
                        min-width: 0;
                        min-height: 400px;  /* Minimum height for chart visibility */
                        grid-column: 2;
                        grid-row: 1;
                        display: flex;
                        flex-direction: column;
                    }
                    
                    /* Market Intel */
                    .market-intel {
                        background: var(--glass-bg);
                        border: 1px solid var(--glass-border);
                        border-radius: 8px;
                        padding: 20px;
                        overflow-y: auto;
                        min-height: 0;
                        grid-column: 3;
                        grid-row: 1 / -1;
                        max-height: calc(100vh - 130px);
                    }
                    
                    /* Metric Cards - Optimized for laptop screens */
                    .metric-card {
                        background: var(--bg-secondary);
                        border: 1px solid var(--border-color);
                        border-radius: 6px;
                        padding: 8px 12px;
                        margin: 4px 0;
                        transition: all 0.2s ease;
                        min-height: 50px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                    }
                    
                    .metric-card:hover {
                        border-color: var(--accent-blue);
                        box-shadow: 0 2px 8px rgba(0, 170, 255, 0.2);
                    }
                    
                    .metric-value {
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 16px;
                        font-weight: bold;
                        margin: 2px 0;
                        line-height: 1.2;
                    }
                    
                    .metric-label {
                        font-size: 10px;
                        color: var(--text-muted);
                        text-transform: uppercase;
                        letter-spacing: 0.3px;
                        margin-bottom: 2px;
                    }
                    
                    /* Compact layout for bottom panels */
                    .compact-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 8px;
                        margin-bottom: 12px;
                    }
                    
                    .compact-metric {
                        background: var(--bg-secondary);
                        border: 1px solid var(--border-color);
                        border-radius: 4px;
                        padding: 6px 8px;
                        text-align: center;
                    }
                    
                    .compact-value {
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 14px;
                        font-weight: bold;
                        margin: 1px 0;
                    }
                    
                    .compact-label {
                        font-size: 9px;
                        color: var(--text-muted);
                        text-transform: uppercase;
                        letter-spacing: 0.2px;
                    }
                    
                    .positive { color: var(--accent-green); }
                    .negative { color: var(--accent-red); }
                    .neutral { color: var(--text-secondary); }
                    
                    /* Configuration Modal */
                    .config-button {
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border-color);
                        border-radius: 6px;
                        padding: 8px 12px;
                        cursor: pointer;
                        transition: all 0.2s ease;
                        color: var(--text-primary);
                        font-size: 14px;
                        margin-left: 12px;
                    }
                    
                    .config-button:hover {
                        background: var(--accent-blue);
                        border-color: var(--accent-blue);
                        color: var(--bg-primary);
                        transform: translateY(-1px);
                    }
                    
                    .config-button:focus {
                        outline: 2px solid var(--accent-blue);
                    }
                    
                    .config-modal {
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.8);
                        backdrop-filter: blur(4px);
                        z-index: 10000;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    
                    .config-content {
                        background: var(--bg-secondary);
                        border: 2px solid var(--accent-blue);
                        border-radius: 12px;
                        width: 90%;
                        max-width: 1000px;
                        height: 80vh;
                        max-height: 800px;
                        overflow: hidden;
                        display: flex;
                        flex-direction: column;
                        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7);
                    }
                    
                    .config-header {
                        background: linear-gradient(135deg, var(--bg-tertiary), var(--accent-blue));
                        padding: 16px 24px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-bottom: 1px solid var(--glass-border);
                    }
                    
                    .config-title {
                        color: var(--text-primary);
                        font-size: 20px;
                        font-weight: bold;
                        margin: 0;
                    }
                    
                    .config-close {
                        background: none;
                        border: none;
                        color: var(--text-primary);
                        font-size: 24px;
                        cursor: pointer;
                        padding: 4px 8px;
                        border-radius: 4px;
                        transition: background 0.2s;
                    }
                    
                    .config-close:hover {
                        background: rgba(255, 255, 255, 0.1);
                    }
                    
                    .config-tabs {
                        background: var(--bg-tertiary);
                        display: flex;
                        border-bottom: 1px solid var(--glass-border);
                    }
                    
                    .config-tab {
                        padding: 12px 24px;
                        cursor: pointer;
                        border-bottom: 3px solid transparent;
                        color: var(--text-muted);
                        font-weight: 500;
                        transition: all 0.2s;
                        flex: 1;
                        text-align: center;
                    }
                    
                    .config-tab:hover {
                        color: var(--text-primary);
                        background: var(--bg-secondary);
                    }
                    
                    .config-tab.active {
                        color: var(--accent-blue);
                        border-bottom-color: var(--accent-blue);
                        background: var(--bg-secondary);
                    }
                    
                    .config-body {
                        flex: 1;
                        overflow-y: auto;
                        padding: 24px;
                    }
                    
                    .config-section {
                        margin-bottom: 32px;
                    }
                    
                    .config-section-title {
                        color: var(--accent-blue);
                        font-size: 16px;
                        font-weight: bold;
                        margin-bottom: 16px;
                        border-bottom: 1px solid var(--glass-border);
                        padding-bottom: 8px;
                    }
                    
                    .config-field {
                        margin-bottom: 20px;
                    }
                    
                    .config-label {
                        display: block;
                        color: var(--text-primary);
                        font-size: 13px;
                        font-weight: 500;
                        margin-bottom: 6px;
                    }
                    
                    .config-input, .config-textarea {
                        width: 100%;
                        background: var(--bg-primary);
                        border: 1px solid var(--border-color);
                        border-radius: 6px;
                        padding: 10px 12px;
                        color: var(--text-primary);
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 12px;
                        line-height: 1.4;
                        transition: border-color 0.2s;
                        box-sizing: border-box;
                    }
                    
                    .config-textarea {
                        resize: vertical;
                        min-height: 120px;
                        max-height: 300px;
                    }
                    
                    .config-input:focus, .config-textarea:focus {
                        outline: none;
                        border-color: var(--accent-blue);
                        box-shadow: 0 0 0 2px rgba(0, 170, 255, 0.2);
                    }
                    
                    .config-help {
                        font-size: 11px;
                        color: var(--text-muted);
                        margin-top: 4px;
                        line-height: 1.3;
                    }
                    
                    .config-save-btn {
                        background: var(--accent-green);
                        color: var(--bg-primary);
                        border: none;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.2s;
                        margin-right: 12px;
                    }
                    
                    .config-save-btn:hover {
                        background: var(--accent-blue);
                        transform: translateY(-1px);
                    }
                    
                    .config-reset-btn {
                        background: var(--accent-red);
                        color: var(--text-primary);
                        border: none;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: bold;
                        cursor: pointer;
                        transition: all 0.2s;
                    }
                    
                    .config-reset-btn:hover {
                        background: #cc3333;
                        transform: translateY(-1px);
                    }
                    
                    .config-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                    }
                    
                    @media (max-width: 768px) {
                        .config-content {
                            width: 95%;
                            height: 90vh;
                        }
                        
                        .config-grid {
                            grid-template-columns: 1fr;
                        }
                        
                        .config-tabs {
                            flex-direction: column;
                        }
                        
                        .config-tab {
                            text-align: left;
                        }
                    }
                    
                    /* Scrollbars */
                    ::-webkit-scrollbar {
                        width: 8px;
                    }
                    
                    ::-webkit-scrollbar-track {
                        background: var(--bg-secondary);
                    }
                    
                    ::-webkit-scrollbar-thumb {
                        background: var(--border-color);
                        border-radius: 4px;
                    }
                    
                    ::-webkit-scrollbar-thumb:hover {
                        background: var(--accent-blue);
                    }
                    
                    /* Tables */
                    .professional-table {
                        background: var(--bg-secondary);
                        color: var(--text-primary);
                        border: none;
                    }
                    
                    .professional-table th {
                        background: var(--bg-tertiary);
                        color: var(--text-primary);
                        border: none;
                        font-weight: 600;
                        font-size: 11px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }
                    
                    .professional-table td {
                        background: var(--bg-secondary);
                        color: var(--text-primary);
                        border: none;
                        font-family: 'JetBrains Mono', monospace;
                        font-size: 12px;
                    }
                    
                    /* Alerts */
                    .alert-panel {
                        position: fixed;
                        top: 80px;
                        right: 20px;
                        width: 300px;
                        z-index: 2000;
                    }
                    
                    .alert-item {
                        background: var(--glass-bg);
                        border: 1px solid var(--accent-orange);
                        border-radius: 6px;
                        padding: 12px;
                        margin: 8px 0;
                        animation: slideIn 0.3s ease;
                    }
                    
                    @keyframes slideIn {
                        from { transform: translateX(100%); }
                        to { transform: translateX(0); }
                    }
                    
                    /* Responsive Design */
                    /* Improved responsive layout for LLM positioning */
                    @media (max-width: 1200px) {
                        .llm-mind {
                            grid-column: 1;
                            grid-row: 1;
                            max-height: 350px;
                        }
                        
                        .chart-panel {
                            grid-column: 2;
                            grid-row: 1;
                        }
                        
                        .market-intel {
                            grid-column: 1 / -1;
                            grid-row: 2;
                            max-height: 300px;
                        }
                    }
                    
                    @media (max-width: 768px) {
                        .main-grid {
                            grid-template-columns: 1fr;
                            grid-template-rows: auto auto auto auto auto;
                            padding: 8px;
                            gap: 8px;
                        }
                        
                        .header-bar {
                            padding: 8px 12px;
                        }
                        
                        .header-title {
                            font-size: 18px;
                        }
                        
                        .llm-mind, .market-intel {
                            padding: 12px;
                            grid-column: 1;
                            grid-row: auto;
                            max-height: 250px;
                        }
                        
                        .chart-panel {
                            grid-column: 1;
                            grid-row: auto;
                            min-height: 300px;
                        }
                    }
                </style>
                <script>
                    // Modal and tab management
                    function openConfigModal() {
                        document.getElementById('config-modal').style.display = 'flex';
                        console.log('Config modal opened');
                    }
                    
                    function closeConfigModal() {
                        document.getElementById('config-modal').style.display = 'none';
                        console.log('Config modal closed');
                    }
                    
                    function switchTab(activeTab, inactiveTab) {
                        // Update tab classes
                        document.getElementById(activeTab).className = 'config-tab active';
                        document.getElementById(inactiveTab).className = 'config-tab';
                    }
                    
                    // Initialize when DOM is ready
                    document.addEventListener('DOMContentLoaded', function() {
                        // Add click handlers
                        const configBtn = document.getElementById('config-button');
                        const closeBtn = document.getElementById('config-close');
                        const llmTab = document.getElementById('llm-tab');
                        const traderTab = document.getElementById('trader-tab');
                        
                        if (configBtn) {
                            configBtn.addEventListener('click', openConfigModal);
                        }
                        
                        if (closeBtn) {
                            closeBtn.addEventListener('click', closeConfigModal);
                        }
                        
                        // Close modal when clicking backdrop
                        const modal = document.getElementById('config-modal');
                        if (modal) {
                            modal.addEventListener('click', function(e) {
                                if (e.target === modal) {
                                    closeConfigModal();
                                }
                            });
                        }
                        
                        console.log('Config modal handlers initialized');
                    });
                </script>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
    
    def _build_professional_layout(self):
        """Build the professional trading interface layout"""
        
        self.app.layout = html.Div([
            # Auto-refresh components
            dcc.Interval(
                id='main-interval',
                interval=5000,  # 5 seconds for professional real-time updates
                n_intervals=0
            ),
            
            dcc.Interval(
                id='llm-interval', 
                interval=2000,  # 2 seconds for LLM thoughts
                n_intervals=0
            ),
            
            # Header Bar
            html.Div([
                html.Div([
                    html.I(className="fas fa-robot", style={"marginRight": "8px"}),
                    "WawaTrader Beta"
                ], className="header-title"),
                
                html.Div([
                    html.Div("LIVE", className="status-badge status-live"),
                    html.Div(id="system-time", className="status-badge", 
                            style={"background": "var(--bg-tertiary)", "color": "var(--text-secondary)"}),
                    html.Div(id="pnl-header", className="status-badge",
                            style={"background": "var(--bg-tertiary)", "fontFamily": "JetBrains Mono"}),
                    html.Button([
                        html.I(className="fas fa-cog", style={"marginRight": "6px"}),
                        "Config"
                    ], 
                    id="config-button", 
                    className="config-button")
                ], className="header-status")
            ], className="header-bar"),
            
            # Main Grid Layout
            html.Div([
                # LLM Mind Panel (Left)
                html.Div([
                    html.Div([
                        html.I(className="fas fa-brain", style={"marginRight": "8px", "color": "var(--accent-blue)"}),
                        html.H5("LLM Data", style={"margin": "0", "color": "var(--accent-blue)", "fontSize": "14px"}),
                        html.Div("🧠", style={"marginLeft": "auto", "fontSize": "16px"})
                    ], className="llm-mind-header", style={"display": "flex", "alignItems": "center"}),
                    
                    html.Div(id="llm-thoughts", className="llm-thoughts-container", children=[
                        html.Div([
                            html.Div("💭 Analyzing market conditions...", className="llm-thought"),
                            html.Div([
                                html.Div("Confidence", style={"fontSize": "10px", "color": "var(--text-muted)", "marginBottom": "4px"}),
                                html.Div(className="confidence-bar", children=[
                                    html.Div(className="confidence-fill", style={
                                        "width": "75%", 
                                        "background": "linear-gradient(90deg, var(--accent-green), var(--accent-blue))"
                                    })
                                ])
                            ], style={"marginTop": "8px"})
                        ])
                    ])
                ], className="llm-mind"),
                
                # Chart Panel (Center)
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-candlestick", style={"marginRight": "8px", "color": "var(--accent-blue)"}),
                        html.H5("AAPL - Live Trading Chart", style={"margin": "0", "color": "var(--accent-blue)", "fontSize": "14px"}),
                        html.Div("📊 IEX Real-Time Data", style={"fontSize": "10px", "color": "var(--text-muted)", "marginLeft": "auto"})
                    ], style={"display": "flex", "alignItems": "center", "padding": "12px 16px", "borderBottom": "1px solid var(--border-color)"}),
                    
                    dcc.Graph(
                        id="main-chart",
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d'],
                            'responsive': True  # Enable responsive sizing
                        },
                        style={
                            "height": "calc(100% - 50px)", 
                            "width": "100%",
                            "minHeight": "350px",  # Ensure minimum chart height
                            "flex": "1"  # Take up available space
                        }
                    )
                ], className="chart-panel"),
                
                # Market Intel Panel (Right)
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-line", style={"marginRight": "8px", "color": "var(--accent-green)"}),
                        html.H5("Market Intel", style={"margin": "0", "color": "var(--accent-green)"})
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "16px"}),
                    
                    html.Div(id="market-screener")
                ], className="market-intel"),
                
                # Performance Panel (Bottom Left)
                html.Div([
                    html.Div([
                        html.I(className="fas fa-chart-area", style={"marginRight": "8px", "color": "var(--accent-orange)"}),
                        html.H5("Performance", style={"margin": "0", "color": "var(--accent-orange)", "fontSize": "14px"})
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}),
                    
                    html.Div(id="performance-metrics", style={"overflowY": "auto", "height": "calc(100% - 40px)"})
                ], className="glass-card", style={"gridColumn": "1", "gridRow": "2", "padding": "18px", "minHeight": "0"}),
                
                # Positions Panel (Bottom Center)  
                html.Div([
                    html.Div([
                        html.I(className="fas fa-briefcase", style={"marginRight": "8px", "color": "var(--accent-purple)"}),
                        html.H5("Positions", style={"margin": "0", "color": "var(--accent-purple)", "fontSize": "14px"})
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}),
                    
                    html.Div(id="positions-panel", style={"overflowY": "auto", "height": "calc(100% - 40px)"})
                ], className="glass-card", style={"gridColumn": "2", "gridRow": "2", "padding": "18px", "minHeight": "0"}),
                
                # Conversations Panel (Bottom Right)
                html.Div([
                    html.Div([
                        html.I(className="fas fa-robot", style={"marginRight": "8px", "color": "var(--accent-red)"}),
                        html.H5("AI Decisions", style={"margin": "0", "color": "var(--accent-red)", "fontSize": "14px"})
                    ], style={"display": "flex", "alignItems": "center", "marginBottom": "12px"}),
                    
                    html.Div(id="conversations-panel", style={"overflowY": "auto", "height": "calc(100% - 40px)"})
                ], className="glass-card", style={"gridColumn": "3", "gridRow": "2", "padding": "18px", "minHeight": "0"}),
                
            ], className="main-grid"),
            
            # Alert Panel (Fixed position)
            html.Div(id="alert-panel", className="alert-panel"),
            
            # Configuration Modal - Using DBC Modal for better compatibility
            dbc.Modal([
                dbc.ModalHeader([
                    dbc.ModalTitle("⚙️ WawaTrader Configuration")
                ]),
                dbc.ModalBody([
                    # Tabs
                    dbc.Tabs([
                        dbc.Tab(label="🤖 LLM Settings", tab_id="llm-tab", active_tab_style={"backgroundColor": "#00aaff"}),
                        dbc.Tab(label="📈 Trader Settings", tab_id="trader-tab")
                    ], id="config-tabs", active_tab="llm-tab"),
                    
                    html.Br(),
                    
                    # Content
                    html.Div(id="config-content")
                ])
            ], id="config-modal", is_open=False, size="xl", backdrop=True) if MODAL_AVAILABLE else 
            
            # Fallback simple modal for systems without DBC
            html.Div(id="config-modal", className="config-modal", style={"display": "none"}, children=[
                html.Div(className="config-content", children=[
                    # Header
                    html.Div(className="config-header", children=[
                        html.H2("⚙️ WawaTrader Configuration", className="config-title"),
                        html.Button("×", 
                                  id="config-close", 
                                  className="config-close")
                    ]),
                    
                    # Tabs
                    html.Div(className="config-tabs", children=[
                        html.Button("🤖 LLM Settings", 
                                  id="llm-tab", 
                                  className="config-tab active"),
                        html.Button("📈 Trader Settings", 
                                  id="trader-tab", 
                                  className="config-tab")
                    ]),
                    
                    # Content
                    html.Div(id="config-content", className="config-body", children=[])
                ])
            ])
            
        ], className="professional-container")
    
    def _register_professional_callbacks(self):
        """Register callbacks for professional dashboard"""
        
        @self.app.callback(
            [Output('system-time', 'children'),
             Output('pnl-header', 'children'),
             Output('pnl-header', 'style')],
            [Input('main-interval', 'n_intervals')]
        )
        def update_header(n):
            """Update header with time and P&L"""
            current_time = datetime.now().strftime("%H:%M:%S")
            
            try:
                # Get account info
                account = self.alpaca.get_account()
                
                # Handle both dict and object responses
                if isinstance(account, dict):
                    equity = float(account.get('equity', 0))
                    last_equity = float(account.get('last_equity', equity))
                    buying_power = float(account.get('buying_power', 0))
                else:
                    equity = float(account.equity)
                    last_equity = float(account.last_equity)
                    buying_power = float(account.buying_power)
                
                pnl = equity - last_equity
                pnl_pct = (pnl / last_equity) * 100 if last_equity > 0 else 0
                
                pnl_text = f"P&L: {'+' if pnl >= 0 else ''}{pnl:,.2f} ({pnl_pct:+.2f}%)"
                pnl_color = "var(--accent-green)" if pnl >= 0 else "var(--accent-red)"
                
                pnl_style = {
                    "background": "var(--bg-tertiary)", 
                    "fontFamily": "JetBrains Mono",
                    "color": pnl_color,
                    "fontWeight": "bold"
                }
                
                return current_time, pnl_text, pnl_style
                
            except Exception as e:
                logger.error(f"Error updating header: {e}")
                return current_time, "P&L: --", {"background": "var(--bg-tertiary)", "color": "var(--text-muted)"}
        
        @self.app.callback(
            Output('main-chart', 'figure'),
            [Input('main-interval', 'n_intervals')]
        )
        def update_main_chart(n):
            """Update main candlestick chart with professional styling"""
            try:
                # Get price data for primary symbol (AAPL as example)
                symbol = "AAPL"
                
                # Try to get recent data, fall back to daily data if subscription doesn't allow
                bars = None
                try:
                    bars = self.alpaca.get_bars(symbol, limit=100, timeframe='1Day')  # Start with daily for reliability
                    logger.debug(f"Retrieved {len(bars) if not bars.empty else 0} daily bars for {symbol}")
                    if bars.empty:
                        raise ValueError("Empty daily data")
                except Exception as api_error:
                    logger.error(f"Daily data not available: {api_error}")
                    try:
                        # Fallback to a smaller dataset
                        bars = self.alpaca.get_bars(symbol, limit=30, timeframe='1Day')
                        logger.debug(f"Fallback: Retrieved {len(bars) if not bars.empty else 0} bars")
                        if bars.empty:
                            raise ValueError("Empty fallback data")
                    except Exception as fallback_error:
                        logger.error(f"No data available: {fallback_error}")
                        return self._create_empty_chart(f"No market data for {symbol}")
                
                if bars is None or bars.empty:
                    return self._create_empty_chart("No data available")
                
                # Create professional candlestick chart
                fig = go.Figure()
                
                # Add candlestick
                fig.add_trace(go.Candlestick(
                    x=bars.index,
                    open=bars['open'],
                    high=bars['high'],
                    low=bars['low'],
                    close=bars['close'],
                    name=symbol,
                    increasing_line_color='#00ff88',
                    decreasing_line_color='#ff4444',
                    increasing_fillcolor='rgba(0, 255, 136, 0.3)',
                    decreasing_fillcolor='rgba(255, 68, 68, 0.3)'
                ))
                
                # Add volume
                fig.add_trace(go.Bar(
                    x=bars.index,
                    y=bars['volume'],
                    name='Volume',
                    yaxis='y2',
                    marker_color='rgba(0, 170, 255, 0.3)',
                    showlegend=False
                ))
                
                # Professional chart styling with improved responsive layout
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#ffffff', family='JetBrains Mono', size=11),
                    xaxis=dict(
                        gridcolor='rgba(255,255,255,0.08)',
                        showgrid=True,
                        zeroline=False,
                        color='#cccccc',
                        showticklabels=True,
                        tickfont=dict(size=10),
                        fixedrange=False  # Allow zooming
                    ),
                    yaxis=dict(
                        title=dict(text="Price ($)", font=dict(size=11)),
                        gridcolor='rgba(255,255,255,0.08)', 
                        showgrid=True,
                        zeroline=False,
                        color='#cccccc',
                        side='right',
                        tickfont=dict(size=10),
                        tickformat=',.2f',
                        fixedrange=False  # Allow zooming
                    ),
                    yaxis2=dict(
                        title=dict(text="Volume", font=dict(size=10)),
                        overlaying='y',
                        side='left',
                        showgrid=False,
                        color='#888888',
                        tickfont=dict(size=9),
                        showticklabels=True,
                        fixedrange=False
                    ),
                    showlegend=False,
                    margin=dict(l=60, r=60, t=10, b=30),  # Reduced margins for better space usage
                    hovermode='x unified',
                    hoverlabel=dict(
                        bgcolor='rgba(42, 42, 42, 0.9)',
                        bordercolor='rgba(255, 255, 255, 0.2)',
                        font=dict(color='white', family='JetBrains Mono', size=10)
                    ),
                    autosize=True,  # Enable automatic sizing
                    height=None,    # Let container control height
                    dragmode='pan'  # Set default drag mode
                )
                
                # Add LLM decision annotations (example)
                fig.add_annotation(
                    x=bars.index[-10],
                    y=bars['high'].iloc[-10],
                    text="🤖 BUY Signal<br>Confidence: 85%",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor='#00ff88',
                    bgcolor='rgba(0, 255, 136, 0.1)',
                    bordercolor='#00ff88',
                    font=dict(color='#00ff88', size=10)
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating main chart: {e}")
                return self._create_empty_chart("Chart Error")
        
        @self.app.callback(
            Output('llm-thoughts', 'children'),
            [Input('llm-interval', 'n_intervals')]
        )
        def update_llm_thoughts(n):
            """Update LLM thought process display"""
            try:
                # Get recent LLM conversations
                conversations = self._get_llm_conversations()
                
                if not conversations:
                    return [
                        html.Div([
                            html.Div("💭 Waiting for LLM analysis...", className="llm-thought"),
                            html.Div([
                                html.Div("System Ready", style={"fontSize": "11px", "color": "var(--text-muted)"}),
                                html.Div(className="confidence-bar", children=[
                                    html.Div(className="confidence-fill", style={
                                        "width": "100%", 
                                        "background": "var(--accent-blue)"
                                    })
                                ])
                            ])
                        ])
                    ]
                
                # Show latest thoughts
                thoughts = []
                for conv in conversations[-5:]:  # Last 5 conversations
                    confidence = 75  # Default confidence
                    if 'response' in conv:
                        try:
                            response_data = json.loads(conv['response'])
                            confidence = response_data.get('confidence', 75)
                        except:
                            pass
                    
                    thought_text = f"💭 {conv.get('symbol', 'Market')}: "
                    if 'prompt' in conv and len(conv['prompt']) > 0:
                        # Show full prompt text
                        thought_text += conv['prompt']
                    else:
                        thought_text += "Analyzing market conditions..."
                    
                    # Add response if available
                    if 'response' in conv and len(conv['response']) > 0:
                        thought_text += f"\n\n🤖 Response: {conv['response']}"
                    
                    confidence_color = "var(--accent-green)" if confidence >= 70 else "var(--accent-orange)" if confidence >= 50 else "var(--accent-red)"
                    
                    thoughts.append(
                        html.Div([
                            html.Div(thought_text, className="llm-thought"),
                            html.Div([
                                html.Div(f"Confidence: {confidence}%", style={"fontSize": "11px", "color": "var(--text-muted)"}),
                                html.Div(className="confidence-bar", children=[
                                    html.Div(className="confidence-fill", style={
                                        "width": f"{confidence}%", 
                                        "background": confidence_color
                                    })
                                ])
                            ])
                        ])
                    )
                
                return thoughts
                
            except Exception as e:
                logger.error(f"Error updating LLM thoughts: {e}")
                return [html.Div("🔧 LLM system error", className="llm-thought")]
        
        @self.app.callback(
            Output('market-screener', 'children'),
            [Input('main-interval', 'n_intervals')]
        )
        def update_market_screener(n):
            """Update market intelligence screener"""
            try:
                # Get market intelligence data
                intelligence_data = self._get_latest_market_intelligence()
                
                if not intelligence_data:
                    return [
                        html.Div([
                            html.Div("🔍 Scanning markets...", className="metric-label"),
                            html.Div("--", className="metric-value neutral")
                        ], className="metric-card")
                    ]
                
                # Create metric cards
                cards = []
                
                # Market sentiment
                sentiment = intelligence_data.get('market_sentiment', 'neutral')
                confidence = intelligence_data.get('confidence', 0)
                sentiment_color = "positive" if sentiment == "bullish" else "negative" if sentiment == "bearish" else "neutral"
                
                cards.append(
                    html.Div([
                        html.Div("Market Sentiment", className="metric-label"),
                        html.Div(f"{sentiment.title()} ({confidence}%)", className=f"metric-value {sentiment_color}")
                    ], className="metric-card")
                )
                
                # Opportunities
                opportunities = intelligence_data.get('opportunities', [])
                cards.append(
                    html.Div([
                        html.Div("Opportunities", className="metric-label"),
                        html.Div(str(len(opportunities)), className="metric-value positive")
                    ], className="metric-card")
                )
                
                # Risk Level
                risks = intelligence_data.get('risks', [])
                risk_count = len(risks)
                risk_color = "negative" if risk_count > 3 else "neutral" if risk_count > 1 else "positive"
                
                cards.append(
                    html.Div([
                        html.Div("Risk Alerts", className="metric-label"),
                        html.Div(str(risk_count), className=f"metric-value {risk_color}")
                    ], className="metric-card")
                )
                
                # Show top opportunities
                if opportunities:
                    cards.append(html.Hr(style={"borderColor": "var(--border-color)", "margin": "16px 0"}))
                    cards.append(
                        html.Div("🎯 Top Opportunities", style={"color": "var(--accent-green)", "fontWeight": "bold", "marginBottom": "8px"})
                    )
                    
                    for opp in opportunities[:3]:
                        cards.append(
                            html.Div([
                                html.Div(str(opp), 
                                        style={"fontSize": "11px", "color": "var(--text-secondary)", "padding": "3px 0", "lineHeight": "1.3"})
                            ])
                        )
                
                return cards
                
            except Exception as e:
                logger.error(f"Error updating market screener: {e}")
                return [html.Div("🔧 Screener error", className="metric-card")]
        
        @self.app.callback(
            [Output('performance-metrics', 'children'),
             Output('positions-panel', 'children'),
             Output('conversations-panel', 'children')],
            [Input('main-interval', 'n_intervals')]
        )
        def update_bottom_panels(n):
            """Update performance, positions, and conversations panels"""
            try:
                # Performance Metrics
                account = self.alpaca.get_account()
                
                # Handle both dict and object responses
                if isinstance(account, dict):
                    equity = float(account.get('equity', 100000))
                    last_equity = float(account.get('last_equity', equity))
                    buying_power = float(account.get('buying_power', 0))
                else:
                    equity = float(account.equity)
                    last_equity = float(account.last_equity)
                    buying_power = float(account.buying_power)
                
                pnl = equity - last_equity
                
                # Compact performance layout
                performance = [
                    html.Div([
                        html.Div([
                            html.Div("Portfolio", className="compact-label"),
                            html.Div(f"${equity:,.0f}", className="compact-value neutral")
                        ], className="compact-metric"),
                        html.Div([
                            html.Div("P&L Today", className="compact-label"),
                            html.Div(f"${pnl:+,.0f}", className=f"compact-value {'positive' if pnl >= 0 else 'negative'}")
                        ], className="compact-metric")
                    ], className="compact-grid"),
                    
                    html.Div([
                        html.Div([
                            html.Div("Buying Power", className="compact-label"),
                            html.Div(f"${buying_power:,.0f}", className="compact-value neutral")
                        ], className="compact-metric"),
                        html.Div([
                            html.Div("Cash Avail", className="compact-label"),
                            html.Div(f"${buying_power*0.25:,.0f}", className="compact-value neutral")  # Rough estimate
                        ], className="compact-metric")
                    ], className="compact-grid")
                ]
                
                # Positions
                try:
                    positions = self.alpaca.get_positions()
                    position_cards = []
                    
                    if positions and len(positions) > 0:
                        for pos in positions[:5]:  # Top 5 positions
                            # Handle both dict and object responses
                            if isinstance(pos, dict):
                                symbol = pos.get('symbol', 'UNKNOWN')
                                qty = pos.get('qty', 0)
                                pnl = float(pos.get('unrealized_pl', 0))
                            else:
                                symbol = pos.symbol
                                qty = pos.qty
                                pnl = float(pos.unrealized_pl)
                                
                            pnl_color = "positive" if pnl >= 0 else "negative"
                            
                            position_cards.append(
                                html.Div([
                                    html.Div([
                                        html.Span(symbol, style={"fontWeight": "bold", "fontSize": "12px", "color": "var(--accent-blue)"}),
                                        html.Span(f" {qty}", style={"fontSize": "10px", "color": "var(--text-muted)", "marginLeft": "6px"})
                                    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                                    html.Div(f"${pnl:+,.0f}", className=f"compact-value {pnl_color}", style={"fontSize": "11px", "textAlign": "right"})
                                ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "borderRadius": "4px", "padding": "6px 8px", "margin": "3px 0"})
                            )
                    else:
                        position_cards = [
                            html.Div([
                                html.Div("No active positions", style={"fontSize": "11px", "color": "var(--text-muted)", "textAlign": "center", "padding": "12px"})
                            ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "borderRadius": "4px"})
                        ]
                except Exception as pos_error:
                    logger.warning(f"Error getting positions: {pos_error}")
                    position_cards = [
                        html.Div([
                            html.Div("Positions unavailable", style={"fontSize": "11px", "color": "var(--accent-red)", "textAlign": "center", "padding": "12px"})
                        ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "borderRadius": "4px"})
                    ]
                
                # Conversations
                conversations = self._get_llm_conversations()[-3:]  # Last 3 conversations
                conv_cards = []
                
                for conv in conversations:
                    symbol = conv.get('symbol', 'Unknown')
                    timestamp = conv.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M")
                        except:
                            time_str = timestamp[:5] if len(timestamp) > 5 else timestamp
                    else:
                        time_str = "N/A"
                    
                    # Try to extract action from response
                    action = "ANALYZE"
                    if 'response' in conv:
                        try:
                            response_data = json.loads(conv['response'])
                            action = response_data.get('action', 'ANALYZE').upper()
                        except:
                            pass
                    
                    action_color = "positive" if action == "BUY" else "negative" if action == "SELL" else "neutral"
                    
                    conv_cards.append(
                        html.Div([
                            html.Div([
                                html.Span(f"{symbol}", style={"fontWeight": "bold", "fontSize": "11px", "color": "var(--accent-blue)"}),
                                html.Span(f"{time_str}", style={"fontSize": "9px", "color": "var(--text-muted)", "marginLeft": "auto"})
                            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                            html.Div(action, className=f"compact-value {action_color}", style={"fontSize": "10px", "textAlign": "center", "marginTop": "2px"})
                        ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "borderRadius": "4px", "padding": "6px 8px", "margin": "3px 0"})
                    )
                
                if not conv_cards:
                    conv_cards = [
                        html.Div([
                            html.Div("No AI conversations yet", style={"fontSize": "11px", "color": "var(--text-muted)", "textAlign": "center", "padding": "12px"})
                        ], style={"background": "var(--bg-secondary)", "border": "1px solid var(--border-color)", "borderRadius": "4px"})
                    ]
                
                return performance, position_cards, conv_cards
                
            except Exception as e:
                logger.error(f"Error updating bottom panels: {e}")
                return (
                    [html.Div("Error loading performance", className="metric-card")],
                    [html.Div("Error loading positions", className="metric-card")], 
                    [html.Div("Error loading conversations", className="metric-card")]
                )
    
    def _create_empty_chart(self, message: str):
        """Create empty chart with message"""
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text=message,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=16, color="#888888")
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            margin=dict(l=0, r=0, t=0, b=0)
        )
        return fig
    
    def _get_llm_conversations(self):
        """Get LLM conversations from log file"""
        try:
            log_file = Path("logs/llm_conversations.jsonl")
            conversations = []
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            conversations.append(json.loads(line))
                        except:
                            continue
            
            return conversations[-20:]  # Last 20 conversations
            
        except Exception as e:
            logger.error(f"Error reading conversations: {e}")
            return []
    
        # Modal open/close callback
        @self.app.callback(
            Output('config-modal', 'is_open') if MODAL_AVAILABLE else Output('config-modal', 'style'),
            [Input('config-button', 'n_clicks')],
            [State('config-modal', 'is_open')] if MODAL_AVAILABLE else [],
            prevent_initial_call=True
        )
        def toggle_modal(n_clicks, is_open=None):
            """Toggle configuration modal"""
            if n_clicks:
                logger.info(f"🔧 Config button clicked, toggling modal")
                if MODAL_AVAILABLE:
                    return not (is_open if is_open is not None else False)
                else:
                    # For non-DBC modal, we'll just open it
                    return {"display": "flex"}
            if MODAL_AVAILABLE:
                return False
            else:
                return {"display": "none"}

        # Tab content callback
        @self.app.callback(
            Output('config-content', 'children'),
            [Input('config-tabs', 'active_tab')] if MODAL_AVAILABLE else [Input('llm-tab', 'n_clicks'), Input('trader-tab', 'n_clicks')],
            prevent_initial_call=False
        )
        def render_tab_content(active_tab_or_llm_clicks, trader_clicks=None):
            """Render content based on active tab"""
            if MODAL_AVAILABLE:
                if active_tab_or_llm_clicks == "trader-tab":
                    return self._get_trader_config_content()
                else:
                    return self._get_llm_config_content()
            else:
                # Fallback for non-DBC modal
                ctx_triggered = ctx.triggered[0]['prop_id'] if ctx.triggered else None
                if ctx_triggered == 'trader-tab.n_clicks' and trader_clicks:
                    return self._get_trader_config_content()
                else:
                    return self._get_llm_config_content()
        
        # Save configuration callback
        @self.app.callback(
            Output('config-modal', 'style', allow_duplicate=True),
            [Input({'type': 'config-save', 'index': ALL}, 'n_clicks')],
            [State({'type': 'config-input', 'index': ALL}, 'value'),
             State({'type': 'config-input', 'index': ALL}, 'id')],
            prevent_initial_call=True
        )
        def save_configuration(save_clicks, values, input_ids):
            """Save configuration changes"""
            if not any(save_clicks):
                return {"display": "flex"}
            
            try:
                # Save the configuration
                config_data = {}
                for i, input_id in enumerate(input_ids):
                    if i < len(values) and values[i] is not None:
                        config_data[input_id['index']] = values[i]
                
                self._save_config(config_data)
                logger.info("✅ Configuration saved successfully")
                
                # Close modal after save
                return {"display": "none"}
                
            except Exception as e:
                logger.error(f"❌ Failed to save configuration: {e}")
                return {"display": "flex"}

    def _get_llm_config_content(self):
        """Get LLM configuration tab content"""
        current_config = self._load_config()
        
        return html.Div([
            html.Div(className="config-section", children=[
                html.H3("🤖 LLM Analysis Settings", className="config-section-title"),
                
                html.Div(className="config-field", children=[
                    html.Label("Market Analysis Prompt Template", className="config-label"),
                    dcc.Textarea(
                        id={'type': 'config-input', 'index': 'llm_market_prompt'},
                        value=current_config.get('llm_market_prompt', self._get_default_market_prompt()),
                        className="config-textarea",
                        placeholder="Enter the prompt template for market analysis..."
                    ),
                    html.Div("This prompt is sent to the LLM with market data for analysis. Use {symbol}, {price}, {indicators} placeholders.", className="config-help")
                ]),
                
                html.Div(className="config-field", children=[
                    html.Label("Decision Making Prompt", className="config-label"),
                    dcc.Textarea(
                        id={'type': 'config-input', 'index': 'llm_decision_prompt'},
                        value=current_config.get('llm_decision_prompt', self._get_default_decision_prompt()),
                        className="config-textarea",
                        placeholder="Enter the prompt for trading decisions..."
                    ),
                    html.Div("This prompt asks the LLM to make buy/sell/hold decisions. Must request JSON output with action, confidence, reasoning.", className="config-help")
                ])
            ]),
            
            html.Div(className="config-section", children=[
                html.H3("⚙️ LLM Connection Settings", className="config-section-title"),
                
                html.Div(className="config-grid", children=[
                    html.Div(className="config-field", children=[
                        html.Label("LM Studio URL", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'llm_url'},
                            value=current_config.get('llm_url', 'http://localhost:1234'),
                            className="config-input",
                            placeholder="http://localhost:1234"
                        ),
                        html.Div("LM Studio server endpoint", className="config-help")
                    ]),
                    
                    html.Div(className="config-field", children=[
                        html.Label("Model Name", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'llm_model'},
                            value=current_config.get('llm_model', 'gemma-2-2b-it'),
                            className="config-input",
                            placeholder="gemma-2-2b-it"
                        ),
                        html.Div("Model identifier in LM Studio", className="config-help")
                    ])
                ]),
                
                html.Div(className="config-grid", children=[
                    html.Div(className="config-field", children=[
                        html.Label("Temperature", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'llm_temperature'},
                            type="number",
                            value=current_config.get('llm_temperature', 0.3),
                            min=0, max=2, step=0.1,
                            className="config-input"
                        ),
                        html.Div("Creativity level (0.0-2.0)", className="config-help")
                    ]),
                    
                    html.Div(className="config-field", children=[
                        html.Label("Max Tokens", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'llm_max_tokens'},
                            type="number",
                            value=current_config.get('llm_max_tokens', 500),
                            min=50, max=2000,
                            className="config-input"
                        ),
                        html.Div("Maximum response length", className="config-help")
                    ])
                ])
            ]),
            
            html.Div([
                html.Button("💾 Save LLM Settings", id={'type': 'config-save', 'index': 'llm'}, className="config-save-btn"),
                html.Button("🔄 Reset to Defaults", id={'type': 'config-reset', 'index': 'llm'}, className="config-reset-btn")
            ], style={"marginTop": "32px", "textAlign": "center"})
        ])

    def _get_trader_config_content(self):
        """Get Trader configuration tab content"""
        current_config = self._load_config()
        
        return html.Div([
            html.Div(className="config-section", children=[
                html.H3("📈 Trading Parameters", className="config-section-title"),
                
                html.Div(className="config-grid", children=[
                    html.Div(className="config-field", children=[
                        html.Label("Max Position Size (%)", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'max_position_size'},
                            type="number",
                            value=current_config.get('max_position_size', 10),
                            min=1, max=50, step=1,
                            className="config-input"
                        ),
                        html.Div("Maximum % of portfolio per stock", className="config-help")
                    ]),
                    
                    html.Div(className="config-field", children=[
                        html.Label("Daily Loss Limit (%)", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'daily_loss_limit'},
                            type="number",
                            value=current_config.get('daily_loss_limit', 2),
                            min=0.5, max=10, step=0.1,
                            className="config-input"
                        ),
                        html.Div("Stop trading if daily loss exceeds this %", className="config-help")
                    ])
                ]),
                
                html.Div(className="config-grid", children=[
                    html.Div(className="config-field", children=[
                        html.Label("Min Confidence (%)", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'min_confidence'},
                            type="number",
                            value=current_config.get('min_confidence', 60),
                            min=30, max=90, step=5,
                            className="config-input"
                        ),
                        html.Div("Minimum LLM confidence to execute trades", className="config-help")
                    ]),
                    
                    html.Div(className="config-field", children=[
                        html.Label("Trading Interval (minutes)", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'trading_interval'},
                            type="number",
                            value=current_config.get('trading_interval', 5),
                            min=1, max=60, step=1,
                            className="config-input"
                        ),
                        html.Div("Minutes between trading cycles", className="config-help")
                    ])
                ])
            ]),
            
            html.Div(className="config-section", children=[
                html.H3("🎯 Trading Symbols", className="config-section-title"),
                
                html.Div(className="config-field", children=[
                    html.Label("Active Symbols", className="config-label"),
                    dcc.Input(
                        id={'type': 'config-input', 'index': 'trading_symbols'},
                        value=current_config.get('trading_symbols', 'AAPL,MSFT,GOOGL,TSLA,NVDA'),
                        className="config-input",
                        placeholder="AAPL,MSFT,GOOGL,TSLA,NVDA"
                    ),
                    html.Div("Comma-separated list of stock symbols to trade", className="config-help")
                ])
            ]),
            
            html.Div(className="config-section", children=[
                html.H3("⚠️ Risk Management", className="config-section-title"),
                
                html.Div(className="config-grid", children=[
                    html.Div(className="config-field", children=[
                        html.Label("Max Trades Per Day", className="config-label"),
                        dcc.Input(
                            id={'type': 'config-input', 'index': 'max_trades_per_day'},
                            type="number",
                            value=current_config.get('max_trades_per_day', 20),
                            min=1, max=100,
                            className="config-input"
                        ),
                        html.Div("Limit total trades per trading day", className="config-help")
                    ]),
                    
                    html.Div(className="config-field", children=[
                        html.Label("Dry Run Mode", className="config-label"),
                        dcc.Dropdown(
                            id={'type': 'config-input', 'index': 'dry_run_mode'},
                            options=[
                                {'label': 'Yes - Simulate only', 'value': True},
                                {'label': 'No - Live paper trading', 'value': False}
                            ],
                            value=current_config.get('dry_run_mode', False),
                            className="config-input",
                            style={'background': 'var(--bg-primary)', 'color': 'var(--text-primary)'}
                        ),
                        html.Div("Enable to simulate without placing real orders", className="config-help")
                    ])
                ])
            ]),
            
            html.Div([
                html.Button("💾 Save Trading Settings", id={'type': 'config-save', 'index': 'trader'}, className="config-save-btn"),
                html.Button("🔄 Reset to Defaults", id={'type': 'config-reset', 'index': 'trader'}, className="config-reset-btn")
            ], style={"marginTop": "32px", "textAlign": "center"})
        ])

    def _load_config(self):
        """Load current configuration"""
        try:
            config_file = self.data_dir / "config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
        
        return {}

    def _save_config(self, config_data):
        """Save configuration to file"""
        try:
            config_file = self.data_dir / "config.json"
            
            # Load existing config
            existing_config = self._load_config()
            
            # Update with new data
            existing_config.update(config_data)
            
            # Save to file
            with open(config_file, 'w') as f:
                json.dump(existing_config, f, indent=2)
                
            logger.info(f"Configuration saved to {config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise

    def _get_default_market_prompt(self):
        """Get default market analysis prompt"""
        return """Analyze the following market data for {symbol}:

Current Price: ${price:.2f}
Technical Indicators:
{indicators}

Recent Market Context:
- RSI indicates momentum conditions
- MACD shows trend strength  
- Moving averages reveal trend direction
- Volume patterns suggest institutional interest

Provide a comprehensive analysis considering:
1. Technical indicator signals
2. Market momentum and trend
3. Risk/reward potential
4. Current market regime

Focus on actionable insights for day trading decisions."""

    def _get_default_decision_prompt(self):
        """Get default decision-making prompt"""
        return """Based on the market analysis, make a trading decision and respond with JSON only:

{{
  "sentiment": "bullish" | "bearish" | "neutral",
  "confidence": 0-100,
  "action": "buy" | "sell" | "hold",
  "reasoning": "Brief explanation of decision rationale"
}}

Guidelines:
- Only recommend BUY if highly confident in upward movement
- Only recommend SELL if holding position and confident in downward movement  
- Use HOLD when uncertain or conditions don't favor strong moves
- Confidence should reflect conviction level (60+ for action, <60 for hold)
- Keep reasoning concise but specific to current market conditions"""

    def _get_latest_market_intelligence(self):
        """Get latest market intelligence data"""
        try:
            # Try to get from database or file
            # For now, return mock data
            return {
                "market_sentiment": "bullish",
                "confidence": 75,
                "opportunities": [
                    "AAPL showing strong momentum",
                    "Tech sector outperforming",
                    "Low volatility environment"
                ],
                "risks": [
                    "High market concentration",
                    "Earnings season approaching"
                ]
            }
        except Exception as e:
            logger.error(f"Error getting market intelligence: {e}")
            return None
    
    def run(self, host: str = "127.0.0.1", port: int = 8050, debug: bool = False):
        """Run the professional dashboard"""
        logger.info(f"🚀 Starting WawaTrader Pro Dashboard on http://{host}:{port}")
        logger.info("🎯 Professional trading interface with LLM transparency")
        logger.info("📊 Dark theme optimized for daytrading")
        logger.info("🤖 Real-time AI decision monitoring")
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        
        # Use modern Dash API (v2.0+) - run_server is obsolete in Dash 3.x
        self.app.run(host=host, port=port, debug=debug)


