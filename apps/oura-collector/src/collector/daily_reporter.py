"""Daily Health Reporter - Posts daily summaries to Discord and Obsidian vault."""

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
from sqlalchemy import func

from database_models import (
    Activity, DailySleep, Readiness, SleepPeriod,
    Stress, DailySummary
)

logger = logging.getLogger(__name__)


class DailyHealthReporter:
    """Generates and publishes daily health summaries."""

    def __init__(
        self,
        storage,
        discord_webhook_url: Optional[str] = None,
        vault_path: Optional[str] = None,
    ):
        """Initialize the daily reporter.

        Args:
            storage: PostgresStorage instance for database queries
            discord_webhook_url: Discord webhook URL for posting summaries
            vault_path: Path to Obsidian vault for saving markdown files
        """
        self.storage = storage
        self.discord_webhook_url = discord_webhook_url or os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
        self.vault_path = vault_path or os.getenv("OBSIDIAN_VAULT_PATH", "/vault")
        self.health_notes_path = os.path.join(self.vault_path, "Landry", "health")

    def get_daily_data(self, target_date: date) -> Dict[str, Any]:
        """Fetch all health data for a specific date.

        Args:
            target_date: The date to fetch data for

        Returns:
            Dictionary with all health metrics for the date
        """
        data = {
            "date": target_date,
            "sleep": None,
            "activity": None,
            "readiness": None,
            "sleep_period": None,
            "stress": None,
            "previous_day": None,
        }

        try:
            with self.storage.get_session() as session:
                # Daily sleep score
                try:
                    sleep = session.query(DailySleep).filter(
                        DailySleep.date == target_date
                    ).first()
                    if sleep:
                        data["sleep"] = {
                            "score": sleep.sleep_score,
                            "deep_sleep_score": getattr(sleep, 'score_deep_sleep', None),
                            "rem_score": getattr(sleep, 'score_rem_sleep', None),
                            "efficiency_score": getattr(sleep, 'score_efficiency', None),
                            "timing_score": getattr(sleep, 'score_timing', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching sleep data: {e}")

                # Activity
                try:
                    activity = session.query(Activity).filter(
                        Activity.date == target_date
                    ).first()
                    if activity:
                        data["activity"] = {
                            "score": activity.activity_score,
                            "steps": activity.steps,
                            "calories": getattr(activity, 'calories_total', None),
                            "active_calories": getattr(activity, 'calories_active', None),
                            "sedentary_time": (getattr(activity, 'sedentary_minutes', 0) or 0) * 60,
                            "high_activity_time": (getattr(activity, 'high_activity_minutes', 0) or 0) * 60,
                            "medium_activity_time": (getattr(activity, 'medium_activity_minutes', 0) or 0) * 60,
                            "low_activity_time": (getattr(activity, 'low_activity_minutes', 0) or 0) * 60,
                        }
                except Exception as e:
                    logger.warning(f"Error fetching activity data: {e}")

                # Readiness
                try:
                    readiness = session.query(Readiness).filter(
                        Readiness.date == target_date
                    ).first()
                    if readiness:
                        data["readiness"] = {
                            "score": readiness.readiness_score,
                            "resting_hr": readiness.resting_heart_rate,
                            "hrv_balance": getattr(readiness, 'hrv_balance', None),
                            "body_temperature": getattr(readiness, 'score_body_temperature', None),
                            "recovery_index": getattr(readiness, 'score_recovery_index', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching readiness data: {e}")

                # Sleep period details (for duration, HRV)
                try:
                    sleep_period = session.query(SleepPeriod).filter(
                        func.date(SleepPeriod.bedtime_start) == target_date - timedelta(days=1)
                    ).first()
                    if sleep_period:
                        total_hours = (sleep_period.total_sleep_duration or 0) / 3600
                        data["sleep_period"] = {
                            "total_hours": round(total_hours, 1),
                            "deep_sleep_mins": (sleep_period.deep_sleep_duration or 0) // 60,
                            "rem_sleep_mins": (sleep_period.rem_sleep_duration or 0) // 60,
                            "light_sleep_mins": (sleep_period.light_sleep_duration or 0) // 60,
                            "efficiency": sleep_period.efficiency,
                            "avg_hrv": sleep_period.average_hrv,
                            "lowest_hr": sleep_period.lowest_heart_rate,
                        }
                except Exception as e:
                    logger.warning(f"Error fetching sleep period data: {e}")

                # Stress (if available)
                try:
                    stress = session.query(Stress).filter(
                        Stress.date == target_date
                    ).first()
                    if stress:
                        data["stress"] = {
                            "day_summary": getattr(stress, 'day_summary', None),
                            "stress_high": getattr(stress, 'stress_high', None),
                            "recovery_high": getattr(stress, 'recovery_high', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching stress data: {e}")

                # Previous day for comparison
                try:
                    prev_date = target_date - timedelta(days=1)
                    prev_sleep = session.query(DailySleep).filter(DailySleep.date == prev_date).first()
                    prev_activity = session.query(Activity).filter(Activity.date == prev_date).first()
                    prev_readiness = session.query(Readiness).filter(Readiness.date == prev_date).first()

                    data["previous_day"] = {
                        "sleep_score": prev_sleep.sleep_score if prev_sleep else None,
                        "activity_score": prev_activity.activity_score if prev_activity else None,
                        "readiness_score": prev_readiness.readiness_score if prev_readiness else None,
                    }
                except Exception as e:
                    logger.warning(f"Error fetching previous day data: {e}")
                    data["previous_day"] = {"sleep_score": None, "activity_score": None, "readiness_score": None}

        except Exception as e:
            logger.error(f"Error fetching daily data: {e}")

        return data

    def _format_trend(self, current: Optional[int], previous: Optional[int]) -> str:
        """Format a trend indicator."""
        if current is None or previous is None:
            return ""
        diff = current - previous
        if diff > 0:
            return f"↑{diff}"
        elif diff < 0:
            return f"↓{abs(diff)}"
        return "→"

    def _score_emoji(self, score: Optional[int]) -> str:
        """Get an emoji based on score."""
        if score is None:
            return "❓"
        if score >= 85:
            return "🟢"
        elif score >= 70:
            return "🟡"
        elif score >= 50:
            return "🟠"
        return "🔴"

    def format_discord_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format data as a Discord embed.

        Args:
            data: Health data dictionary

        Returns:
            Discord webhook payload with embed
        """
        target_date = data["date"]
        date_str = target_date.strftime("%B %d, %Y")

        # Build description
        lines = []

        # Sleep
        if data["sleep"] and data["sleep_period"]:
            sleep_score = data["sleep"]["score"]
            hours = data["sleep_period"]["total_hours"]
            trend = self._format_trend(sleep_score, data["previous_day"].get("sleep_score"))
            emoji = self._score_emoji(sleep_score)
            lines.append(f"{emoji} **Sleep:** {sleep_score}/100 ({hours}h) {trend}")

            # Sleep details
            deep = data["sleep_period"]["deep_sleep_mins"]
            rem = data["sleep_period"]["rem_sleep_mins"]
            lines.append(f"   └ Deep: {deep}min | REM: {rem}min")

        # Activity
        if data["activity"]:
            activity_score = data["activity"]["score"]
            steps = data["activity"]["steps"]
            trend = self._format_trend(activity_score, data["previous_day"].get("activity_score"))
            emoji = self._score_emoji(activity_score)
            lines.append(f"{emoji} **Activity:** {activity_score}/100 ({steps:,} steps) {trend}")

            # Activity details
            cals = data["activity"]["active_calories"]
            high_mins = (data["activity"]["high_activity_time"] or 0) // 60
            lines.append(f"   └ Active cal: {cals:,} | High activity: {high_mins}min")

        # Readiness
        if data["readiness"]:
            readiness_score = data["readiness"]["score"]
            trend = self._format_trend(readiness_score, data["previous_day"].get("readiness_score"))
            emoji = self._score_emoji(readiness_score)
            lines.append(f"{emoji} **Readiness:** {readiness_score}/100 {trend}")

            # HRV and HR
            rhr = data["readiness"]["resting_hr"]
            if data["sleep_period"] and data["sleep_period"]["avg_hrv"]:
                hrv = data["sleep_period"]["avg_hrv"]
                lines.append(f"   └ Resting HR: {rhr} bpm | HRV: {hrv}ms")
            else:
                lines.append(f"   └ Resting HR: {rhr} bpm")

        # Stress (if available)
        if data["stress"] and data["stress"]["day_summary"]:
            stress_summary = data["stress"]["day_summary"]
            lines.append(f"🧘 **Stress:** {stress_summary}")

        description = "\n".join(lines) if lines else "No data available for this date."

        # Determine embed color based on average score
        scores = []
        if data["sleep"]:
            scores.append(data["sleep"]["score"])
        if data["activity"]:
            scores.append(data["activity"]["score"])
        if data["readiness"]:
            scores.append(data["readiness"]["score"])

        avg_score = sum(scores) / len(scores) if scores else 0
        if avg_score >= 85:
            color = 5763719  # Green
        elif avg_score >= 70:
            color = 16776960  # Yellow
        elif avg_score >= 50:
            color = 16744448  # Orange
        else:
            color = 15158332  # Red

        return {
            "embeds": [{
                "title": f"📊 Daily Health Summary",
                "description": description,
                "color": color,
                "footer": {
                    "text": f"{date_str} • oura-collector"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
        }

    def format_markdown(self, data: Dict[str, Any]) -> str:
        """Format data as Obsidian markdown.

        Args:
            data: Health data dictionary

        Returns:
            Markdown string for Obsidian note
        """
        target_date = data["date"]
        date_str = target_date.strftime("%Y-%m-%d")
        date_display = target_date.strftime("%B %d, %Y")

        lines = [
            f"---",
            f"date: {date_str}",
            f"type: health-daily",
            f"tags: [health, oura, daily-summary]",
        ]

        # Add scores to frontmatter
        if data["sleep"]:
            lines.append(f"sleep_score: {data['sleep']['score']}")
        if data["activity"]:
            lines.append(f"activity_score: {data['activity']['score']}")
        if data["readiness"]:
            lines.append(f"readiness_score: {data['readiness']['score']}")

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"# Daily Health Summary - {date_display}")
        lines.append(f"")

        # Sleep Section
        lines.append(f"## 😴 Sleep")
        if data["sleep"] and data["sleep_period"]:
            sleep = data["sleep"]
            sp = data["sleep_period"]
            prev = data["previous_day"].get("sleep_score")
            trend = self._format_trend(sleep["score"], prev)

            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| **Score** | {sleep['score']}/100 {trend} |")
            lines.append(f"| Duration | {sp['total_hours']}h |")
            lines.append(f"| Deep Sleep | {sp['deep_sleep_mins']} min |")
            lines.append(f"| REM Sleep | {sp['rem_sleep_mins']} min |")
            lines.append(f"| Light Sleep | {sp['light_sleep_mins']} min |")
            lines.append(f"| Efficiency | {sp['efficiency']}% |")
            if sp["avg_hrv"]:
                lines.append(f"| Avg HRV | {sp['avg_hrv']} ms |")
            if sp["lowest_hr"]:
                lines.append(f"| Lowest HR | {sp['lowest_hr']} bpm |")
        else:
            lines.append(f"No sleep data available.")
        lines.append(f"")

        # Activity Section
        lines.append(f"## 🏃 Activity")
        if data["activity"]:
            act = data["activity"]
            prev = data["previous_day"].get("activity_score")
            trend = self._format_trend(act["score"], prev)

            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| **Score** | {act['score']}/100 {trend} |")
            lines.append(f"| Steps | {act['steps']:,} |")
            lines.append(f"| Total Calories | {act['calories']:,} |")
            lines.append(f"| Active Calories | {act['active_calories']:,} |")
            high_mins = (act["high_activity_time"] or 0) // 60
            med_mins = (act["medium_activity_time"] or 0) // 60
            low_mins = (act["low_activity_time"] or 0) // 60
            lines.append(f"| High Activity | {high_mins} min |")
            lines.append(f"| Medium Activity | {med_mins} min |")
            lines.append(f"| Low Activity | {low_mins} min |")
        else:
            lines.append(f"No activity data available.")
        lines.append(f"")

        # Readiness Section
        lines.append(f"## 💪 Readiness")
        if data["readiness"]:
            r = data["readiness"]
            prev = data["previous_day"].get("readiness_score")
            trend = self._format_trend(r["score"], prev)

            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| **Score** | {r['score']}/100 {trend} |")
            lines.append(f"| Resting HR | {r['resting_hr']} bpm |")
            if r["hrv_balance"]:
                lines.append(f"| HRV Balance | {r['hrv_balance']} |")
            if r["recovery_index"]:
                lines.append(f"| Recovery Index | {r['recovery_index']} |")
        else:
            lines.append(f"No readiness data available.")
        lines.append(f"")

        # Stress Section (if available)
        if data["stress"]:
            lines.append(f"## 🧘 Stress & Recovery")
            lines.append(f"")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            if data["stress"]["day_summary"]:
                lines.append(f"| Day Summary | {data['stress']['day_summary']} |")
            if data["stress"]["stress_high"]:
                lines.append(f"| High Stress | {data['stress']['stress_high']} min |")
            if data["stress"]["recovery_high"]:
                lines.append(f"| High Recovery | {data['stress']['recovery_high']} min |")
            lines.append(f"")

        # Footer
        lines.append(f"---")
        lines.append(f"*Generated automatically by oura-collector*")

        return "\n".join(lines)

    def post_to_discord(self, payload: Dict[str, Any]) -> bool:
        """Post the summary to Discord.

        Args:
            payload: Discord webhook payload

        Returns:
            True if successful
        """
        if not self.discord_webhook_url:
            logger.warning("Discord webhook URL not configured, skipping Discord post")
            return False

        try:
            response = requests.post(
                self.discord_webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Daily summary posted to Discord")
            return True
        except Exception as e:
            logger.error(f"Failed to post to Discord: {e}")
            return False

    def save_to_vault(self, markdown: str, target_date: date) -> bool:
        """Save the markdown to Obsidian vault.

        Args:
            markdown: Markdown content
            target_date: Date for the filename

        Returns:
            True if successful
        """
        try:
            # Create directory if it doesn't exist
            vault_dir = Path(self.health_notes_path)
            if not vault_dir.exists():
                logger.warning(f"Vault path does not exist: {vault_dir}")
                return False

            # Create filename: YYYY-MM-DD-health.md
            filename = f"{target_date.strftime('%Y-%m-%d')}-health.md"
            filepath = vault_dir / filename

            # Write the file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            logger.info(f"Daily summary saved to vault: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to vault: {e}")
            return False

    def generate_and_publish(self, target_date: Optional[date] = None) -> Dict[str, bool]:
        """Generate and publish the daily summary.

        Args:
            target_date: Date to generate report for (defaults to yesterday)

        Returns:
            Dictionary with success status for each destination
        """
        if target_date is None:
            # Default to yesterday (today's data may not be complete)
            target_date = date.today() - timedelta(days=1)

        logger.info(f"Generating daily health report for {target_date}")

        results = {
            "discord": False,
            "vault": False,
        }

        # Fetch data
        data = self.get_daily_data(target_date)

        # Check if we have any data
        if not data["sleep"] and not data["activity"] and not data["readiness"]:
            logger.warning(f"No health data available for {target_date}")
            return results

        # Post to Discord
        discord_payload = self.format_discord_message(data)
        results["discord"] = self.post_to_discord(discord_payload)

        # Save to vault
        markdown = self.format_markdown(data)
        results["vault"] = self.save_to_vault(markdown, target_date)

        return results

    def get_weekly_data(self, end_date: date) -> Dict[str, Any]:
        """Fetch aggregated health data for the past week.

        Args:
            end_date: Last day of the week to analyze

        Returns:
            Dictionary with weekly aggregated metrics
        """
        start_date = end_date - timedelta(days=6)  # 7 days total

        data = {
            "start_date": start_date,
            "end_date": end_date,
            "days_with_data": 0,
            "sleep": {"scores": [], "durations": [], "deep_mins": [], "rem_mins": []},
            "activity": {"scores": [], "steps": [], "active_calories": []},
            "readiness": {"scores": [], "resting_hrs": [], "hrvs": []},
        }

        try:
            with self.storage.get_session() as session:
                # Sleep data
                sleep_records = session.query(DailySleep).filter(
                    DailySleep.date >= start_date,
                    DailySleep.date <= end_date
                ).all()
                for s in sleep_records:
                    if s.sleep_score:
                        data["sleep"]["scores"].append(s.sleep_score)

                # Sleep period details
                sleep_periods = session.query(SleepPeriod).filter(
                    func.date(SleepPeriod.bedtime_start) >= start_date - timedelta(days=1),
                    func.date(SleepPeriod.bedtime_start) <= end_date
                ).all()
                for sp in sleep_periods:
                    if sp.total_sleep_duration:
                        data["sleep"]["durations"].append(sp.total_sleep_duration / 3600)
                    if sp.deep_sleep_duration:
                        data["sleep"]["deep_mins"].append(sp.deep_sleep_duration / 60)
                    if sp.rem_sleep_duration:
                        data["sleep"]["rem_mins"].append(sp.rem_sleep_duration / 60)
                    if sp.average_hrv:
                        data["readiness"]["hrvs"].append(sp.average_hrv)

                # Activity data
                activity_records = session.query(Activity).filter(
                    Activity.date >= start_date,
                    Activity.date <= end_date
                ).all()
                for a in activity_records:
                    if a.activity_score:
                        data["activity"]["scores"].append(a.activity_score)
                    if a.steps:
                        data["activity"]["steps"].append(a.steps)
                    if a.calories_active:
                        data["activity"]["active_calories"].append(a.calories_active)

                # Readiness data
                readiness_records = session.query(Readiness).filter(
                    Readiness.date >= start_date,
                    Readiness.date <= end_date
                ).all()
                for r in readiness_records:
                    if r.readiness_score:
                        data["readiness"]["scores"].append(r.readiness_score)
                    if r.resting_heart_rate:
                        data["readiness"]["resting_hrs"].append(r.resting_heart_rate)

                data["days_with_data"] = len(sleep_records)

        except Exception as e:
            logger.error(f"Error fetching weekly data: {e}")

        return data

    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate mean, min, max for a list of values."""
        if not values:
            return {"avg": None, "min": None, "max": None}
        return {
            "avg": round(sum(values) / len(values), 1),
            "min": round(min(values), 1),
            "max": round(max(values), 1),
        }

    def format_weekly_discord(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format weekly data as a Discord embed."""
        start_str = data["start_date"].strftime("%b %d")
        end_str = data["end_date"].strftime("%b %d, %Y")

        lines = []

        # Sleep section
        sleep_stats = self._calculate_stats(data["sleep"]["scores"])
        duration_stats = self._calculate_stats(data["sleep"]["durations"])
        if sleep_stats["avg"]:
            emoji = self._score_emoji(int(sleep_stats["avg"]))
            lines.append(f"{emoji} **Sleep:** avg {sleep_stats['avg']}/100 (range: {sleep_stats['min']}-{sleep_stats['max']})")
            if duration_stats["avg"]:
                lines.append(f"   └ Avg duration: {duration_stats['avg']}h")

        # Activity section
        activity_stats = self._calculate_stats(data["activity"]["scores"])
        steps_stats = self._calculate_stats(data["activity"]["steps"])
        if activity_stats["avg"]:
            emoji = self._score_emoji(int(activity_stats["avg"]))
            lines.append(f"{emoji} **Activity:** avg {activity_stats['avg']}/100 (range: {activity_stats['min']}-{activity_stats['max']})")
            if steps_stats["avg"]:
                lines.append(f"   └ Avg steps: {int(steps_stats['avg']):,}/day | Total: {sum(data['activity']['steps']):,}")

        # Readiness section
        readiness_stats = self._calculate_stats(data["readiness"]["scores"])
        hrv_stats = self._calculate_stats(data["readiness"]["hrvs"])
        if readiness_stats["avg"]:
            emoji = self._score_emoji(int(readiness_stats["avg"]))
            lines.append(f"{emoji} **Readiness:** avg {readiness_stats['avg']}/100 (range: {readiness_stats['min']}-{readiness_stats['max']})")
            if hrv_stats["avg"]:
                lines.append(f"   └ Avg HRV: {hrv_stats['avg']}ms (range: {hrv_stats['min']}-{hrv_stats['max']})")

        description = "\n".join(lines) if lines else "No data available for this week."

        # Determine color based on average of averages
        scores = []
        if sleep_stats["avg"]:
            scores.append(sleep_stats["avg"])
        if activity_stats["avg"]:
            scores.append(activity_stats["avg"])
        if readiness_stats["avg"]:
            scores.append(readiness_stats["avg"])

        avg_score = sum(scores) / len(scores) if scores else 0
        if avg_score >= 85:
            color = 5763719
        elif avg_score >= 70:
            color = 16776960
        elif avg_score >= 50:
            color = 16744448
        else:
            color = 15158332

        return {
            "embeds": [{
                "title": f"📈 Weekly Health Summary",
                "description": description,
                "color": color,
                "footer": {"text": f"{start_str} - {end_str} • oura-collector"},
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }]
        }

    def format_weekly_markdown(self, data: Dict[str, Any]) -> str:
        """Format weekly data as Obsidian markdown."""
        start_str = data["start_date"].strftime("%Y-%m-%d")
        end_str = data["end_date"].strftime("%Y-%m-%d")
        week_num = data["end_date"].isocalendar()[1]

        lines = [
            "---",
            f"date: {end_str}",
            f"week: {week_num}",
            "type: health-weekly",
            "tags: [health, oura, weekly-summary]",
        ]

        # Add averages to frontmatter
        sleep_stats = self._calculate_stats(data["sleep"]["scores"])
        activity_stats = self._calculate_stats(data["activity"]["scores"])
        readiness_stats = self._calculate_stats(data["readiness"]["scores"])

        if sleep_stats["avg"]:
            lines.append(f"avg_sleep_score: {sleep_stats['avg']}")
        if activity_stats["avg"]:
            lines.append(f"avg_activity_score: {activity_stats['avg']}")
        if readiness_stats["avg"]:
            lines.append(f"avg_readiness_score: {readiness_stats['avg']}")

        lines.append("---")
        lines.append("")
        lines.append(f"# Weekly Health Summary - Week {week_num}")
        lines.append(f"*{data['start_date'].strftime('%B %d')} - {data['end_date'].strftime('%B %d, %Y')}*")
        lines.append("")

        # Sleep Section
        lines.append("## 😴 Sleep")
        if sleep_stats["avg"]:
            duration_stats = self._calculate_stats(data["sleep"]["durations"])
            deep_stats = self._calculate_stats(data["sleep"]["deep_mins"])
            rem_stats = self._calculate_stats(data["sleep"]["rem_mins"])

            lines.append("")
            lines.append("| Metric | Average | Range |")
            lines.append("|--------|---------|-------|")
            lines.append(f"| **Score** | {sleep_stats['avg']}/100 | {sleep_stats['min']}-{sleep_stats['max']} |")
            if duration_stats["avg"]:
                lines.append(f"| Duration | {duration_stats['avg']}h | {duration_stats['min']}-{duration_stats['max']}h |")
            if deep_stats["avg"]:
                lines.append(f"| Deep Sleep | {int(deep_stats['avg'])}min | {int(deep_stats['min'])}-{int(deep_stats['max'])}min |")
            if rem_stats["avg"]:
                lines.append(f"| REM Sleep | {int(rem_stats['avg'])}min | {int(rem_stats['min'])}-{int(rem_stats['max'])}min |")
        else:
            lines.append("No sleep data available.")
        lines.append("")

        # Activity Section
        lines.append("## 🏃 Activity")
        if activity_stats["avg"]:
            steps_stats = self._calculate_stats(data["activity"]["steps"])
            cal_stats = self._calculate_stats(data["activity"]["active_calories"])

            lines.append("")
            lines.append("| Metric | Average | Total/Range |")
            lines.append("|--------|---------|-------------|")
            lines.append(f"| **Score** | {activity_stats['avg']}/100 | {activity_stats['min']}-{activity_stats['max']} |")
            if steps_stats["avg"]:
                total_steps = sum(data["activity"]["steps"])
                lines.append(f"| Steps | {int(steps_stats['avg']):,}/day | {total_steps:,} total |")
            if cal_stats["avg"]:
                total_cals = sum(data["activity"]["active_calories"])
                lines.append(f"| Active Cal | {int(cal_stats['avg']):,}/day | {total_cals:,} total |")
        else:
            lines.append("No activity data available.")
        lines.append("")

        # Readiness Section
        lines.append("## 💪 Readiness")
        if readiness_stats["avg"]:
            hr_stats = self._calculate_stats(data["readiness"]["resting_hrs"])
            hrv_stats = self._calculate_stats(data["readiness"]["hrvs"])

            lines.append("")
            lines.append("| Metric | Average | Range |")
            lines.append("|--------|---------|-------|")
            lines.append(f"| **Score** | {readiness_stats['avg']}/100 | {readiness_stats['min']}-{readiness_stats['max']} |")
            if hr_stats["avg"]:
                lines.append(f"| Resting HR | {int(hr_stats['avg'])} bpm | {int(hr_stats['min'])}-{int(hr_stats['max'])} bpm |")
            if hrv_stats["avg"]:
                lines.append(f"| HRV | {hrv_stats['avg']}ms | {hrv_stats['min']}-{hrv_stats['max']}ms |")
        else:
            lines.append("No readiness data available.")
        lines.append("")

        lines.append("---")
        lines.append("*Generated automatically by oura-collector*")

        return "\n".join(lines)

    def generate_weekly_report(self, end_date: Optional[date] = None) -> Dict[str, bool]:
        """Generate and publish the weekly summary.

        Args:
            end_date: Last day of the week (defaults to yesterday)

        Returns:
            Dictionary with success status for each destination
        """
        if end_date is None:
            end_date = date.today() - timedelta(days=1)

        logger.info(f"Generating weekly health report ending {end_date}")

        results = {"discord": False, "vault": False}

        data = self.get_weekly_data(end_date)

        if data["days_with_data"] == 0:
            logger.warning(f"No health data available for the week ending {end_date}")
            return results

        # Post to Discord
        discord_payload = self.format_weekly_discord(data)
        results["discord"] = self.post_to_discord(discord_payload)

        # Save to vault
        markdown = self.format_weekly_markdown(data)
        week_num = end_date.isocalendar()[1]
        try:
            vault_dir = Path(self.health_notes_path)
            if vault_dir.exists():
                filename = f"{end_date.strftime('%Y')}-W{week_num:02d}-weekly.md"
                filepath = vault_dir / filename
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(markdown)
                logger.info(f"Weekly summary saved to vault: {filepath}")
                results["vault"] = True
        except Exception as e:
            logger.error(f"Failed to save weekly report to vault: {e}")

        return results
