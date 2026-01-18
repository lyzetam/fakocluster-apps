"""Data quality validation for Oura Health Agent.

Every tool MUST validate data quality before returning results to prevent
the agent from confidently reporting stale or incomplete data.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of data quality validation.

    Attributes:
        valid: True if data exists and can be used
        stale: True if data is older than freshness threshold
        days_old: Age of most recent record in days
        latest_date: Date string of most recent record
        warning: Human-readable warning message (if any)
    """

    valid: bool
    stale: bool
    days_old: int | None
    latest_date: str | None
    warning: str | None


class DataQualityValidator:
    """Validate data freshness and completeness before tools return results.

    This validator ensures the agent acknowledges data staleness and doesn't
    present old data as current. Every health data tool should use this.

    Usage:
        validator = DataQualityValidator()
        result = validator.validate("sleep_periods", data)
        if not result.valid:
            return result.warning
        if result.stale:
            response = f"⚠️ {result.warning}\\n\\n{response}"
    """

    # Days before data is considered stale (critical tables need fresh data)
    FRESHNESS_THRESHOLDS = {
        "sleep_periods": 2,  # Critical - detailed sleep stages
        "oura_sleep_periods": 2,
        "activity": 2,  # Critical - detailed activity metrics
        "oura_activity": 2,
        "daily_sleep": 1,  # Score tables should be daily
        "oura_daily_sleep": 1,
        "readiness": 1,
        "oura_readiness": 1,
        "daily_summaries": 1,
        "workouts": 7,  # Workouts may not happen daily
        "oura_workouts": 7,
        "sessions": 7,  # Meditation sessions sporadic
        "oura_sessions": 7,
        "stress": 2,
        "oura_stress": 2,
        "resilience": 3,
        "oura_resilience": 3,
        "spo2": 2,
        "oura_spo2": 2,
        "vo2_max": 30,  # Updated less frequently
        "oura_vo2_max": 30,
        "cardiovascular_age": 90,  # Updated rarely
        "oura_cardiovascular_age": 90,
    }

    # Fields that commonly contain dates
    DATE_FIELDS = ["date", "day", "timestamp", "bedtime_start", "start_datetime"]

    def validate(
        self,
        table: str,
        data: list[dict[str, Any]] | dict[str, Any] | None,
    ) -> ValidationResult:
        """Validate data quality and return metadata.

        Args:
            table: Name of the data table/source
            data: Query results (list of dicts, single dict, or None)

        Returns:
            ValidationResult with quality metadata
        """
        # Normalize data to list
        if data is None:
            data_list = []
        elif isinstance(data, dict):
            data_list = [data]
        else:
            data_list = list(data)

        # Handle empty data
        if not data_list:
            table_name = table.replace("_", " ").replace("oura ", "")
            return ValidationResult(
                valid=False,
                stale=True,
                days_old=None,
                latest_date=None,
                warning=f"No {table_name} data found in database.",
            )

        # Find most recent date in data
        latest = self._find_latest_date(data_list)

        if latest is None:
            return ValidationResult(
                valid=True,
                stale=False,
                days_old=0,
                latest_date="unknown",
                warning=None,
            )

        # Calculate staleness
        days_old = (date.today() - latest).days
        threshold = self.FRESHNESS_THRESHOLDS.get(table, 3)

        if days_old > threshold:
            return ValidationResult(
                valid=True,
                stale=True,
                days_old=days_old,
                latest_date=str(latest),
                warning=(
                    f"⚠️ Data is {days_old} days old (last: {latest}). "
                    "Your Oura ring may not be syncing properly."
                ),
            )

        return ValidationResult(
            valid=True,
            stale=False,
            days_old=days_old,
            latest_date=str(latest),
            warning=None,
        )

    def _find_latest_date(self, data: list[dict[str, Any]]) -> date | None:
        """Find the most recent date in the data.

        Args:
            data: List of data records

        Returns:
            Most recent date found, or None
        """
        latest = None

        for row in data:
            for field in self.DATE_FIELDS:
                if field in row and row[field]:
                    val = row[field]

                    # Parse various date formats
                    try:
                        if isinstance(val, str):
                            # Handle ISO format with optional time
                            val = date.fromisoformat(val[:10])
                        elif isinstance(val, datetime):
                            val = val.date()
                        elif hasattr(val, "date"):
                            val = val.date()

                        if latest is None or val > latest:
                            latest = val
                        break
                    except (ValueError, TypeError):
                        continue

        return latest

    def validate_multiple(
        self,
        tables_data: dict[str, list[dict[str, Any]] | None],
    ) -> dict[str, ValidationResult]:
        """Validate multiple tables at once.

        Args:
            tables_data: Dict mapping table names to their data

        Returns:
            Dict mapping table names to ValidationResults
        """
        return {table: self.validate(table, data) for table, data in tables_data.items()}

    def get_freshness_summary(
        self,
        tables_data: dict[str, list[dict[str, Any]] | None],
    ) -> str:
        """Get a human-readable freshness summary for multiple tables.

        Args:
            tables_data: Dict mapping table names to their data

        Returns:
            Formatted freshness summary string
        """
        results = self.validate_multiple(tables_data)

        lines = ["Data Freshness Status:"]
        for table, result in results.items():
            table_name = table.replace("oura_", "").replace("_", " ").title()
            if not result.valid:
                lines.append(f"❌ {table_name}: No data")
            elif result.stale:
                lines.append(f"⚠️ {table_name}: {result.days_old} days old")
            else:
                lines.append(f"✅ {table_name}: Fresh (as of {result.latest_date})")

        return "\n".join(lines)


# Singleton instance for convenience
data_validator = DataQualityValidator()
