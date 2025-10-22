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
            
            # Technical Indicators
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H5("Technical Indicators"),
                            dcc.Dropdown(
                                id='symbol-dropdown',
                                options=[],
                                value=None,
                                placeholder="Select a symbol"
                            )
                        ]),
                        dbc.CardBody([
                            dcc.Graph(id="indicators-chart")
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
        
        self.app.run_server(host=host, port=port, debug=debug)


def main():
    """Main entry point for running dashboard standalone"""
    dashboard = Dashboard()
    dashboard.run(debug=True)


if __name__ == "__main__":
    main()
