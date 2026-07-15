"""Daily Health Reporter - Posts daily summaries to Discord and Obsidian vault."""

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
from urllib.parse import quote
from sqlalchemy import func

from database_models import (
    Activity, DailySleep, Readiness, SleepPeriod,
    Stress, DailySummary, SpO2, Resilience, CardiovascularAge
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
        # oura-agent (Dr. Oura) daily-briefing endpoint, in-cluster by default
        self.dr_agent_url = os.getenv(
            "DR_AGENT_URL",
            "http://oura-agent.oura-agent.svc.cluster.local:8080/daily-summary",
        )
        # Shared bearer token for the authenticated /daily-summary endpoint
        self.dr_agent_token = os.getenv("DR_AGENT_TOKEN", "")
        # Obsidian Local REST API (fronted by obsidian-api.landryzetam.net). When set,
        # the daily report is PUT into the vault via the API instead of a mounted path.
        self.obsidian_api_url = os.getenv("OBSIDIAN_API_URL", "").rstrip("/")
        self.obsidian_api_key = os.getenv("OBSIDIAN_API_KEY", "")
        self.obsidian_verify_tls = os.getenv("OBSIDIAN_VERIFY_TLS", "false").lower() == "true"
        # If a pinned CA cert path is provided, verify against it (real MITM protection
        # for the self-signed endpoint). Takes precedence over the boolean flag.
        self.obsidian_ca_cert = os.getenv("OBSIDIAN_CA_CERT", "")
        # Vault path the note is written to (folder inside the vault)
        self.obsidian_vault_folder = os.getenv("OBSIDIAN_VAULT_FOLDER", "Health/Oura Daily")

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
            "spo2": None,
            "resilience": None,
            "cardiovascular": None,
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
                            "restfulness_score": getattr(sleep, 'score_restfulness', None),
                            "latency_score": getattr(sleep, 'score_latency', None),
                            "timing_score": getattr(sleep, 'score_timing', None),
                            "total_sleep_score": getattr(sleep, 'score_total_sleep', None),
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
                            "distance_km": getattr(activity, 'distance_km', None),
                            "calories": getattr(activity, 'calories_total', None),
                            "active_calories": getattr(activity, 'calories_active', None),
                            "target_calories": getattr(activity, 'calories_target', None),
                            "sedentary_time": (getattr(activity, 'sedentary_minutes', 0) or 0) * 60,
                            "high_activity_time": (getattr(activity, 'high_activity_minutes', 0) or 0) * 60,
                            "medium_activity_time": (getattr(activity, 'medium_activity_minutes', 0) or 0) * 60,
                            "low_activity_time": (getattr(activity, 'low_activity_minutes', 0) or 0) * 60,
                            "resting_time_min": getattr(activity, 'resting_time_minutes', None),
                            "avg_met": getattr(activity, 'average_met', None),
                            "met_minutes": getattr(activity, 'met_minutes', None),
                            "target_meters": getattr(activity, 'target_meters', None),
                            "meters_to_target": getattr(activity, 'meters_to_target', None),
                            "inactivity_alerts": getattr(activity, 'inactivity_alerts', None),
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
                            "recovery_index": getattr(readiness, 'recovery_index', None),
                            "temp_deviation": getattr(readiness, 'temperature_deviation', None),
                            "temp_trend_deviation": getattr(readiness, 'temperature_trend_deviation', None),
                            "score_body_temp": getattr(readiness, 'score_body_temperature', None),
                            "score_hrv_balance": getattr(readiness, 'score_hrv_balance', None),
                            "score_resting_hr": getattr(readiness, 'score_resting_heart_rate', None),
                            "score_recovery_index": getattr(readiness, 'score_recovery_index', None),
                            "score_sleep_balance": getattr(readiness, 'score_sleep_balance', None),
                            "score_activity_balance": getattr(readiness, 'score_activity_balance', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching readiness data: {e}")

                # Sleep period details (for duration, HRV, respiratory)
                try:
                    sleep_period = session.query(SleepPeriod).filter(
                        func.date(SleepPeriod.bedtime_start) == target_date - timedelta(days=1)
                    ).first()
                    if sleep_period:
                        data["sleep_period"] = {
                            "total_hours": round(sleep_period.total_sleep_hours or 0, 1),
                            "time_in_bed_hours": round(sleep_period.time_in_bed_hours or 0, 1),
                            "deep_sleep_mins": int((sleep_period.deep_hours or 0) * 60),
                            "rem_sleep_mins": int((sleep_period.rem_hours or 0) * 60),
                            "light_sleep_mins": int((sleep_period.light_hours or 0) * 60),
                            "efficiency": sleep_period.efficiency_percent,
                            "latency_min": sleep_period.latency_minutes,
                            "restless_periods": sleep_period.restless_periods,
                            "avg_hrv": sleep_period.hrv_avg,
                            "max_hrv": getattr(sleep_period, 'hrv_max', None),
                            "min_hrv": getattr(sleep_period, 'hrv_min', None),
                            "respiratory_rate": getattr(sleep_period, 'respiratory_rate', None),
                            "avg_hr": getattr(sleep_period, 'heart_rate_avg', None),
                            # lowest_heart_rate is often unmapped/NULL; heart_rate_min is the
                            # real overnight resting-HR bpm. Fall back between them.
                            "lowest_hr": sleep_period.lowest_heart_rate or sleep_period.heart_rate_min,
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
                            "stress_high_min": getattr(stress, 'stress_high_minutes', None),
                            "recovery_high_min": getattr(stress, 'recovery_high_minutes', None),
                            "stress_recovery_ratio": getattr(stress, 'stress_recovery_ratio', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching stress data: {e}")

                # SpO2 (blood oxygen)
                try:
                    spo2 = session.query(SpO2).filter(SpO2.date == target_date).first()
                    if spo2:
                        data["spo2"] = {
                            "avg_pct": getattr(spo2, 'spo2_percentage_avg', None),
                            "breathing_disturbance_index": getattr(spo2, 'breathing_disturbance_index', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching spo2 data: {e}")

                # Resilience
                try:
                    resilience = session.query(Resilience).filter(Resilience.date == target_date).first()
                    if resilience:
                        data["resilience"] = {
                            "level": getattr(resilience, 'resilience_level', None),
                            "sleep_recovery": getattr(resilience, 'sleep_recovery', None),
                            "daytime_recovery": getattr(resilience, 'daytime_recovery', None),
                            "stress": getattr(resilience, 'stress', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching resilience data: {e}")

                # Cardiovascular age
                try:
                    cardio = session.query(CardiovascularAge).filter(CardiovascularAge.date == target_date).first()
                    if cardio:
                        data["cardiovascular"] = {
                            "cardiovascular_age": getattr(cardio, 'cardiovascular_age', None),
                        }
                except Exception as e:
                    logger.warning(f"Error fetching cardiovascular data: {e}")

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

    @staticmethod
    def _fmt(value: Any, suffix: str = "", nd: Optional[int] = None) -> str:
        """Render a value or 'n/a' if missing, with optional rounding + suffix."""
        if value is None:
            return "n/a"
        if nd is not None and isinstance(value, (int, float)):
            value = round(value, nd)
        return f"{value}{suffix}"

    def format_discord_message(
        self, data: Dict[str, Any], doctor_briefing: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format data as one comprehensive Discord embed.

        Dr. Oura's clinical briefing leads the description; every collected metric
        is laid out in labelled fields below it.

        Args:
            data: Enriched health data dictionary
            doctor_briefing: The Dr. Oura narrative (from the oura-agent hand-off)

        Returns:
            Discord webhook payload with a single rich embed
        """
        target_date = data["date"]
        date_str = target_date.strftime("%B %d, %Y")
        f = self._fmt

        sp = data.get("sleep_period") or {}
        sl = data.get("sleep") or {}
        act = data.get("activity") or {}
        rd = data.get("readiness") or {}
        st = data.get("stress") or {}
        spo2 = data.get("spo2") or {}
        res = data.get("resilience") or {}
        cardio = data.get("cardiovascular") or {}
        prev = data.get("previous_day") or {}

        # One-line score header + Dr. Oura briefing as the description
        header_bits = []
        if sl.get("score") is not None:
            header_bits.append(f"{self._score_emoji(sl['score'])} Sleep {sl['score']}")
        if act.get("score") is not None:
            header_bits.append(f"{self._score_emoji(act['score'])} Activity {act['score']}")
        if rd.get("score") is not None:
            header_bits.append(f"{self._score_emoji(rd['score'])} Readiness {rd['score']}")
        header = " · ".join(header_bits) if header_bits else "No scores available"

        if doctor_briefing:
            description = f"**{header}**\n\n🩺 **Dr. Oura's Briefing**\n{doctor_briefing.strip()}"
        else:
            description = f"**{header}**\n\n_(Dr. Oura's briefing unavailable — showing metrics only.)_"
        description = description[:4096]  # Discord embed description limit

        fields = []

        # 🌙 Sleep
        if sl or sp:
            trend = self._format_trend(sl.get("score"), prev.get("sleep_score"))
            val = (
                f"Score **{f(sl.get('score'))}/100** {trend}\n"
                f"Duration {f(sp.get('total_hours'),'h')} (in bed {f(sp.get('time_in_bed_hours'),'h')})\n"
                f"Deep {f(sp.get('deep_sleep_mins'),'m')} · REM {f(sp.get('rem_sleep_mins'),'m')} · "
                f"Light {f(sp.get('light_sleep_mins'),'m')}\n"
                f"Efficiency {f(sp.get('efficiency'),'%')} · Latency {f(sp.get('latency_min'),'m')} · "
                f"Restless {f(sp.get('restless_periods'))}"
            )
            fields.append({"name": "🌙 Sleep", "value": val[:1024], "inline": False})

        # 🏃 Activity
        if act:
            trend = self._format_trend(act.get("score"), prev.get("activity_score"))
            steps = act.get("steps")
            steps_str = f"{steps:,}" if isinstance(steps, int) else "n/a"
            high_m = (act.get("high_activity_time") or 0) // 60
            med_m = (act.get("medium_activity_time") or 0) // 60
            val = (
                f"Score **{f(act.get('score'))}/100** {trend}\n"
                f"Steps {steps_str} · Distance {f(act.get('distance_km'),'km',2)}\n"
                f"Calories {f(act.get('calories'))} total / {f(act.get('active_calories'))} active "
                f"(target {f(act.get('target_calories'))})\n"
                f"High {high_m}m · Medium {med_m}m · Avg MET {f(act.get('avg_met'),'',2)}"
            )
            fields.append({"name": "🏃 Activity", "value": val[:1024], "inline": False})

        # 💚 Readiness & vitals
        if rd or sp:
            trend = self._format_trend(rd.get("score"), prev.get("readiness_score"))
            rhr = rd.get("resting_hr")
            if rhr is None:
                rhr = sp.get("lowest_hr")
            val = (
                f"Score **{f(rd.get('score'))}/100** {trend}\n"
                f"Resting HR {f(rhr,' bpm')} · HRV {f(sp.get('avg_hrv'),' ms')} "
                f"(min {f(sp.get('min_hrv'))} / max {f(sp.get('max_hrv'))})\n"
                f"Respiratory {f(sp.get('respiratory_rate'),'/min',1)} · "
                f"Temp dev {f(rd.get('temp_deviation'),'°C',2)}\n"
                # Readiness contributor sub-scores (0-100), consistently labelled — the
                # raw recovery_index / hrv_balance fields are frequently null, so we show
                # the populated contributor scores instead.
                f"Contributors → Recovery {f(rd.get('score_recovery_index'),'/100')} · "
                f"HRV bal {f(rd.get('score_hrv_balance'),'/100')} · "
                f"Sleep bal {f(rd.get('score_sleep_balance'),'/100')} · "
                f"Temp {f(rd.get('score_body_temp'),'/100')}"
            )
            fields.append({"name": "💚 Readiness & Vitals", "value": val[:1024], "inline": False})

        # 🫀 Cardiovascular & SpO2
        if cardio or spo2:
            val = (
                f"Cardiovascular age {f(cardio.get('cardiovascular_age'),' yrs')}\n"
                f"SpO₂ {f(spo2.get('avg_pct'),'%',1)} · "
                f"Breathing disturbance {f(spo2.get('breathing_disturbance_index'),'',2)}"
            )
            fields.append({"name": "🫀 Cardiovascular & SpO₂", "value": val[:1024], "inline": False})

        # 🧘 Stress & Resilience
        if st or res:
            val = (
                f"Stress: **{f(st.get('day_summary'))}** "
                f"(high {f(st.get('stress_high_min'),'m')}, recovery {f(st.get('recovery_high_min'),'m')})\n"
                f"Resilience: **{f(res.get('level'))}** · "
                f"sleep-recovery {f(res.get('sleep_recovery'),'',1)} · "
                f"daytime {f(res.get('daytime_recovery'),'',1)}"
            )
            fields.append({"name": "🧘 Stress & Resilience", "value": val[:1024], "inline": False})

        # Color by average of the three primary scores
        scores = [s for s in (sl.get("score"), act.get("score"), rd.get("score")) if s is not None]
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
                "title": f"📊 Daily Health Briefing — {date_str}",
                "description": description,
                "color": color,
                "fields": fields,
                "footer": {"text": "Dr. Oura • oura-collector → oura-agent"},
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }]
        }

    def format_markdown(self, data: Dict[str, Any], doctor_briefing: Optional[str] = None) -> str:
        """Format data as Obsidian markdown.

        Args:
            data: Health data dictionary
            doctor_briefing: The Dr. Oura clinical briefing (included as a section)

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

        # Dr. Oura's clinical briefing (the interpretive summary) leads the note
        if doctor_briefing:
            lines.append(f"## 🩺 Dr. Oura's Briefing")
            lines.append(f"")
            lines.append(doctor_briefing.strip())
            lines.append(f"")
            lines.append(f"---")
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
            if data["stress"].get("stress_high_min"):
                lines.append(f"| High Stress | {data['stress']['stress_high_min']} min |")
            if data["stress"].get("recovery_high_min"):
                lines.append(f"| High Recovery | {data['stress']['recovery_high_min']} min |")
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

    def _save_to_obsidian_api(self, markdown: str, target_date: date) -> bool:
        """PUT the report into the Obsidian vault via the Local REST API.

        Uses obsidian-api.landryzetam.net (creds from the obsidian/api secret).
        Non-fatal: returns False on any failure so the Discord post still stands.
        """
        vault_path = f"{self.obsidian_vault_folder}/oura-{target_date.strftime('%Y-%m-%d')}.md"
        # The REST API PUTs to /vault/<url-encoded path>
        url = f"{self.obsidian_api_url}/vault/{quote(vault_path)}"
        try:
            resp = requests.put(
                url,
                data=markdown.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.obsidian_api_key}",
                    "Content-Type": "text/markdown",
                },
                verify=(self.obsidian_ca_cert if self.obsidian_ca_cert else self.obsidian_verify_tls),
                timeout=20,
            )
            resp.raise_for_status()
            logger.info(f"Daily report saved to Obsidian vault: {vault_path}")
            return True
        except Exception as e:
            logger.warning(f"Obsidian API save failed ({e}); vault copy skipped")
            return False

    def save_to_vault(self, markdown: str, target_date: date) -> bool:
        """Save the markdown to the Obsidian vault.

        Prefers the Obsidian Local REST API (works from the cluster); falls back
        to a mounted filesystem path if the API isn't configured.

        Args:
            markdown: Markdown content
            target_date: Date for the filename

        Returns:
            True if successful
        """
        # Preferred path: Obsidian Local REST API
        if self.obsidian_api_url and self.obsidian_api_key:
            return self._save_to_obsidian_api(markdown, target_date)

        # Fallback: mounted filesystem vault
        try:
            vault_dir = Path(self.health_notes_path)
            if not vault_dir.exists():
                logger.warning(f"Vault path does not exist: {vault_dir}")
                return False

            filename = f"{target_date.strftime('%Y-%m-%d')}-health.md"
            filepath = vault_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            logger.info(f"Daily summary saved to vault: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to vault: {e}")
            return False

    def _get_doctor_briefing(self, data: Dict[str, Any], target_date: date) -> Optional[str]:
        """Hand off the day's metrics to the oura-agent (Dr. Oura) for a briefing.

        Non-fatal: if the agent is unreachable or errors, returns None and the
        report still posts with the metric fields only.

        Args:
            data: Enriched health data dictionary
            target_date: The report date

        Returns:
            The Dr. Oura briefing text, or None on any failure
        """
        # Build a JSON-serializable metrics payload (drop the date object)
        metrics = {k: v for k, v in data.items() if k not in ("date", "previous_day") and v}
        metrics["previous_day"] = data.get("previous_day")
        try:
            headers = {}
            if self.dr_agent_token:
                headers["Authorization"] = f"Bearer {self.dr_agent_token}"
            resp = requests.post(
                self.dr_agent_url,
                json={"date": target_date.isoformat(), "metrics": metrics},
                headers=headers,
                timeout=90,  # specialists + synthesis is several LLM calls
            )
            resp.raise_for_status()
            summary = resp.json().get("summary")
            if summary:
                logger.info("Received Dr. Oura briefing from oura-agent")
                return summary
            logger.warning("oura-agent returned no summary")
        except Exception as e:
            logger.warning(f"Dr. Oura hand-off failed ({e}); posting metrics without briefing")
        return None

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

        # Hand off to the Dr. Oura agent for the clinical briefing
        doctor_briefing = self._get_doctor_briefing(data, target_date)

        # Post to Discord
        discord_payload = self.format_discord_message(data, doctor_briefing=doctor_briefing)
        results["discord"] = self.post_to_discord(discord_payload)

        # Save to vault (same briefing as the Discord post)
        markdown = self.format_markdown(data, doctor_briefing=doctor_briefing)
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
                    if sp.total_sleep_hours:
                        data["sleep"]["durations"].append(sp.total_sleep_hours)
                    if sp.deep_hours:
                        data["sleep"]["deep_mins"].append(sp.deep_hours * 60)
                    if sp.rem_hours:
                        data["sleep"]["rem_mins"].append(sp.rem_hours * 60)
                    if sp.hrv_avg:
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
