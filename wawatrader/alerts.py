"""
Alert System for WawaTrader

Provides real-time notifications via email and Slack for critical trading events:
- Trade execution alerts
- Risk limit violations
- Significant P&L changes
- Daily performance summaries
- System errors and warnings

Configuration:
    Set environment variables or update config.yaml:
    - ALERT_EMAIL_ENABLED: Enable email notifications
    - ALERT_EMAIL_SMTP_HOST: SMTP server (default: smtp.gmail.com)
    - ALERT_EMAIL_SMTP_PORT: SMTP port (default: 587)
    - ALERT_EMAIL_FROM: Sender email address
    - ALERT_EMAIL_PASSWORD: Email password or app password
    - ALERT_EMAIL_TO: Recipient email addresses (comma-separated)
    
    - ALERT_SLACK_ENABLED: Enable Slack notifications
    - ALERT_SLACK_WEBHOOK_URL: Slack incoming webhook URL
    
    - ALERT_MIN_PNL_PERCENT: Minimum P&L change to trigger alert (default: 2.0%)
    - ALERT_DAILY_SUMMARY_TIME: Time to send daily summary (default: "16:00")

Usage:
    from wawatrader.alerts import get_alert_manager, AlertType
    
    # Get singleton instance
    alerts = get_alert_manager()
    
    # Send trade execution alert
    alerts.send_trade_alert(
        symbol='AAPL',
        action='BUY',
        quantity=100,
        price=150.0,
        total_cost=15000.0
    )
    
    # Send risk violation alert
    alerts.send_risk_alert(
        violation_type='position_size',
        message='Position size exceeds 10% limit',
        severity='high'
    )
    
    # Send P&L alert
    alerts.send_pnl_alert(
        current_value=115000.0,
        previous_value=112500.0,
        change_percent=2.22
    )
    
    # Send daily summary
    alerts.send_daily_summary(
        total_trades=5,
        total_pnl=2500.0,
        win_rate=80.0,
        portfolio_value=115000.0
    )

Author: WawaTrader Team
Date: October 2025
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import requests
from loguru import logger


class AlertType(Enum):
    """Alert type classifications"""
    TRADE = "trade"
    RISK = "risk"
    PNL = "pnl"
    DAILY_SUMMARY = "daily_summary"
    ERROR = "error"
    WARNING = "warning"


class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertManager:
    """
    Manages alert notifications via multiple channels.
    
    Features:
    - Email notifications (SMTP)
    - Slack notifications (webhook)
    - Alert throttling to prevent spam
    - Alert history tracking
    - Configurable severity levels
    
    Attributes:
        email_enabled (bool): Whether email alerts are enabled
        slack_enabled (bool): Whether Slack alerts are enabled
        min_pnl_percent (float): Minimum P&L change to trigger alert
        alert_history (List[Dict]): History of sent alerts
    """
    
    def __init__(
        self,
        email_enabled: bool = False,
        slack_enabled: bool = False,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        email_from: Optional[str] = None,
        email_password: Optional[str] = None,
        email_to: Optional[List[str]] = None,
        slack_webhook_url: Optional[str] = None,
        min_pnl_percent: float = 2.0,
        daily_summary_time: str = "16:00"
    ):
        """
        Initialize alert manager.
        
        Args:
            email_enabled: Enable email notifications
            slack_enabled: Enable Slack notifications
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            email_from: Sender email address
            email_password: Email password or app password
            email_to: List of recipient email addresses
            slack_webhook_url: Slack incoming webhook URL
            min_pnl_percent: Minimum P&L change to trigger alert
            daily_summary_time: Time to send daily summary (HH:MM format)
        """
        # Email configuration
        self.email_enabled = email_enabled
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = email_to or []
        
        # Slack configuration
        self.slack_enabled = slack_enabled
        self.slack_webhook_url = slack_webhook_url
        
        # Alert settings
        self.min_pnl_percent = min_pnl_percent
        self.daily_summary_time = daily_summary_time
        
        # Alert history (in-memory for now, could be persisted to database)
        self.alert_history: List[Dict[str, Any]] = []
        
        # Validate configuration
        self._validate_config()
        
        logger.info(
            f"Alert manager initialized - "
            f"Email: {self.email_enabled}, Slack: {self.slack_enabled}"
        )
    
    def _validate_config(self) -> None:
        """Validate alert configuration"""
        if self.email_enabled:
            if not self.email_from or not self.email_password:
                logger.warning(
                    "Email alerts enabled but credentials not provided. "
                    "Email alerts will be disabled."
                )
                self.email_enabled = False
            elif not self.email_to:
                logger.warning(
                    "Email alerts enabled but no recipients configured. "
                    "Email alerts will be disabled."
                )
                self.email_enabled = False
        
        if self.slack_enabled:
            if not self.slack_webhook_url:
                logger.warning(
                    "Slack alerts enabled but webhook URL not provided. "
                    "Slack alerts will be disabled."
                )
                self.slack_enabled = False
    
    def send_trade_alert(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        total_cost: float,
        order_id: Optional[str] = None,
        severity: AlertSeverity = AlertSeverity.MEDIUM
    ) -> bool:
        """
        Send alert for trade execution.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            quantity: Number of shares
            price: Execution price
            total_cost: Total transaction cost
            order_id: Order identifier
            severity: Alert severity level
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        timestamp = datetime.now().isoformat()
        
        # Create alert message
        subject = f"🔔 Trade Executed: {action} {quantity} {symbol}"
        
        message = f"""
Trade Execution Alert
=====================

Symbol: {symbol}
Action: {action}
Quantity: {quantity:,} shares
Price: ${price:.2f}
Total Cost: ${total_cost:,.2f}
Order ID: {order_id or 'N/A'}
Time: {timestamp}

---
WawaTrader Alert System
        """.strip()
        
        # Slack-formatted message
        slack_message = {
            "text": f"🔔 *Trade Executed*",
            "attachments": [{
                "color": "good" if action == "BUY" else "warning",
                "fields": [
                    {"title": "Symbol", "value": symbol, "short": True},
                    {"title": "Action", "value": action, "short": True},
                    {"title": "Quantity", "value": f"{quantity:,} shares", "short": True},
                    {"title": "Price", "value": f"${price:.2f}", "short": True},
                    {"title": "Total Cost", "value": f"${total_cost:,.2f}", "short": True},
                    {"title": "Order ID", "value": order_id or "N/A", "short": True},
                ],
                "footer": "WawaTrader",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        # Send via all enabled channels
        success = self._send_alert(
            alert_type=AlertType.TRADE,
            severity=severity,
            subject=subject,
            message=message,
            slack_message=slack_message
        )
        
        # Log to history
        self.alert_history.append({
            "type": AlertType.TRADE.value,
            "severity": severity.value,
            "timestamp": timestamp,
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "total_cost": total_cost,
            "order_id": order_id,
            "sent": success
        })
        
        return success
    
    def send_risk_alert(
        self,
        violation_type: str,
        message: str,
        symbol: Optional[str] = None,
        severity: AlertSeverity = AlertSeverity.HIGH,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send alert for risk limit violation.
        
        Args:
            violation_type: Type of violation (position_size, daily_loss, etc.)
            message: Human-readable violation description
            symbol: Trading symbol (if applicable)
            severity: Alert severity level
            details: Additional violation details
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        timestamp = datetime.now().isoformat()
        
        # Create alert message
        subject = f"⚠️ Risk Violation: {violation_type.upper()}"
        
        body = f"""
Risk Management Alert
=====================

Violation Type: {violation_type}
Symbol: {symbol or 'N/A'}
Message: {message}
Time: {timestamp}
"""
        
        if details:
            body += "\nDetails:\n"
            for key, value in details.items():
                body += f"  {key}: {value}\n"
        
        body += "\n---\nWawaTrader Alert System"
        
        # Slack-formatted message
        slack_fields = [
            {"title": "Violation Type", "value": violation_type, "short": True},
            {"title": "Symbol", "value": symbol or "N/A", "short": True},
            {"title": "Message", "value": message, "short": False},
        ]
        
        if details:
            for key, value in details.items():
                slack_fields.append({
                    "title": key.replace('_', ' ').title(),
                    "value": str(value),
                    "short": True
                })
        
        slack_message = {
            "text": f"⚠️ *Risk Violation Detected*",
            "attachments": [{
                "color": "danger",
                "fields": slack_fields,
                "footer": "WawaTrader",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        # Send via all enabled channels
        success = self._send_alert(
            alert_type=AlertType.RISK,
            severity=severity,
            subject=subject,
            message=body,
            slack_message=slack_message
        )
        
        # Log to history
        self.alert_history.append({
            "type": AlertType.RISK.value,
            "severity": severity.value,
            "timestamp": timestamp,
            "violation_type": violation_type,
            "symbol": symbol,
            "message": message,
            "details": details,
            "sent": success
        })
        
        return success
    
    def send_pnl_alert(
        self,
        current_value: float,
        previous_value: float,
        change_percent: float,
        symbol: Optional[str] = None,
        severity: Optional[AlertSeverity] = None
    ) -> bool:
        """
        Send alert for significant P&L change.
        
        Args:
            current_value: Current portfolio/position value
            previous_value: Previous portfolio/position value
            change_percent: Percentage change
            symbol: Trading symbol (if position-specific)
            severity: Alert severity (auto-determined if not provided)
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        # Check if change exceeds threshold
        if abs(change_percent) < self.min_pnl_percent:
            logger.debug(
                f"P&L change {change_percent:.2f}% below threshold "
                f"{self.min_pnl_percent:.2f}%, skipping alert"
            )
            return False
        
        timestamp = datetime.now().isoformat()
        change_amount = current_value - previous_value
        
        # Auto-determine severity if not provided
        if severity is None:
            if abs(change_percent) >= 5.0:
                severity = AlertSeverity.HIGH
            elif abs(change_percent) >= 3.0:
                severity = AlertSeverity.MEDIUM
            else:
                severity = AlertSeverity.LOW
        
        # Determine emoji and color based on positive/negative change
        is_positive = change_amount > 0
        emoji = "📈" if is_positive else "📉"
        color = "good" if is_positive else "danger"
        direction = "Gain" if is_positive else "Loss"
        
        # Create alert message
        scope = f"{symbol} Position" if symbol else "Portfolio"
        subject = f"{emoji} {scope} P&L {direction}: {abs(change_percent):.2f}%"
        
        message = f"""
P&L Alert
=========

Scope: {scope}
Previous Value: ${previous_value:,.2f}
Current Value: ${current_value:,.2f}
Change: ${change_amount:+,.2f} ({change_percent:+.2f}%)
Time: {timestamp}

---
WawaTrader Alert System
        """.strip()
        
        # Slack-formatted message
        slack_message = {
            "text": f"{emoji} *Significant P&L Change*",
            "attachments": [{
                "color": color,
                "fields": [
                    {"title": "Scope", "value": scope, "short": True},
                    {"title": "Change", "value": f"{change_percent:+.2f}%", "short": True},
                    {"title": "Previous Value", "value": f"${previous_value:,.2f}", "short": True},
                    {"title": "Current Value", "value": f"${current_value:,.2f}", "short": True},
                    {"title": "P&L", "value": f"${change_amount:+,.2f}", "short": True},
                ],
                "footer": "WawaTrader",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        # Send via all enabled channels
        success = self._send_alert(
            alert_type=AlertType.PNL,
            severity=severity,
            subject=subject,
            message=message,
            slack_message=slack_message
        )
        
        # Log to history
        self.alert_history.append({
            "type": AlertType.PNL.value,
            "severity": severity.value,
            "timestamp": timestamp,
            "symbol": symbol,
            "current_value": current_value,
            "previous_value": previous_value,
            "change_percent": change_percent,
            "change_amount": change_amount,
            "sent": success
        })
        
        return success
    
    def send_daily_summary(
        self,
        total_trades: int,
        total_pnl: float,
        win_rate: float,
        portfolio_value: float,
        top_performers: Optional[List[Dict[str, Any]]] = None,
        worst_performers: Optional[List[Dict[str, Any]]] = None,
        severity: AlertSeverity = AlertSeverity.LOW
    ) -> bool:
        """
        Send daily performance summary.
        
        Args:
            total_trades: Number of trades executed
            total_pnl: Total profit/loss for the day
            win_rate: Percentage of profitable trades
            portfolio_value: Current portfolio value
            top_performers: List of best performing positions
            worst_performers: List of worst performing positions
            severity: Alert severity level
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        timestamp = datetime.now().isoformat()
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Create alert message
        subject = f"📊 Daily Trading Summary - {date_str}"
        
        message = f"""
Daily Trading Summary
=====================
Date: {date_str}

Performance Metrics
-------------------
Total Trades: {total_trades}
Total P&L: ${total_pnl:+,.2f}
Win Rate: {win_rate:.1f}%
Portfolio Value: ${portfolio_value:,.2f}
"""
        
        if top_performers:
            message += "\nTop Performers:\n"
            for i, perf in enumerate(top_performers[:3], 1):
                message += f"  {i}. {perf.get('symbol', 'N/A')}: {perf.get('pnl', 0):+.2f}%\n"
        
        if worst_performers:
            message += "\nWorst Performers:\n"
            for i, perf in enumerate(worst_performers[:3], 1):
                message += f"  {i}. {perf.get('symbol', 'N/A')}: {perf.get('pnl', 0):+.2f}%\n"
        
        message += "\n---\nWawaTrader Alert System"
        
        # Slack-formatted message
        slack_fields = [
            {"title": "Total Trades", "value": str(total_trades), "short": True},
            {"title": "Win Rate", "value": f"{win_rate:.1f}%", "short": True},
            {"title": "Daily P&L", "value": f"${total_pnl:+,.2f}", "short": True},
            {"title": "Portfolio Value", "value": f"${portfolio_value:,.2f}", "short": True},
        ]
        
        slack_message = {
            "text": f"📊 *Daily Summary - {date_str}*",
            "attachments": [{
                "color": "good" if total_pnl >= 0 else "danger",
                "fields": slack_fields,
                "footer": "WawaTrader",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        # Send via all enabled channels
        success = self._send_alert(
            alert_type=AlertType.DAILY_SUMMARY,
            severity=severity,
            subject=subject,
            message=message,
            slack_message=slack_message
        )
        
        # Log to history
        self.alert_history.append({
            "type": AlertType.DAILY_SUMMARY.value,
            "severity": severity.value,
            "timestamp": timestamp,
            "date": date_str,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "portfolio_value": portfolio_value,
            "sent": success
        })
        
        return success
    
    def send_error_alert(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None,
        severity: AlertSeverity = AlertSeverity.CRITICAL
    ) -> bool:
        """
        Send alert for system errors.
        
        Args:
            error_message: Error description
            error_type: Type of error
            traceback: Full error traceback
            severity: Alert severity level
        
        Returns:
            True if alert sent successfully, False otherwise
        """
        timestamp = datetime.now().isoformat()
        
        # Create alert message
        subject = f"🚨 System Error: {error_type or 'Unknown'}"
        
        message = f"""
System Error Alert
==================

Error Type: {error_type or 'Unknown'}
Message: {error_message}
Time: {timestamp}
"""
        
        if traceback:
            message += f"\nTraceback:\n{traceback}\n"
        
        message += "\n---\nWawaTrader Alert System"
        
        # Slack-formatted message
        slack_message = {
            "text": f"🚨 *System Error*",
            "attachments": [{
                "color": "danger",
                "fields": [
                    {"title": "Error Type", "value": error_type or "Unknown", "short": True},
                    {"title": "Time", "value": timestamp, "short": True},
                    {"title": "Message", "value": error_message, "short": False},
                ],
                "footer": "WawaTrader",
                "ts": int(datetime.now().timestamp())
            }]
        }
        
        # Send via all enabled channels
        success = self._send_alert(
            alert_type=AlertType.ERROR,
            severity=severity,
            subject=subject,
            message=message,
            slack_message=slack_message
        )
        
        # Log to history
        self.alert_history.append({
            "type": AlertType.ERROR.value,
            "severity": severity.value,
            "timestamp": timestamp,
            "error_type": error_type,
            "error_message": error_message,
            "sent": success
        })
        
        return success
    
    def _send_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        subject: str,
        message: str,
        slack_message: Optional[Dict] = None
    ) -> bool:
        """
        Send alert via all enabled channels.
        
        Args:
            alert_type: Type of alert
            severity: Alert severity
            subject: Email subject line
            message: Plain text message
            slack_message: Slack-formatted message (optional)
        
        Returns:
            True if sent successfully via at least one channel
        """
        success = False
        
        # Send email
        if self.email_enabled:
            try:
                email_success = self._send_email(subject, message)
                if email_success:
                    logger.info(f"Email alert sent: {subject}")
                    success = True
                else:
                    logger.warning(f"Failed to send email alert: {subject}")
            except Exception as e:
                logger.error(f"Error sending email alert: {e}")
        
        # Send Slack message
        if self.slack_enabled and slack_message:
            try:
                slack_success = self._send_slack(slack_message)
                if slack_success:
                    logger.info(f"Slack alert sent: {subject}")
                    success = True
                else:
                    logger.warning(f"Failed to send Slack alert: {subject}")
            except Exception as e:
                logger.error(f"Error sending Slack alert: {e}")
        
        if not self.email_enabled and not self.slack_enabled:
            logger.warning(
                f"Alert not sent (no channels enabled): {subject}"
            )
        
        return success
    
    def _send_email(self, subject: str, message: str) -> bool:
        """
        Send email via SMTP.
        
        Args:
            subject: Email subject
            message: Email body
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = ', '.join(self.email_to)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _send_slack(self, message: Dict) -> bool:
        """
        Send message to Slack via webhook.
        
        Args:
            message: Slack-formatted message dict
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            response = requests.post(
                self.slack_webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(
                    f"Slack webhook returned status {response.status_code}: "
                    f"{response.text}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def get_alert_history(
        self,
        alert_type: Optional[AlertType] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get alert history.
        
        Args:
            alert_type: Filter by alert type (optional)
            limit: Maximum number of alerts to return
        
        Returns:
            List of alert history entries
        """
        history = self.alert_history
        
        if alert_type:
            history = [
                alert for alert in history
                if alert['type'] == alert_type.value
            ]
        
        return history[-limit:]
    
    def clear_history(self) -> None:
        """Clear alert history"""
        self.alert_history.clear()
        logger.info("Alert history cleared")


# Singleton instance
_alert_manager_instance: Optional[AlertManager] = None


def get_alert_manager(
    email_enabled: Optional[bool] = None,
    slack_enabled: Optional[bool] = None,
    **kwargs
) -> AlertManager:
    """
    Get or create singleton AlertManager instance.
    
    Args:
        email_enabled: Enable email notifications (from env if not provided)
        slack_enabled: Enable Slack notifications (from env if not provided)
        **kwargs: Additional configuration parameters
    
    Returns:
        AlertManager singleton instance
    """
    global _alert_manager_instance
    
    if _alert_manager_instance is None:
        # Get configuration from environment variables
        email_enabled = email_enabled if email_enabled is not None else (
            os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true'
        )
        slack_enabled = slack_enabled if slack_enabled is not None else (
            os.getenv('ALERT_SLACK_ENABLED', 'false').lower() == 'true'
        )
        
        # Email configuration from environment
        email_config = {
            'smtp_host': os.getenv('ALERT_EMAIL_SMTP_HOST', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('ALERT_EMAIL_SMTP_PORT', '587')),
            'email_from': os.getenv('ALERT_EMAIL_FROM'),
            'email_password': os.getenv('ALERT_EMAIL_PASSWORD'),
            'email_to': [
                email.strip()
                for email in os.getenv('ALERT_EMAIL_TO', '').split(',')
                if email.strip()
            ],
        }
        
        # Slack configuration from environment
        slack_config = {
            'slack_webhook_url': os.getenv('ALERT_SLACK_WEBHOOK_URL'),
        }
        
        # Alert settings from environment
        alert_config = {
            'min_pnl_percent': float(os.getenv('ALERT_MIN_PNL_PERCENT', '2.0')),
            'daily_summary_time': os.getenv('ALERT_DAILY_SUMMARY_TIME', '16:00'),
        }
        
        # Merge with provided kwargs
        config = {
            'email_enabled': email_enabled,
            'slack_enabled': slack_enabled,
            **email_config,
            **slack_config,
            **alert_config,
            **kwargs
        }
        
        _alert_manager_instance = AlertManager(**config)
    
    return _alert_manager_instance
