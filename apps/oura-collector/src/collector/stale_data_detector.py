"""Stale data detection and alerting for Oura collector"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import requests

import config

logger = logging.getLogger(__name__)


class StaleDataDetector:
    """Detects stale data and sends alerts via Discord webhook"""

    def __init__(self, storage):
        """Initialize the detector with storage reference

        Args:
            storage: PostgresStorage instance for database queries
        """
        self.storage = storage
        self.threshold_days = config.STALE_DATA_THRESHOLD_DAYS
        self.webhook_url = config.DISCORD_WEBHOOK_URL
        self.alert_enabled = config.ALERT_ON_STALE_DATA
        self._last_alert_time: Optional[datetime] = None
        self._alert_cooldown_hours = 6  # Don't spam alerts

    def check_data_freshness(self) -> Dict[str, dict]:
        """Check the freshness of critical data tables

        Returns:
            Dictionary with table names and their freshness status
        """
        results = {}
        today = datetime.now().date()

        try:
            if not hasattr(self.storage, 'get_session'):
                logger.warning("Storage does not support freshness checks")
                return results

            with self.storage.get_session() as session:
                from sqlalchemy import func, text
                from database_models import SleepPeriod, Activity, DailySleep, Readiness

                # Map table names to models
                table_models = {
                    'sleep_periods': SleepPeriod,
                    'activity': Activity,
                    'daily_sleep': DailySleep,
                    'readiness': Readiness,
                }

                for table_name, model in table_models.items():
                    try:
                        max_date = session.query(func.max(model.date)).scalar()

                        if max_date is None:
                            results[table_name] = {
                                'latest_date': None,
                                'days_old': None,
                                'is_stale': True,
                                'status': 'no_data'
                            }
                        else:
                            days_old = (today - max_date).days
                            is_critical = table_name in config.CRITICAL_TABLES
                            is_stale = days_old > self.threshold_days if is_critical else False

                            results[table_name] = {
                                'latest_date': str(max_date),
                                'days_old': days_old,
                                'is_stale': is_stale,
                                'is_critical': is_critical,
                                'status': 'stale' if is_stale else 'fresh'
                            }

                    except Exception as e:
                        logger.error(f"Error checking {table_name}: {e}")
                        results[table_name] = {
                            'latest_date': None,
                            'days_old': None,
                            'is_stale': None,
                            'status': 'error',
                            'error': str(e)
                        }

        except Exception as e:
            logger.error(f"Error checking data freshness: {e}")

        return results

    def get_stale_tables(self, freshness_results: Dict[str, dict]) -> List[str]:
        """Get list of tables that are stale

        Args:
            freshness_results: Results from check_data_freshness()

        Returns:
            List of stale table names
        """
        return [
            table for table, info in freshness_results.items()
            if info.get('is_stale') and info.get('is_critical')
        ]

    def format_alert_message(self, freshness_results: Dict[str, dict]) -> str:
        """Format a Discord alert message for stale data

        Args:
            freshness_results: Results from check_data_freshness()

        Returns:
            Formatted message string
        """
        stale_tables = self.get_stale_tables(freshness_results)

        if not stale_tables:
            return ""

        lines = [
            "**Oura Ring Data Sync Issue Detected**",
            "",
            "The following data has not been updated recently:",
            ""
        ]

        for table in stale_tables:
            info = freshness_results[table]
            lines.append(f"- **{table}**: Last data from `{info['latest_date']}` ({info['days_old']} days ago)")

        # Add context about what this means
        lines.extend([
            "",
            "**What this means:**",
            "Your Oura ring may not be syncing to the Oura app.",
            "",
            "**How to fix:**",
            "1. Open the Oura app on your phone",
            "2. Pull down to refresh and sync your ring",
            "3. Wait a few minutes for data to sync",
            "4. The collector will pick up new data in the next hour",
            "",
            f"*Alert threshold: {self.threshold_days} days*"
        ])

        return "\n".join(lines)

    def _can_send_alert(self) -> bool:
        """Check if we can send an alert (respects cooldown)"""
        if self._last_alert_time is None:
            return True

        cooldown = timedelta(hours=self._alert_cooldown_hours)
        return datetime.now() - self._last_alert_time > cooldown

    def send_discord_alert(self, message: str) -> bool:
        """Send an alert message to Discord webhook

        Args:
            message: Message to send

        Returns:
            True if sent successfully
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured, skipping alert")
            return False

        if not self._can_send_alert():
            logger.info("Alert cooldown active, skipping Discord notification")
            return False

        try:
            payload = {
                "embeds": [{
                    "title": "Oura Data Stale Alert",
                    "description": message,
                    "color": 15158332,  # Red color
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "footer": {
                        "text": "oura-collector"
                    }
                }]
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            self._last_alert_time = datetime.now()
            logger.info("Discord stale data alert sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    def check_and_alert(self) -> Dict[str, dict]:
        """Main method: check freshness and alert if needed

        Returns:
            Freshness results dictionary
        """
        logger.info("Checking data freshness...")
        results = self.check_data_freshness()

        # Log freshness status
        for table, info in results.items():
            status = info.get('status', 'unknown')
            days_old = info.get('days_old')
            is_critical = info.get('is_critical', False)

            if status == 'stale':
                logger.warning(f"STALE DATA: {table} - last updated {days_old} days ago (critical: {is_critical})")
            elif status == 'fresh':
                logger.info(f"Data fresh: {table} - {days_old} days old")
            elif status == 'no_data':
                logger.warning(f"NO DATA: {table} has no records")
            else:
                logger.error(f"Error checking {table}: {info.get('error', 'unknown')}")

        # Send alert if needed
        stale_tables = self.get_stale_tables(results)
        if stale_tables and self.alert_enabled:
            message = self.format_alert_message(results)
            if message:
                self.send_discord_alert(message)
        elif stale_tables:
            logger.warning(f"Stale data detected but alerting is disabled: {stale_tables}")
        else:
            logger.info("All critical data is fresh")

        return results
