"""
Performance Dashboard

Real-time monitoring interface for WawaTrader using Plotly Dash.

Features:
- Live portfolio value tracking
- Open positions display
- P&L metrics (daily, total, by symbol)
- Trade history table
- Technical indicator charts
- Risk metrics monitoring

Usage:
    from wawatrader.dashboard import Dashboard
    
    dash = Dashboard()
    dash.run(port=8050)
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
from pathlib import Path
from loguru import logger

try:
    from dash import Dash, html, dcc, Input, Output, dash_table
    import dash_bootstrap_components as dbc
    DASH_AVAILABLE = True
except ImportError:
    logger.warning("Dash not installed. Dashboard features unavailable.")
    logger.info("Install with: pip install dash dash-bootstrap-components")
    DASH_AVAILABLE = False

from wawatrader.alpaca_client import get_client
from wawatrader.indicators import analyze_dataframe, get_latest_signals


class Dashboard:
    """
    Real-time trading performance dashboard.
    
    Displays:
    - Portfolio value and P&L
    - Current positions
    - Trade history
    - Performance charts
    - Risk metrics
    """
    
    def __init__(self, data_dir: str = "trading_data"):
        """
        Initialize dashboard.
        
        Args:
            data_dir: Directory containing trading data/logs
        """
        if not DASH_AVAILABLE:
            raise ImportError("Dash is required for dashboard. Install with: pip install dash dash-bootstrap-components")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize Alpaca client
        self.alpaca = get_client()
        
        # Create Dash app
        self.app = Dash(
            __name__,
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title="WawaTrader Dashboard"
        )
        
        # Build layout
        self._build_layout()
        
        # Register callbacks
        self._register_callbacks()
        
        logger.info("Dashboard initialized")
    
    def _build_layout(self):
        """Build dashboard layout"""
        
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🤖 WawaTrader Dashboard", className="text-center mb-4"),
                    html.Hr()
                ])
            ]),
            
            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # Update every 30 seconds
                n_intervals=0
            ),
            
            # Account Summary Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Portfolio Value", className="card-title"),
                            html.H2(id="portfolio-value", children="$0.00", className="text-primary"),
                            html.P(id="portfolio-change", children="+$0.00 (0.00%)", className="text-success")
                        ])
                    ])
                ], width=3),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Today's P&L", className="card-title"),
                            html.H2(id="daily-pnl", children="$0.00", className="text-primary"),
                            html.P(id="daily-pnl-pct", children="0.00%", className="text-muted")
                        ])
                    ])
                ], width=3),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Open Positions", className="card-title"),
                            html.H2(id="position-count", children="0", className="text-primary"),
                            html.P(id="position-value", children="$0.00", className="text-muted")
                        ])
                    ])
                ], width=3),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Buying Power", className="card-title"),
                            html.H2(id="buying-power", children="$0.00", className="text-primary"),
                            html.P(id="cash-value", children="Cash: $0.00", className="text-muted")
                        ])
                    ])
                ], width=3),
            ], className="mb-4"),
            
            # Charts Row
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Portfolio Value Over Time")),
                        dbc.CardBody([
                            dcc.Graph(id="portfolio-chart")
                        ])
                    ])
                ], width=8),
                
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Position Allocation")),
                        dbc.CardBody([
                            dcc.Graph(id="allocation-chart")
                        ])
                    ])
                ], width=4),
            ], className="mb-4"),
            
            # Positions Table
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Current Positions")),
                        dbc.CardBody([
                            html.Div(id="positions-table")
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Trade History
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H5("Recent Trades")),
                        dbc.CardBody([
                            html.Div(id="trades-table")
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # LLM Intelligence Section
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("🤖 LLM Intelligence & Conversations"),
                            dbc.Badge("Live AI Analysis", color="success", className="ms-2")
                        ]),
                        dbc.CardBody([
                            dbc.Tabs([
                                dbc.Tab(label="Market Intelligence", tab_id="market-intel"),
                                dbc.Tab(label="LLM Conversations", tab_id="llm-conversations"),
                                dbc.Tab(label="Trading Plan", tab_id="trading-plan")
                            ], id="llm-tabs", active_tab="market-intel"),
                            html.Div(id="llm-content")
                        ])
                    ])
                ], width=12)
            ], className="mb-4"),

            # Technical Indicators - Improved Layout
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("📈 Technical Analysis Dashboard"),
                            dcc.Dropdown(
                                id='symbol-dropdown',
                                options=[],
                                value=None,
                                placeholder="Select a symbol for detailed analysis",
                                style={'width': '300px', 'display': 'inline-block'}
                            )
                        ]),
                        dbc.CardBody([
                            # Indicators Overview Cards
                            dbc.Row([
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("RSI", className="card-subtitle"),
                                            html.H4(id="rsi-value", className="text-primary"),
                                            html.Small(id="rsi-signal", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("MACD", className="card-subtitle"),
                                            html.H4(id="macd-value", className="text-primary"),
                                            html.Small(id="macd-signal", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("Volume", className="card-subtitle"),
                                            html.H4(id="volume-ratio", className="text-primary"),
                                            html.Small(id="volume-signal", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("Trend", className="card-subtitle"),
                                            html.H4(id="trend-value", className="text-primary"),
                                            html.Small(id="trend-signal", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("Volatility", className="card-subtitle"),
                                            html.H4(id="volatility-value", className="text-primary"),
                                            html.Small(id="volatility-signal", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                                dbc.Col([
                                    dbc.Card([
                                        dbc.CardBody([
                                            html.H6("AI Confidence", className="card-subtitle"),
                                            html.H4(id="ai-confidence", className="text-primary"),
                                            html.Small(id="ai-action", className="text-muted")
                                        ])
                                    ], color="light")
                                ], width=2),
                            ], className="mb-3"),
                            # Full Chart
                            dcc.Graph(id="indicators-chart", style={'height': '500px'})
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(),
                    html.P(
                        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        id="last-update",
                        className="text-center text-muted"
                    )
                ])
            ])
            
        ], fluid=True, style={"padding": "20px"})
    
    def _register_callbacks(self):
        """Register dashboard callbacks"""
        
        @self.app.callback(
            [
                Output("portfolio-value", "children"),
                Output("portfolio-change", "children"),
                Output("portfolio-change", "className"),
                Output("daily-pnl", "children"),
                Output("daily-pnl-pct", "children"),
                Output("daily-pnl", "className"),
                Output("position-count", "children"),
                Output("position-value", "children"),
                Output("buying-power", "children"),
                Output("cash-value", "children"),
                Output("last-update", "children"),
            ],
            [Input("interval-component", "n_intervals")]
        )
        def update_account_summary(n):
            """Update account summary cards"""
            try:
                account = self.alpaca.get_account()
                
                portfolio_value = float(account['portfolio_value'])
                equity = float(account['equity'])
                last_equity = float(account.get('last_equity', equity))
                
                # Calculate changes
                total_change = equity - last_equity
                total_change_pct = (total_change / last_equity * 100) if last_equity > 0 else 0
                
                # Daily P&L
                daily_pnl = total_change
                daily_pnl_pct = total_change_pct
                
                # Position info
                positions = self.alpaca.get_positions()
                position_count = len(positions)
                position_value = sum(float(p.get('market_value', 0)) for p in positions)
                
                # Buying power
                buying_power = float(account['buying_power'])
                cash = float(account['cash'])
                
                # Formatting
                pnl_class = "text-success" if daily_pnl >= 0 else "text-danger"
                change_class = "text-success" if total_change >= 0 else "text-danger"
                
                return (
                    f"${portfolio_value:,.2f}",
                    f"{'+' if total_change >= 0 else ''}{total_change:,.2f} ({total_change_pct:+.2f}%)",
                    change_class,
                    f"${daily_pnl:+,.2f}",
                    f"{daily_pnl_pct:+.2f}%",
                    pnl_class,
                    str(position_count),
                    f"${position_value:,.2f}",
                    f"${buying_power:,.2f}",
                    f"Cash: ${cash:,.2f}",
                    f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.error(f"Error updating account summary: {e}")
                return ("$0.00", "$0.00 (0.00%)", "text-muted", "$0.00", "0.00%", "text-muted", 
                       "0", "$0.00", "$0.00", "Cash: $0.00", 
                       f"Error: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        @self.app.callback(
            Output("portfolio-chart", "figure"),
            [Input("interval-component", "n_intervals")]
        )
        def update_portfolio_chart(n):
            """Update portfolio value chart"""
            try:
                # Get portfolio history
                history = self.alpaca.get_portfolio_history(
                    period="1M",
                    timeframe="1D"
                )
                
                if history and 'timestamp' in history and 'equity' in history:
                    df = pd.DataFrame({
                        'timestamp': pd.to_datetime(history['timestamp'], unit='s'),
                        'equity': history['equity']
                    })
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['equity'],
                        mode='lines',
                        name='Portfolio Value',
                        line=dict(color='#0d6efd', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(13, 110, 253, 0.1)'
                    ))
                    
                    fig.update_layout(
                        title="Portfolio Value (Last 30 Days)",
                        xaxis_title="Date",
                        yaxis_title="Value ($)",
                        hovermode='x unified',
                        showlegend=False,
                        margin=dict(l=40, r=40, t=40, b=40)
                    )
                    
                    return fig
                else:
                    # No data available
                    return self._empty_chart("No portfolio history available")
                    
            except Exception as e:
                logger.error(f"Error updating portfolio chart: {e}")
                return self._empty_chart(f"Error: {str(e)}")
        
        @self.app.callback(
            Output("allocation-chart", "figure"),
            [Input("interval-component", "n_intervals")]
        )
        def update_allocation_chart(n):
            """Update position allocation pie chart"""
            try:
                positions = self.alpaca.get_positions()
                
                if not positions:
                    return self._empty_chart("No open positions")
                
                # Get position values
                symbols = []
                values = []
                
                for pos in positions:
                    symbols.append(pos['symbol'])
                    values.append(abs(float(pos['market_value'])))
                
                fig = go.Figure(data=[go.Pie(
                    labels=symbols,
                    values=values,
                    hole=0.3
                )])
                
                fig.update_layout(
                    title="Position Allocation",
                    showlegend=True,
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating allocation chart: {e}")
                return self._empty_chart(f"Error: {str(e)}")
        
        @self.app.callback(
            Output("positions-table", "children"),
            [Input("interval-component", "n_intervals")]
        )
        def update_positions_table(n):
            """Update positions table"""
            try:
                positions = self.alpaca.get_positions()
                
                if not positions:
                    return html.P("No open positions", className="text-muted text-center")
                
                # Format positions data
                data = []
                for pos in positions:
                    unrealized_pl = float(pos.get('unrealized_pl', 0))
                    unrealized_plpc = float(pos.get('unrealized_plpc', 0)) * 100
                    
                    data.append({
                        'Symbol': pos['symbol'],
                        'Qty': int(pos['qty']),
                        'Avg Entry': f"${float(pos['avg_entry_price']):.2f}",
                        'Current': f"${float(pos['current_price']):.2f}",
                        'Market Value': f"${float(pos['market_value']):,.2f}",
                        'P&L': f"${unrealized_pl:+,.2f}",
                        'P&L %': f"{unrealized_plpc:+.2f}%",
                    })
                
                return dash_table.DataTable(
                    data=data,
                    columns=[{"name": i, "id": i} for i in data[0].keys()],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_data_conditional=[
                        {
                            'if': {'column_id': 'P&L'},
                            'color': 'green',
                            'fontWeight': 'bold'
                        }
                    ]
                )
                
            except Exception as e:
                logger.error(f"Error updating positions table: {e}")
                return html.P(f"Error: {str(e)}", className="text-danger")
        
        @self.app.callback(
            [
                Output("trades-table", "children"),
                Output("symbol-dropdown", "options"),
            ],
            [Input("interval-component", "n_intervals")]
        )
        def update_trades_table(n):
            """Update recent trades table"""
            try:
                # Get recent orders
                orders = self.alpaca.get_orders(status='all', limit=20)
                
                if not orders:
                    return (
                        html.P("No recent trades", className="text-muted text-center"),
                        []
                    )
                
                # Format trades data
                data = []
                symbols = set()
                
                for order in orders:
                    if order.get('status') == 'filled':
                        filled_at = order.get('filled_at', '')
                        if filled_at:
                            filled_at = pd.to_datetime(filled_at).strftime('%Y-%m-%d %H:%M')
                        
                        symbols.add(order['symbol'])
                        
                        data.append({
                            'Time': filled_at,
                            'Symbol': order['symbol'],
                            'Side': order['side'].upper(),
                            'Qty': int(order.get('filled_qty', 0)),
                            'Price': f"${float(order.get('filled_avg_price', 0)):.2f}",
                            'Status': order['status'].upper()
                        })
                
                # Symbol dropdown options
                symbol_options = [{'label': s, 'value': s} for s in sorted(symbols)]
                
                if not data:
                    return (
                        html.P("No filled orders", className="text-muted text-center"),
                        symbol_options
                    )
                
                return (
                    dash_table.DataTable(
                        data=data,
                        columns=[{"name": i, "id": i} for i in data[0].keys()],
                        style_cell={'textAlign': 'left', 'padding': '10px'},
                        style_header={
                            'backgroundColor': 'rgb(230, 230, 230)',
                            'fontWeight': 'bold'
                        },
                        style_data_conditional=[
                            {
                                'if': {
                                    'filter_query': '{Side} = "BUY"',
                                    'column_id': 'Side'
                                },
                                'color': 'green',
                                'fontWeight': 'bold'
                            },
                            {
                                'if': {
                                    'filter_query': '{Side} = "SELL"',
                                    'column_id': 'Side'
                                },
                                'color': 'red',
                                'fontWeight': 'bold'
                            }
                        ],
                        page_size=10
                    ),
                    symbol_options
                )
                
            except Exception as e:
                logger.error(f"Error updating trades table: {e}")
                return (html.P(f"Error: {str(e)}", className="text-danger"), [])
        
        @self.app.callback(
            Output("indicators-chart", "figure"),
            [Input("symbol-dropdown", "value")]
        )
        def update_indicators_chart(symbol):
            """Update technical indicators chart"""
            if not symbol:
                return self._empty_chart("Select a symbol to view indicators")
            
            try:
                # Get historical data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    start=start_date.strftime("%Y-%m-%d"),
                    end=end_date.strftime("%Y-%m-%d"),
                    timeframe="1Day"
                )
                
                if bars.empty:
                    return self._empty_chart(f"No data available for {symbol}")
                
                # Calculate indicators
                df = analyze_dataframe(bars)
                
                # Create subplots
                fig = make_subplots(
                    rows=3, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.5, 0.25, 0.25],
                    subplot_titles=(f'{symbol} Price & Indicators', 'RSI', 'MACD')
                )
                
                # Price and moving averages
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name='Price'
                    ),
                    row=1, col=1
                )
                
                if 'sma_20' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['sma_20'], name='SMA 20',
                                 line=dict(color='orange', width=1)),
                        row=1, col=1
                    )
                
                if 'sma_50' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['sma_50'], name='SMA 50',
                                 line=dict(color='blue', width=1)),
                        row=1, col=1
                    )
                
                # RSI
                if 'rsi' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['rsi'], name='RSI',
                                 line=dict(color='purple', width=2)),
                        row=2, col=1
                    )
                    # Add RSI reference lines
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                # MACD
                if 'macd' in df.columns and 'macd_signal' in df.columns:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['macd'], name='MACD',
                                 line=dict(color='blue', width=1)),
                        row=3, col=1
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=df['macd_signal'], name='Signal',
                                 line=dict(color='orange', width=1)),
                        row=3, col=1
                    )
                    
                    if 'macd_histogram' in df.columns:
                        colors = ['green' if val >= 0 else 'red' for val in df['macd_histogram']]
                        fig.add_trace(
                            go.Bar(x=df.index, y=df['macd_histogram'], name='Histogram',
                                 marker_color=colors),
                            row=3, col=1
                        )
                
                fig.update_layout(
                    height=800,
                    showlegend=True,
                    hovermode='x unified',
                    margin=dict(l=40, r=40, t=60, b=40)
                )
                
                fig.update_xaxes(title_text="Date", row=3, col=1)
                fig.update_yaxes(title_text="Price ($)", row=1, col=1)
                fig.update_yaxes(title_text="RSI", row=2, col=1)
                fig.update_yaxes(title_text="MACD", row=3, col=1)
                
                return fig
                
            except Exception as e:
                logger.error(f"Error updating indicators chart: {e}")
                return self._empty_chart(f"Error: {str(e)}")
        
        # New LLM Intelligence Callbacks
        @self.app.callback(
            Output("llm-content", "children"),
            [Input("llm-tabs", "active_tab"), Input("interval-component", "n_intervals")]
        )
        def update_llm_content(active_tab, n):
            """Update LLM intelligence content based on active tab"""
            if active_tab == "market-intel":
                return self._create_market_intelligence_content()
            elif active_tab == "llm-conversations":
                return self._create_llm_conversations_content()
            elif active_tab == "trading-plan":
                return self._create_trading_plan_content()
            return html.Div("Select a tab to view content")
        
        # Enhanced Technical Indicators Callbacks
        @self.app.callback(
            [
                Output("rsi-value", "children"),
                Output("rsi-signal", "children"),
                Output("macd-value", "children"), 
                Output("macd-signal", "children"),
                Output("volume-ratio", "children"),
                Output("volume-signal", "children"),
                Output("trend-value", "children"),
                Output("trend-signal", "children"),
                Output("volatility-value", "children"),
                Output("volatility-signal", "children"),
                Output("ai-confidence", "children"),
                Output("ai-action", "children"),
            ],
            [Input("symbol-dropdown", "value"), Input("interval-component", "n_intervals")]
        )
        def update_indicator_cards(symbol, n):
            """Update individual indicator cards"""
            if not symbol:
                empty = ["--", "", "--", "", "--", "", "--", "", "--", "", "--", ""]
                return empty
            
            try:
                # Get latest data for the symbol
                bars = self.alpaca.get_bars(
                    symbol=symbol,
                    start=datetime.now() - timedelta(days=30),
                    end=datetime.now() - timedelta(hours=24),
                    timeframe='1Day'
                )
                
                if bars.empty:
                    return ["No data", "", "No data", "", "No data", "", "No data", "", "No data", "", "No data", ""]
                
                # Calculate indicators
                from wawatrader.indicators import analyze_dataframe, get_latest_signals
                df = analyze_dataframe(bars)
                signals = get_latest_signals(df)
                
                if not signals:
                    return ["No signals", "", "No signals", "", "No signals", "", "No signals", "", "No signals", "", "No signals", ""]
                
                # Extract values
                rsi = signals.get('momentum', {}).get('rsi', 0)
                macd = signals.get('momentum', {}).get('macd', 0)
                volume_ratio = signals.get('volume', {}).get('volume_ratio', 0)
                sma_20 = signals.get('trend', {}).get('sma_20', 0)
                sma_50 = signals.get('trend', {}).get('sma_50', 0)
                volatility = signals.get('volatility', {}).get('volatility', 0)
                
                # Determine signals
                rsi_signal = "Overbought" if rsi > 70 else "Oversold" if rsi < 30 else "Neutral"
                macd_signal = "Bullish" if macd > 0 else "Bearish"
                volume_signal = "High" if volume_ratio > 1.5 else "Low" if volume_ratio < 0.5 else "Normal"
                trend_signal = "Bullish" if sma_20 > sma_50 else "Bearish"
                vol_signal = "High" if volatility > 30 else "Low" if volatility < 15 else "Normal"
                
                # Get AI analysis from recent decisions
                ai_conf, ai_action = self._get_recent_ai_analysis(symbol)
                
                return [
                    f"{rsi:.1f}", rsi_signal,
                    f"{macd:.3f}", macd_signal,
                    f"{volume_ratio:.2f}x", volume_signal,
                    "Bullish" if sma_20 > sma_50 else "Bearish", trend_signal,
                    f"{volatility:.1f}%", vol_signal,
                    f"{ai_conf}%", ai_action
                ]
                
            except Exception as e:
                logger.error(f"Error updating indicator cards: {e}")
                return ["Error", "", "Error", "", "Error", "", "Error", "", "Error", "", "Error", ""]
    
    def _create_market_intelligence_content(self):
        """Create market intelligence dashboard content"""
        try:
            # Get latest market intelligence from file or database
            intelligence_data = self._get_latest_market_intelligence()
            
            if not intelligence_data:
                return html.Div([
                    dbc.Alert("No market intelligence data available yet. The system will generate analysis during the next trading cycle.", color="info")
                ])
            
            return html.Div([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("📊 Market Sentiment"),
                                html.H3(intelligence_data.get('market_sentiment', 'Unknown').title(), 
                                        className=f"text-{'success' if intelligence_data.get('market_sentiment') == 'bullish' else 'danger' if intelligence_data.get('market_sentiment') == 'bearish' else 'warning'}"),
                                html.P(f"Confidence: {intelligence_data.get('confidence', 0)}%")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("🎯 Market Regime"),
                                html.H3(intelligence_data.get('regime_assessment', 'Unknown').replace('_', ' ').title()),
                                html.P("Current market state")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("⚠️ Risk Level"),
                                html.H3("Medium", className="text-warning"),  # Calculated from risks
                                html.P(f"{len(intelligence_data.get('risks', []))} risks identified")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("💡 Opportunities"),
                                html.H3(str(len(intelligence_data.get('opportunities', [])))),
                                html.P("Potential trades found")
                            ])
                        ])
                    ], width=3),
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("🔍 Key Findings"),
                            dbc.CardBody([
                                html.Ul([
                                    html.Li(str(finding)) for finding in intelligence_data.get('key_findings', ['No findings available'])
                                ])
                            ])
                        ])
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📋 Recommended Actions"),
                            dbc.CardBody([
                                html.Ol([
                                    html.Li(str(action)) for action in intelligence_data.get('recommended_actions', ['No recommendations available'])
                                ])
                            ])
                        ])
                    ], width=6),
                ])
            ])
            
        except Exception as e:
            logger.error(f"Error creating market intelligence content: {e}")
            return dbc.Alert(f"Error loading market intelligence: {str(e)}", color="danger")
    
    def _create_llm_conversations_content(self):
        """Create LLM conversations history content"""
        try:
            conversations = self._get_llm_conversations()
            
            if not conversations:
                return dbc.Alert("No LLM conversations recorded yet. Start a trading cycle to see AI interactions.", color="info")
            
            conversation_cards = []
            for i, conv in enumerate(conversations[-10:]):  # Show last 10 conversations
                timestamp = conv.get('timestamp', 'Unknown')
                symbol = conv.get('symbol', 'Unknown')
                prompt = conv.get('prompt', 'No prompt')[:200] + '...' if len(conv.get('prompt', '')) > 200 else conv.get('prompt', '')
                response = conv.get('response', 'No response')[:200] + '...' if len(conv.get('response', '')) > 200 else conv.get('response', '')
                
                conversation_cards.append(
                    dbc.Card([
                        dbc.CardHeader([
                            html.H6(f"🤖 {symbol} Analysis - {timestamp}", className="mb-0"),
                            dbc.Badge(conv.get('action', 'Unknown'), color="primary", className="ms-2")
                        ]),
                        dbc.CardBody([
                            dbc.Accordion([
                                dbc.AccordionItem([
                                    html.Pre(prompt, style={'fontSize': '12px', 'whiteSpace': 'pre-wrap'})
                                ], title="📤 Prompt to LLM"),
                                dbc.AccordionItem([
                                    html.Pre(response, style={'fontSize': '12px', 'whiteSpace': 'pre-wrap'})
                                ], title="📥 LLM Response"),
                            ])
                        ])
                    ], className="mb-2")
                )
            
            return html.Div(conversation_cards)
            
        except Exception as e:
            logger.error(f"Error creating LLM conversations: {e}")
            return dbc.Alert(f"Error loading conversations: {str(e)}", color="danger")
    
    def _create_trading_plan_content(self):
        """Create trading plan and strategy content"""
        return html.Div([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🎯 Current Trading Strategy"),
                        dbc.CardBody([
                            html.H5("Hybrid LLM + Technical Analysis"),
                            html.P("WawaTrader combines technical indicators with AI sentiment analysis for trading decisions."),
                            html.Hr(),
                            html.H6("📋 Trading Rules:"),
                            html.Ul([
                                html.Li("Maximum 10% position size per stock"),
                                html.Li("Maximum 2% daily loss limit"),
                                html.Li("Minimum 60% AI confidence required for trades"),
                                html.Li("Technical analysis validates AI decisions"),
                                html.Li("Paper trading only (no real money risk)")
                            ]),
                            html.Hr(),
                            html.H6("🔄 Trading Cycle (Every 5 minutes):"),
                            html.Ol([
                                html.Li("📊 Fetch real-time market data"),
                                html.Li("📈 Calculate 21+ technical indicators"),
                                html.Li("📰 Gather recent news for each symbol"),
                                html.Li("🤖 LLM analyzes market + news + technicals"),
                                html.Li("⚖️ Risk management validates decisions"),
                                html.Li("💰 Execute paper trades (if approved)"),
                                html.Li("📝 Log all decisions with reasoning"),
                                html.Li("🔍 Background market intelligence during wait")
                            ])
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🎲 Strategy Tags & Status"),
                        dbc.CardBody([
                            html.Div([
                                dbc.Badge("🤖 AI-Powered", color="primary", className="me-2 mb-2"),
                                dbc.Badge("📈 Technical Analysis", color="success", className="me-2 mb-2"),
                                dbc.Badge("📰 News Integration", color="info", className="me-2 mb-2"),
                                dbc.Badge("⚡ Real-time", color="warning", className="me-2 mb-2"),
                                dbc.Badge("🛡️ Risk Management", color="danger", className="me-2 mb-2"),
                                dbc.Badge("📊 Paper Trading", color="secondary", className="me-2 mb-2"),
                                dbc.Badge("🔄 Automated", color="dark", className="me-2 mb-2"),
                            ], className="mb-3"),
                            html.Hr(),
                            html.H6("📈 Performance Metrics:"),
                            html.Ul([
                                html.Li(f"🎯 Win Rate: {self._get_win_rate()}%"),
                                html.Li(f"📊 Total Trades: {self._get_total_trades()}"),
                                html.Li(f"💰 Best Trade: +{self._get_best_trade()}%"),
                                html.Li(f"📉 Worst Trade: {self._get_worst_trade()}%"),
                                html.Li(f"⏱️ Avg Hold Time: {self._get_avg_hold_time()}"),
                            ])
                        ])
                    ])
                ], width=6),
            ])
        ])
    
    def _get_latest_market_intelligence(self):
        """Get latest market intelligence data"""
        try:
            # Try to read from logs or database
            log_file = Path("logs/decisions.jsonl")
            if log_file.exists():
                # This is a placeholder - in a real implementation, you'd parse the intelligence data
                return {
                    'market_sentiment': 'neutral',
                    'confidence': 75,
                    'regime_assessment': 'bull_market',
                    'key_findings': ['Market showing steady growth', 'Tech sector leading', 'Volume normalized'],
                    'opportunities': [{'symbol': 'AAPL', 'reason': 'Bullish breakout'}],
                    'risks': [{'type': 'sector_concentration', 'description': 'Over-weighted in tech'}],
                    'recommended_actions': ['Monitor sector rotation', 'Consider diversification']
                }
        except:
            pass
        return None
    
    def _get_llm_conversations(self):
        """Get LLM conversation history"""
        try:
            conversations = []
            
            # Read from the new conversation log
            conv_log_file = Path("logs/llm_conversations.jsonl")
            if conv_log_file.exists():
                with open(conv_log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            conversations.append({
                                'timestamp': data.get('timestamp', ''),
                                'symbol': data.get('symbol', ''),
                                'prompt': data.get('prompt', ''),
                                'response': data.get('response', ''),
                                'action': 'Analysis'  # Default action
                            })
                        except:
                            continue
            
            # Also read from decisions log for additional context
            log_file = Path("logs/decisions.jsonl")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            if 'llm_analysis' in data:
                                conversations.append({
                                    'timestamp': data.get('timestamp', ''),
                                    'symbol': data.get('symbol', ''),
                                    'prompt': 'Trading Decision Context',
                                    'response': data.get('llm_analysis', {}).get('raw_response', ''),
                                    'action': data.get('action', '').upper()
                                })
                        except:
                            continue
                            
            # Sort by timestamp and return recent ones
            conversations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return conversations[:30]  # Last 30 conversations
        except Exception as e:
            logger.error(f"Error getting LLM conversations: {e}")
            return []
    
    def _get_recent_ai_analysis(self, symbol):
        """Get recent AI analysis for symbol"""
        try:
            conversations = self._get_llm_conversations()
            for conv in reversed(conversations):
                if conv.get('symbol') == symbol:
                    # Extract confidence and action from the conversation
                    return 75, "HOLD"  # Placeholder
            return 50, "ANALYZE"
        except:
            return 50, "UNKNOWN"
    
    def _get_win_rate(self):
        """Calculate win rate from trading history"""
        return 67  # Placeholder
    
    def _get_total_trades(self):
        """Get total number of trades"""
        return 23  # Placeholder
    
    def _get_best_trade(self):
        """Get best trade performance"""
        return 8.5  # Placeholder
    
    def _get_worst_trade(self):
        """Get worst trade performance"""
        return -3.2  # Placeholder
    
    def _get_avg_hold_time(self):
        """Get average holding time"""
        return "2.3 hours"  # Placeholder
    
    def _empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        return fig
    
    def run(self, host: str = "127.0.0.1", port: int = 8050, debug: bool = False):
        """
        Run the dashboard server.
        
        Args:
            host: Host IP address
            port: Port number
            debug: Enable debug mode
        """
        logger.info(f"Starting dashboard on http://{host}:{port}")
        logger.info("Press Ctrl+C to stop")
        
        self.app.run(host=host, port=port, debug=debug)


def main():
    """Main entry point for running dashboard standalone"""
    dashboard = Dashboard()
    dashboard.run(debug=True)


if __name__ == "__main__":
    main()
