import smtplib
import logging
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending trading notifications"""

    def __init__(self, config: Dict):
        self.config = config
        self.email_enabled = config.get('email_enabled', False)
        self.slack_enabled = config.get('slack_enabled', False)

    def send_trade_notification(self, trade_info: Dict) -> None:
        """Send notification when trade is executed"""
        try:
            message = self._format_trade_message(trade_info)

            if self.email_enabled:
                self._send_email("Trade Executed", message)

            if self.slack_enabled:
                self._send_slack_message(message)

            logger.info(f"Trade notification sent for {trade_info.get('symbol')}")

        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")

    def send_daily_summary(self, summary: Dict) -> None:
        """Send daily performance summary"""
        try:
            message = self._format_daily_summary(summary)

            if self.email_enabled:
                self._send_email("Daily Trading Summary", message)

            logger.info("Daily summary notification sent")

        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")

    def send_risk_alert(self, risk_info: Dict) -> None:
        """Send risk management alerts"""
        try:
            message = self._format_risk_alert(risk_info)

            if self.email_enabled:
                self._send_email("⚠️ Risk Alert", message)

            if self.slack_enabled:
                self._send_slack_message(f"⚠️ RISK ALERT: {message}")

            logger.warning(f"Risk alert sent: {risk_info.get('alert_type')}")

        except Exception as e:
            logger.error(f"Error sending risk alert: {e}")

    def _format_trade_message(self, trade_info: Dict) -> str:
        """Format trade information for notifications"""
        return f"""
🔔 TRADE EXECUTED
Strategy: {trade_info.get('strategy', 'Unknown')}
Symbol: {trade_info.get('symbol')}
Action: {trade_info.get('action')}
Quantity: {trade_info.get('quantity')}
Price: ₹{trade_info.get('price', 0):.2f}
Stop Loss: ₹{trade_info.get('stop_loss', 0):.2f}
Target: ₹{trade_info.get('target', 0):.2f}
Time: {datetime.now().strftime('%H:%M:%S')}
        """.strip()

    def _format_daily_summary(self, summary: Dict) -> str:
        """Format daily summary for notifications"""
        return f"""
📊 DAILY TRADING SUMMARY
Date: {datetime.now().strftime('%Y-%m-%d')}

Portfolio Performance:
• Total P&L: ₹{summary.get('total_pnl', 0):.2f}
• Day P&L: ₹{summary.get('daily_pnl', 0):.2f}
• Active Positions: {summary.get('total_positions', 0)}

Strategy Breakdown:
• Gap-Up Short: {summary.get('gap_up_positions', 0)} positions, ₹{summary.get('gap_up_pnl', 0):.2f}
• Breakout: {summary.get('breakout_positions', 0)} positions, ₹{summary.get('breakout_pnl', 0):.2f}

Trades Today: {summary.get('trades_today', 0)}
Win Rate: {summary.get('win_rate', 0):.1f}%
        """.strip()

    def _format_risk_alert(self, risk_info: Dict) -> str:
        """Format risk alert message"""
        return f"""
Alert Type: {risk_info.get('alert_type')}
Current Portfolio: ₹{risk_info.get('current_value', 0):.2f}
Daily P&L: {risk_info.get('daily_pnl_pct', 0):.2f}%
Risk Level: {risk_info.get('risk_level', 'Unknown')}
Action Required: {risk_info.get('action_required', 'Monitor')}
        """.strip()

    def _send_email(self, subject: str, message: str) -> None:
        """Send email notification"""
        try:
            if not self.config.get('smtp_server'):
                return

            msg = MimeMultipart()
            msg['From'] = self.config['smtp_username']
            msg['To'] = self.config['notification_email']
            msg['Subject'] = subject

            msg.attach(MimeText(message, 'plain'))

            server = smtplib.SMTP(self.config['smtp_server'], self.config.get('smtp_port', 587))
            server.starttls()
            server.login(self.config['smtp_username'], self.config['smtp_password'])
            server.send_message(msg)
            server.quit()

        except Exception as e:
            logger.error(f"Error sending email: {e}")

    def _send_slack_message(self, message: str) -> None:
        """Send Slack notification"""
        try:
            # Implementation would use slack_sdk
            # For now, just log the message
            logger.info(f"Slack message: {message}")
        except Exception as e:
            logger.error(f"Error sending Slack message: {e}")