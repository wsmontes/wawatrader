"""
Alert System Demo

Demonstrates the alert notification system for WawaTrader.

Features demonstrated:
- Trade execution alerts
- Risk violation alerts
- P&L change alerts
- Daily summary alerts
- Error alerts
- Email and Slack integration (with mocking for demo)
- Alert history tracking

Run with: python scripts/demo_alerts.py

Note: This demo uses mock implementations for email/Slack to avoid
      requiring actual credentials. In production, set environment
      variables for real notifications.

Author: WawaTrader Team
Date: October 2025
"""

from loguru import logger
from unittest.mock import patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from wawatrader.alerts import (
    get_alert_manager,
    AlertType,
    AlertSeverity
)


def demo_alert_system():
    """Demonstrate all alert system features"""
    
    logger.info("╔═══════════════════════════════════════════════════════════╗")
    logger.info("║       WawaTrader Alert System - Feature Demo             ║")
    logger.info("╚═══════════════════════════════════════════════════════════╝")
    logger.info("")
    
    # Initialize alert manager (disabled for demo - no actual emails/Slack)
    logger.info("1️⃣  ALERT MANAGER INITIALIZATION")
    logger.info("────────────────────────────────────────────────────────────")
    
    # Mock email/Slack for demonstration
    with patch('wawatrader.alerts.AlertManager._send_email', return_value=True), \
         patch('wawatrader.alerts.AlertManager._send_slack', return_value=True):
        
        alerts = get_alert_manager(
            email_enabled=True,
            slack_enabled=True,
            email_from="wawatrader@example.com",
            email_password="demo_password",
            email_to=["admin@example.com"],
            slack_webhook_url="https://hooks.slack.com/services/DEMO",
            min_pnl_percent=2.0
        )
        
        logger.info("✅ Alert manager initialized")
        logger.info(f"   Email enabled: {alerts.email_enabled}")
        logger.info(f"   Slack enabled: {alerts.slack_enabled}")
        logger.info(f"   Min P&L threshold: {alerts.min_pnl_percent}%")
        logger.info("")
        
        # Demo 1: Trade Execution Alert
        logger.info("2️⃣  TRADE EXECUTION ALERTS")
        logger.info("────────────────────────────────────────────────────────────")
        
        success = alerts.send_trade_alert(
            symbol='AAPL',
            action='BUY',
            quantity=100,
            price=150.0,
            total_cost=15000.0,
            order_id='ORD-12345',
            severity=AlertSeverity.MEDIUM
        )
        
        logger.info(f"✅ Buy alert sent: {success}")
        logger.info("   Symbol: AAPL")
        logger.info("   Action: BUY 100 shares @ $150.00")
        logger.info("   Total: $15,000.00")
        logger.info("")
        
        success = alerts.send_trade_alert(
            symbol='TSLA',
            action='SELL',
            quantity=50,
            price=250.0,
            total_cost=12500.0,
            order_id='ORD-12346'
        )
        
        logger.info(f"✅ Sell alert sent: {success}")
        logger.info("   Symbol: TSLA")
        logger.info("   Action: SELL 50 shares @ $250.00")
        logger.info("   Total: $12,500.00")
        logger.info("")
        
        # Demo 2: Risk Violation Alerts
        logger.info("3️⃣  RISK VIOLATION ALERTS")
        logger.info("────────────────────────────────────────────────────────────")
        
        success = alerts.send_risk_alert(
            violation_type='position_size',
            message='Position size exceeds 10% portfolio limit',
            symbol='NVDA',
            severity=AlertSeverity.HIGH,
            details={
                'requested_size': 15000,
                'max_allowed': 10000,
                'portfolio_value': 100000,
                'limit_percent': 10
            }
        )
        
        logger.info(f"✅ Position size violation alert sent: {success}")
        logger.info("   Type: position_size")
        logger.info("   Symbol: NVDA")
        logger.info("   Requested: $15,000 (exceeds $10,000 limit)")
        logger.info("")
        
        success = alerts.send_risk_alert(
            violation_type='daily_loss',
            message='Daily loss limit of 2% exceeded',
            severity=AlertSeverity.CRITICAL,
            details={
                'current_loss': -2500,
                'max_loss': -2000,
                'portfolio_value': 100000,
                'loss_percent': 2.5
            }
        )
        
        logger.info(f"✅ Daily loss violation alert sent: {success}")
        logger.info("   Type: daily_loss")
        logger.info("   Loss: -$2,500 (-2.5%) exceeds -$2,000 limit")
        logger.info("")
        
        # Demo 3: P&L Change Alerts
        logger.info("4️⃣  P&L CHANGE ALERTS")
        logger.info("────────────────────────────────────────────────────────────")
        
        # Significant gain
        success = alerts.send_pnl_alert(
            current_value=115000.0,
            previous_value=112500.0,
            change_percent=2.22
        )
        
        logger.info(f"✅ P&L gain alert sent: {success}")
        logger.info("   Previous: $112,500.00")
        logger.info("   Current: $115,000.00")
        logger.info("   Change: +$2,500.00 (+2.22%)")
        logger.info("")
        
        # Significant loss
        success = alerts.send_pnl_alert(
            current_value=97500.0,
            previous_value=100000.0,
            change_percent=-2.5,
            symbol='AAPL'
        )
        
        logger.info(f"✅ P&L loss alert sent: {success}")
        logger.info("   Symbol: AAPL")
        logger.info("   Previous: $100,000.00")
        logger.info("   Current: $97,500.00")
        logger.info("   Change: -$2,500.00 (-2.5%)")
        logger.info("")
        
        # Below threshold (should not send)
        success = alerts.send_pnl_alert(
            current_value=101000.0,
            previous_value=100000.0,
            change_percent=1.0
        )
        
        logger.info(f"⏭️  Small P&L change alert skipped: {not success}")
        logger.info("   Change: +1.0% (below 2.0% threshold)")
        logger.info("")
        
        # Demo 4: Daily Summary
        logger.info("5️⃣  DAILY SUMMARY ALERTS")
        logger.info("────────────────────────────────────────────────────────────")
        
        success = alerts.send_daily_summary(
            total_trades=12,
            total_pnl=3500.0,
            win_rate=75.0,
            portfolio_value=118500.0,
            top_performers=[
                {'symbol': 'AAPL', 'pnl': 5.2},
                {'symbol': 'TSLA', 'pnl': 3.8},
                {'symbol': 'NVDA', 'pnl': 2.1}
            ],
            worst_performers=[
                {'symbol': 'AMD', 'pnl': -1.5},
                {'symbol': 'INTC', 'pnl': -0.8}
            ]
        )
        
        logger.info(f"✅ Daily summary sent: {success}")
        logger.info("   Total trades: 12")
        logger.info("   Daily P&L: +$3,500.00")
        logger.info("   Win rate: 75.0%")
        logger.info("   Portfolio: $118,500.00")
        logger.info("   Top performer: AAPL (+5.2%)")
        logger.info("   Worst performer: AMD (-1.5%)")
        logger.info("")
        
        # Demo 5: Error Alerts
        logger.info("6️⃣  ERROR ALERTS")
        logger.info("────────────────────────────────────────────────────────────")
        
        success = alerts.send_error_alert(
            error_message="Failed to execute order: Insufficient buying power",
            error_type="OrderExecutionError",
            traceback="Traceback (most recent call last):\n  File 'trading_agent.py', line 123\n  ...",
            severity=AlertSeverity.CRITICAL
        )
        
        logger.info(f"✅ Error alert sent: {success}")
        logger.info("   Type: OrderExecutionError")
        logger.info("   Message: Failed to execute order")
        logger.info("   Severity: CRITICAL")
        logger.info("")
        
        # Demo 6: Alert History
        logger.info("7️⃣  ALERT HISTORY")
        logger.info("────────────────────────────────────────────────────────────")
        
        all_history = alerts.get_alert_history()
        logger.info(f"📊 Total alerts sent: {len(all_history)}")
        
        # Count by type
        trade_count = len(alerts.get_alert_history(alert_type=AlertType.TRADE))
        risk_count = len(alerts.get_alert_history(alert_type=AlertType.RISK))
        pnl_count = len(alerts.get_alert_history(alert_type=AlertType.PNL))
        summary_count = len(alerts.get_alert_history(alert_type=AlertType.DAILY_SUMMARY))
        error_count = len(alerts.get_alert_history(alert_type=AlertType.ERROR))
        
        logger.info(f"   Trade alerts: {trade_count}")
        logger.info(f"   Risk alerts: {risk_count}")
        logger.info(f"   P&L alerts: {pnl_count}")
        logger.info(f"   Summary alerts: {summary_count}")
        logger.info(f"   Error alerts: {error_count}")
        logger.info("")
        
        # Show recent alerts
        recent = alerts.get_alert_history(limit=3)
        logger.info("📋 Last 3 alerts:")
        for i, alert in enumerate(recent[-3:], 1):
            logger.info(f"   {i}. {alert['type']} - {alert.get('severity', 'N/A')} - {alert['timestamp'][:19]}")
        logger.info("")
        
        # Demo 7: Configuration Examples
        logger.info("8️⃣  CONFIGURATION EXAMPLES")
        logger.info("────────────────────────────────────────────────────────────")
        
        logger.info("🔧 Environment Variables:")
        logger.info("   export ALERT_EMAIL_ENABLED=true")
        logger.info("   export ALERT_EMAIL_SMTP_HOST=smtp.gmail.com")
        logger.info("   export ALERT_EMAIL_SMTP_PORT=587")
        logger.info("   export ALERT_EMAIL_FROM=your_email@gmail.com")
        logger.info("   export ALERT_EMAIL_PASSWORD=your_app_password")
        logger.info("   export ALERT_EMAIL_TO=recipient@example.com")
        logger.info("")
        logger.info("   export ALERT_SLACK_ENABLED=true")
        logger.info("   export ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/...")
        logger.info("")
        logger.info("   export ALERT_MIN_PNL_PERCENT=2.0")
        logger.info("   export ALERT_DAILY_SUMMARY_TIME=16:00")
        logger.info("")
        
        logger.info("🐍 Python Code:")
        logger.info("   from wawatrader.alerts import get_alert_manager")
        logger.info("")
        logger.info("   # Get singleton instance (auto-configured from env)")
        logger.info("   alerts = get_alert_manager()")
        logger.info("")
        logger.info("   # Send trade alert")
        logger.info("   alerts.send_trade_alert(")
        logger.info("       symbol='AAPL',")
        logger.info("       action='BUY',")
        logger.info("       quantity=100,")
        logger.info("       price=150.0,")
        logger.info("       total_cost=15000.0")
        logger.info("   )")
        logger.info("")
        
        logger.success("✅ Alert system demo complete!")
        logger.info("")
        logger.info("Alert system features:")
        logger.info("  ✅ Email notifications (SMTP)")
        logger.info("  ✅ Slack notifications (webhook)")
        logger.info("  ✅ Trade execution alerts")
        logger.info("  ✅ Risk violation alerts")
        logger.info("  ✅ P&L change alerts (with threshold)")
        logger.info("  ✅ Daily summary alerts")
        logger.info("  ✅ Error/warning alerts")
        logger.info("  ✅ Alert history tracking")
        logger.info("  ✅ Auto-severity levels")
        logger.info("  ✅ Singleton pattern")
        logger.info("  ✅ Environment-based config")
        logger.info("")
        
        logger.info("📧 Email Setup (Gmail example):")
        logger.info("   1. Enable 2-factor authentication on Gmail")
        logger.info("   2. Generate app password: https://myaccount.google.com/apppasswords")
        logger.info("   3. Set ALERT_EMAIL_PASSWORD to app password (not your regular password)")
        logger.info("")
        
        logger.info("💬 Slack Setup:")
        logger.info("   1. Go to: https://api.slack.com/messaging/webhooks")
        logger.info("   2. Create incoming webhook for your workspace")
        logger.info("   3. Set ALERT_SLACK_WEBHOOK_URL to webhook URL")
        logger.info("")
        
        logger.info("Integration with trading agent:")
        logger.info("   The alert system integrates seamlessly with the trading agent:")
        logger.info("   - Automatic alerts on trade execution")
        logger.info("   - Risk violations trigger immediate notifications")
        logger.info("   - Daily summaries sent at configured time")
        logger.info("   - System errors reported in real-time")
        logger.info("")


if __name__ == '__main__':
    demo_alert_system()
