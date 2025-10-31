"""Multi-channel alerting system."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import aiohttp
from loguru import logger
from ..config import get_settings


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert message."""
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class AlertManager:
    """Multi-channel alert management system."""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self.alert_history: List[Alert] = []
        self.rate_limits: Dict[str, datetime] = {}  # For rate limiting
        self.channels: Dict[str, Callable] = {}
        self._setup_channels()
        
    def _setup_channels(self) -> None:
        """Setup available alert channels."""
        if hasattr(self.settings, 'SLACK_WEBHOOK_URL') and self.settings.SLACK_WEBHOOK_URL:
            self.channels['slack'] = self._send_slack_alert
            
        if (hasattr(self.settings, 'EMAIL_SMTP_SERVER') and 
            self.settings.EMAIL_SMTP_SERVER):
            self.channels['email'] = self._send_email_alert
            
        # Always have console logging
        self.channels['console'] = self._send_console_alert
        
        logger.info(f"Initialized alert channels: {list(self.channels.keys())}")
        
    async def send_alert(
        self,
        level: AlertLevel,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None
    ) -> None:
        """Send alert through specified channels."""
        alert = Alert(
            level=level,
            title=title,
            message=message,
            metadata=metadata or {}
        )
        
        # Rate limiting check
        rate_key = f"{title}_{level}"
        if self._is_rate_limited(rate_key):
            logger.debug(f"Alert rate limited: {title}")
            return
            
        # Store in history
        self.alert_history.append(alert)
        if len(self.alert_history) > 1000:  # Keep last 1000 alerts
            self.alert_history.pop(0)
            
        # Send through channels
        target_channels = channels or list(self.channels.keys())
        
        for channel in target_channels:
            if channel in self.channels:
                try:
                    await self.channels[channel](alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
            else:
                logger.warning(f"Unknown alert channel: {channel}")
                
        logger.info(f"Alert sent [{level}]: {title}")
        
    def _is_rate_limited(self, key: str, min_interval_seconds: int = 300) -> bool:
        """Check if alert should be rate limited."""
        now = datetime.now()
        last_sent = self.rate_limits.get(key)
        
        if last_sent and (now - last_sent).seconds < min_interval_seconds:
            return True
            
        self.rate_limits[key] = now
        return False
        
    async def _send_slack_alert(self, alert: Alert) -> None:
        """Send alert to Slack webhook."""
        if not hasattr(self.settings, 'SLACK_WEBHOOK_URL'):
            return
            
        color_map = {
            AlertLevel.INFO: "#36a64f",      # Green
            AlertLevel.WARNING: "#ffb000",   # Orange  
            AlertLevel.ERROR: "#ff0000",     # Red
            AlertLevel.CRITICAL: "#8B0000"   # Dark red
        }
        
        payload = {
            "attachments": [{
                "color": color_map.get(alert.level, "#808080"),
                "title": f"[{alert.level.upper()}] {alert.title}",
                "text": alert.message,
                "footer": "Alpha Genesis Pro",
                "ts": int(alert.timestamp.timestamp()),
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in alert.metadata.items()
                ]
            }]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.settings.SLACK_WEBHOOK_URL, 
                json=payload
            ) as response:
                if response.status != 200:
                    logger.error(f"Slack webhook failed: {response.status}")
                    
    async def _send_email_alert(self, alert: Alert) -> None:
        """Send alert via email."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            if not all([
                hasattr(self.settings, 'EMAIL_SMTP_SERVER'),
                hasattr(self.settings, 'EMAIL_FROM'), 
                hasattr(self.settings, 'EMAIL_PASSWORD')
            ]):
                return
                
            msg = MIMEMultipart()
            msg['From'] = self.settings.EMAIL_FROM
            msg['To'] = self.settings.EMAIL_FROM  # Send to self for now
            msg['Subject'] = f"[{alert.level.upper()}] {alert.title}"
            
            body = f"""
            Alert Level: {alert.level.upper()}
            Title: {alert.title}
            Message: {alert.message}
            Timestamp: {alert.timestamp}
            
            Metadata:
            {json.dumps(alert.metadata, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp_email, msg)
            
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
            
    def _send_smtp_email(self, msg: Any) -> None:
        """Send email via SMTP (blocking operation)."""
        import smtplib
        
        server = smtplib.SMTP(self.settings.EMAIL_SMTP_SERVER, self.settings.EMAIL_SMTP_PORT)
        server.starttls()
        server.login(self.settings.EMAIL_FROM, self.settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
    async def _send_console_alert(self, alert: Alert) -> None:
        """Send alert to console/logs."""
        log_func = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(alert.level, logger.info)
        
        log_func(f"ALERT [{alert.level}] {alert.title}: {alert.message}")
        if alert.metadata:
            logger.debug(f"Alert metadata: {alert.metadata}")
            
    # Pre-defined alert methods for common scenarios
    async def alert_trade_executed(
        self, symbol: str, side: str, quantity: float, price: float, pnl: float
    ) -> None:
        """Alert for trade execution."""
        level = AlertLevel.INFO if pnl >= 0 else AlertLevel.WARNING
        await self.send_alert(
            level=level,
            title=f"Trade Executed: {side} {symbol}",
            message=f"Executed {side} {quantity} {symbol} @ ${price:.2f}, PnL: ${pnl:.2f}",
            metadata={
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "pnl": pnl
            }
        )
        
    async def alert_system_error(self, component: str, error: str) -> None:
        """Alert for system errors."""
        await self.send_alert(
            level=AlertLevel.ERROR,
            title=f"System Error: {component}",
            message=f"Component {component} encountered an error: {error}",
            metadata={"component": component, "error": error}
        )
        
    async def alert_risk_breach(
        self, risk_type: str, current_value: float, limit: float
    ) -> None:
        """Alert for risk limit breaches."""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title=f"Risk Breach: {risk_type}",
            message=f"{risk_type} breached: {current_value:.2f} > {limit:.2f}",
            metadata={
                "risk_type": risk_type,
                "current_value": current_value,
                "limit": limit
            }
        )
        
    async def alert_high_drawdown(self, current_dd: float, max_dd: float) -> None:
        """Alert for high drawdown."""
        await self.send_alert(
            level=AlertLevel.CRITICAL,
            title="High Drawdown Alert",
            message=f"Current drawdown {current_dd:.2f}% exceeds limit {max_dd:.2f}%",
            metadata={"current_drawdown": current_dd, "max_drawdown": max_dd}
        )
        
    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get alerts from last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [alert for alert in self.alert_history if alert.timestamp > cutoff]
        
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of recent alerts."""
        recent = self.get_recent_alerts(24)
        
        by_level = {}
        for alert in recent:
            by_level[alert.level] = by_level.get(alert.level, 0) + 1
            
        return {
            "total_alerts_24h": len(recent),
            "by_level": by_level,
            "last_alert": recent[-1].to_dict() if recent else None,
            "available_channels": list(self.channels.keys())
        }