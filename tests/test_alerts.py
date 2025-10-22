"""
Unit tests for the Alert System

Tests all alert notification functionality:
- Trade execution alerts
- Risk violation alerts
- P&L change alerts
- Daily summary alerts
- Error alerts
- Email delivery (mocked)
- Slack delivery (mocked)
- Alert history tracking
- Configuration validation

Run with: pytest tests/test_alerts.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import smtplib
import requests

from wawatrader.alerts import (
    AlertManager,
    AlertType,
    AlertSeverity,
    get_alert_manager
)


class TestAlertSetup:
    """Test alert manager initialization and configuration"""
    
    def test_initialization_disabled(self):
        """Test alert manager with all channels disabled"""
        alerts = AlertManager(
            email_enabled=False,
            slack_enabled=False
        )
        
        assert alerts.email_enabled is False
        assert alerts.slack_enabled is False
        assert len(alerts.alert_history) == 0
    
    def test_initialization_email_only(self):
        """Test alert manager with email enabled"""
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        assert alerts.email_enabled is True
        assert alerts.email_from == "test@example.com"
        assert alerts.email_to == ["recipient@example.com"]
    
    def test_initialization_slack_only(self):
        """Test alert manager with Slack enabled"""
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        assert alerts.slack_enabled is True
        assert alerts.slack_webhook_url == "https://hooks.slack.com/test"
    
    def test_email_validation_missing_credentials(self):
        """Test email config validation with missing credentials"""
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com"
            # Missing email_password
        )
        
        # Should disable email alerts due to missing password
        assert alerts.email_enabled is False
    
    def test_email_validation_missing_recipients(self):
        """Test email config validation with missing recipients"""
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password"
            # Missing email_to
        )
        
        # Should disable email alerts due to missing recipients
        assert alerts.email_enabled is False
    
    def test_slack_validation_missing_webhook(self):
        """Test Slack config validation with missing webhook"""
        alerts = AlertManager(
            slack_enabled=True
            # Missing slack_webhook_url
        )
        
        # Should disable Slack alerts due to missing webhook
        assert alerts.slack_enabled is False


class TestTradeAlerts:
    """Test trade execution alerts"""
    
    @patch.object(AlertManager, '_send_email')
    def test_send_trade_alert_buy(self, mock_email):
        """Test sending buy trade alert"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        success = alerts.send_trade_alert(
            symbol='AAPL',
            action='BUY',
            quantity=100,
            price=150.0,
            total_cost=15000.0,
            order_id='order123'
        )
        
        assert success is True
        assert mock_email.called
        
        # Check alert history
        assert len(alerts.alert_history) == 1
        history_entry = alerts.alert_history[0]
        assert history_entry['type'] == AlertType.TRADE.value
        assert history_entry['symbol'] == 'AAPL'
        assert history_entry['action'] == 'BUY'
        assert history_entry['quantity'] == 100
        assert history_entry['price'] == 150.0
        assert history_entry['sent'] is True
    
    @patch.object(AlertManager, '_send_slack')
    def test_send_trade_alert_sell(self, mock_slack):
        """Test sending sell trade alert via Slack"""
        mock_slack.return_value = True
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        success = alerts.send_trade_alert(
            symbol='TSLA',
            action='SELL',
            quantity=50,
            price=250.0,
            total_cost=12500.0
        )
        
        assert success is True
        assert mock_slack.called
        
        # Verify Slack message format
        call_args = mock_slack.call_args[0][0]
        assert 'attachments' in call_args
        assert call_args['attachments'][0]['color'] == 'warning'  # SELL is warning


class TestRiskAlerts:
    """Test risk violation alerts"""
    
    @patch.object(AlertManager, '_send_email')
    def test_send_risk_alert_position_size(self, mock_email):
        """Test sending position size violation alert"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        success = alerts.send_risk_alert(
            violation_type='position_size',
            message='Position size exceeds 10% limit',
            symbol='AAPL',
            severity=AlertSeverity.HIGH,
            details={
                'requested_size': 15000,
                'max_allowed': 10000,
                'current_portfolio': 100000
            }
        )
        
        assert success is True
        assert len(alerts.alert_history) == 1
        
        history_entry = alerts.alert_history[0]
        assert history_entry['type'] == AlertType.RISK.value
        assert history_entry['violation_type'] == 'position_size'
        assert history_entry['severity'] == AlertSeverity.HIGH.value
        assert 'requested_size' in history_entry['details']
    
    @patch.object(AlertManager, '_send_slack')
    def test_send_risk_alert_daily_loss(self, mock_slack):
        """Test sending daily loss limit alert"""
        mock_slack.return_value = True
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        success = alerts.send_risk_alert(
            violation_type='daily_loss',
            message='Daily loss limit exceeded',
            severity=AlertSeverity.CRITICAL,
            details={
                'current_loss': -2500,
                'max_loss': -2000,
                'portfolio_value': 100000
            }
        )
        
        assert success is True
        
        # Verify Slack message has danger color
        call_args = mock_slack.call_args[0][0]
        assert call_args['attachments'][0]['color'] == 'danger'


class TestPnLAlerts:
    """Test P&L change alerts"""
    
    @patch.object(AlertManager, '_send_email')
    def test_send_pnl_alert_gain(self, mock_email):
        """Test sending P&L gain alert"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"],
            min_pnl_percent=2.0
        )
        
        success = alerts.send_pnl_alert(
            current_value=115000.0,
            previous_value=112500.0,
            change_percent=2.22
        )
        
        assert success is True
        assert len(alerts.alert_history) == 1
        
        history_entry = alerts.alert_history[0]
        assert history_entry['type'] == AlertType.PNL.value
        assert history_entry['change_percent'] == 2.22
        assert history_entry['change_amount'] == 2500.0
    
    @patch.object(AlertManager, '_send_slack')
    def test_send_pnl_alert_loss(self, mock_slack):
        """Test sending P&L loss alert"""
        mock_slack.return_value = True
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test",
            min_pnl_percent=2.0
        )
        
        success = alerts.send_pnl_alert(
            current_value=97500.0,
            previous_value=100000.0,
            change_percent=-2.5
        )
        
        assert success is True
        
        # Verify Slack message has danger color for loss
        call_args = mock_slack.call_args[0][0]
        assert call_args['attachments'][0]['color'] == 'danger'
    
    def test_pnl_alert_below_threshold(self):
        """Test P&L alert not sent when below threshold"""
        alerts = AlertManager(
            email_enabled=False,
            min_pnl_percent=2.0
        )
        
        # Small change below threshold
        success = alerts.send_pnl_alert(
            current_value=101000.0,
            previous_value=100000.0,
            change_percent=1.0
        )
        
        assert success is False
        assert len(alerts.alert_history) == 0
    
    @patch.object(AlertManager, '_send_email')
    def test_pnl_alert_auto_severity(self, mock_email):
        """Test automatic severity determination based on P&L change"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"],
            min_pnl_percent=2.0
        )
        
        # Small change (>= 2%, < 3%) -> LOW severity
        alerts.send_pnl_alert(
            current_value=102500.0,
            previous_value=100000.0,
            change_percent=2.5
        )
        assert alerts.alert_history[-1]['severity'] == AlertSeverity.LOW.value
        
        # Medium change (>= 3%, < 5%) -> MEDIUM severity
        alerts.send_pnl_alert(
            current_value=104000.0,
            previous_value=100000.0,
            change_percent=4.0
        )
        assert alerts.alert_history[-1]['severity'] == AlertSeverity.MEDIUM.value
        
        # Large change (>= 5%) -> HIGH severity
        alerts.send_pnl_alert(
            current_value=106000.0,
            previous_value=100000.0,
            change_percent=6.0
        )
        assert alerts.alert_history[-1]['severity'] == AlertSeverity.HIGH.value


class TestDailySummary:
    """Test daily summary alerts"""
    
    @patch.object(AlertManager, '_send_email')
    def test_send_daily_summary_basic(self, mock_email):
        """Test sending basic daily summary"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        success = alerts.send_daily_summary(
            total_trades=5,
            total_pnl=2500.0,
            win_rate=80.0,
            portfolio_value=115000.0
        )
        
        assert success is True
        assert len(alerts.alert_history) == 1
        
        history_entry = alerts.alert_history[0]
        assert history_entry['type'] == AlertType.DAILY_SUMMARY.value
        assert history_entry['total_trades'] == 5
        assert history_entry['total_pnl'] == 2500.0
        assert history_entry['win_rate'] == 80.0
    
    @patch.object(AlertManager, '_send_slack')
    def test_send_daily_summary_with_performers(self, mock_slack):
        """Test sending daily summary with top/worst performers"""
        mock_slack.return_value = True
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        success = alerts.send_daily_summary(
            total_trades=10,
            total_pnl=1500.0,
            win_rate=70.0,
            portfolio_value=112000.0,
            top_performers=[
                {'symbol': 'AAPL', 'pnl': 5.2},
                {'symbol': 'TSLA', 'pnl': 3.8}
            ],
            worst_performers=[
                {'symbol': 'AMD', 'pnl': -2.1}
            ]
        )
        
        assert success is True
        
        # Verify color based on positive P&L
        call_args = mock_slack.call_args[0][0]
        assert call_args['attachments'][0]['color'] == 'good'


class TestErrorAlerts:
    """Test error and warning alerts"""
    
    @patch.object(AlertManager, '_send_email')
    @patch.object(AlertManager, '_send_slack')
    def test_send_error_alert(self, mock_slack, mock_email):
        """Test sending system error alert"""
        mock_email.return_value = True
        mock_slack.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            slack_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"],
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        success = alerts.send_error_alert(
            error_message="Failed to execute order",
            error_type="OrderExecutionError",
            traceback="Traceback (most recent call last):\n  ...",
            severity=AlertSeverity.CRITICAL
        )
        
        assert success is True
        assert mock_email.called
        assert mock_slack.called
        
        history_entry = alerts.alert_history[0]
        assert history_entry['type'] == AlertType.ERROR.value
        assert history_entry['severity'] == AlertSeverity.CRITICAL.value
        assert history_entry['error_type'] == "OrderExecutionError"


class TestEmailDelivery:
    """Test email delivery (mocked SMTP)"""
    
    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp):
        """Test successful email delivery"""
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        alerts = AlertManager(
            email_enabled=True,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        success = alerts._send_email(
            subject="Test Alert",
            message="Test message"
        )
        
        assert success is True
        assert mock_server.starttls.called
        assert mock_server.login.called
        assert mock_server.send_message.called
    
    @patch('smtplib.SMTP')
    def test_send_email_failure(self, mock_smtp):
        """Test email delivery failure"""
        # Mock SMTP error
        mock_smtp.side_effect = smtplib.SMTPException("Connection failed")
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        success = alerts._send_email(
            subject="Test Alert",
            message="Test message"
        )
        
        assert success is False


class TestSlackDelivery:
    """Test Slack delivery (mocked HTTP)"""
    
    @patch('requests.post')
    def test_send_slack_success(self, mock_post):
        """Test successful Slack delivery"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        message = {
            "text": "Test alert",
            "attachments": []
        }
        
        success = alerts._send_slack(message)
        
        assert success is True
        assert mock_post.called
    
    @patch('requests.post')
    def test_send_slack_failure(self, mock_post):
        """Test Slack delivery failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid webhook"
        mock_post.return_value = mock_response
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        message = {"text": "Test alert"}
        success = alerts._send_slack(message)
        
        assert success is False
    
    @patch('requests.post')
    def test_send_slack_exception(self, mock_post):
        """Test Slack delivery with exception"""
        # Mock exception
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        alerts = AlertManager(
            slack_enabled=True,
            slack_webhook_url="https://hooks.slack.com/test"
        )
        
        message = {"text": "Test alert"}
        success = alerts._send_slack(message)
        
        assert success is False


class TestAlertHistory:
    """Test alert history tracking"""
    
    @patch.object(AlertManager, '_send_email')
    def test_get_alert_history_all(self, mock_email):
        """Test retrieving all alert history"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        # Send multiple alerts
        alerts.send_trade_alert('AAPL', 'BUY', 100, 150.0, 15000.0)
        alerts.send_risk_alert('position_size', 'Test violation')
        alerts.send_pnl_alert(115000.0, 112500.0, 2.22)
        
        history = alerts.get_alert_history()
        assert len(history) == 3
    
    @patch.object(AlertManager, '_send_email')
    def test_get_alert_history_filtered(self, mock_email):
        """Test retrieving filtered alert history"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        # Send multiple alerts
        alerts.send_trade_alert('AAPL', 'BUY', 100, 150.0, 15000.0)
        alerts.send_trade_alert('TSLA', 'SELL', 50, 250.0, 12500.0)
        alerts.send_risk_alert('position_size', 'Test violation')
        
        # Get only trade alerts
        trade_history = alerts.get_alert_history(alert_type=AlertType.TRADE)
        assert len(trade_history) == 2
        
        # Get only risk alerts
        risk_history = alerts.get_alert_history(alert_type=AlertType.RISK)
        assert len(risk_history) == 1
    
    @patch.object(AlertManager, '_send_email')
    def test_get_alert_history_limit(self, mock_email):
        """Test retrieving limited alert history"""
        mock_email.return_value = True
        
        alerts = AlertManager(
            email_enabled=True,
            email_from="test@example.com",
            email_password="password",
            email_to=["recipient@example.com"]
        )
        
        # Send 5 alerts
        for i in range(5):
            alerts.send_trade_alert('AAPL', 'BUY', 100, 150.0, 15000.0)
        
        # Get only last 3
        history = alerts.get_alert_history(limit=3)
        assert len(history) == 3
    
    def test_clear_history(self):
        """Test clearing alert history"""
        alerts = AlertManager(email_enabled=False)
        
        # Manually add some history
        alerts.alert_history = [
            {'type': 'trade', 'timestamp': '2025-10-22T12:00:00'},
            {'type': 'risk', 'timestamp': '2025-10-22T13:00:00'}
        ]
        
        assert len(alerts.alert_history) == 2
        
        alerts.clear_history()
        assert len(alerts.alert_history) == 0


class TestSingleton:
    """Test singleton pattern for alert manager"""
    
    def test_singleton_instance(self):
        """Test that get_alert_manager returns singleton"""
        # Clear any existing instance
        import wawatrader.alerts
        wawatrader.alerts._alert_manager_instance = None
        
        # Get two instances
        alerts1 = get_alert_manager(email_enabled=False, slack_enabled=False)
        alerts2 = get_alert_manager(email_enabled=False, slack_enabled=False)
        
        # Should be same instance
        assert alerts1 is alerts2
    
    @patch.dict('os.environ', {
        'ALERT_EMAIL_ENABLED': 'true',
        'ALERT_EMAIL_FROM': 'test@example.com',
        'ALERT_EMAIL_PASSWORD': 'password',
        'ALERT_EMAIL_TO': 'recipient1@example.com,recipient2@example.com',
        'ALERT_SLACK_ENABLED': 'true',
        'ALERT_SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test',
        'ALERT_MIN_PNL_PERCENT': '3.0'
    })
    def test_singleton_from_environment(self):
        """Test singleton configuration from environment variables"""
        # Clear any existing instance
        import wawatrader.alerts
        wawatrader.alerts._alert_manager_instance = None
        
        alerts = get_alert_manager()
        
        assert alerts.email_enabled is True
        assert alerts.email_from == 'test@example.com'
        assert len(alerts.email_to) == 2
        assert alerts.slack_enabled is True
        assert alerts.min_pnl_percent == 3.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
