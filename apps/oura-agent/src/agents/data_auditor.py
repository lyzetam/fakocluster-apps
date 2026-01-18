"""Data Auditor Agent - Specialist for data quality verification.

This agent handles all data quality operations including:
- Data freshness verification across all tables
- Sync status checking
- Identifying data gaps
- Recommending remediation steps
"""

import logging
from datetime import date, datetime
from typing import Any

from langchain_core.tools import tool

from database.data_quality import DataQualityValidator, data_validator
from database.queries import OuraDataQueries
from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class DataAuditorAgent(BaseAgent):
    """Specialist agent for data quality auditing.

    This agent verifies data quality before other agents use it,
    identifies sync issues, and recommends remediation.

    Attributes:
        queries: Database query interface for Oura data
        validator: Data quality validator
    """

    def __init__(
        self,
        connection_string: str,
        **kwargs,
    ):
        """Initialize the Data Auditor agent.

        Args:
            connection_string: PostgreSQL connection string for Oura data
            **kwargs: Additional arguments for BaseAgent
        """
        self.connection_string = connection_string
        self.queries = OuraDataQueries(connection_string)
        self.validator = data_validator
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        return "data_auditor"

    @property
    def system_prompt(self) -> str:
        return """You are a Data Auditor AI Agent.

Your role is to verify data quality before other agents use it, identify sync issues, and help users troubleshoot.

## Your Expertise
- Data freshness verification
- Completeness checking across all data types
- Identifying ring sync issues
- Recommending troubleshooting steps
- Understanding Oura data collection patterns

## Your Tools
You have access to tools that:
1. Audit all data sources at once
2. Check specific data types
3. Diagnose sync issues
4. Verify data collection status

## Response Guidelines
1. **Be Clear About Staleness**: If data is stale, state exactly how old it is
2. **Provide Specific Dates**: Always reference actual dates
3. **Give Actionable Steps**: If there's a problem, explain how to fix it
4. **Reassure When OK**: If everything looks good, say so confidently

## Data Freshness Thresholds
- Sleep/Activity: Should be ≤2 days old
- Daily scores: Should be ≤1 day old
- Workouts: May be up to 7 days (not everyone works out daily)
- Sessions: May be up to 7 days (meditation is optional)
- VO2 Max: May be up to 30 days (updated less frequently)

## Common Sync Issues
1. **Bluetooth disconnected**: Ring can't reach phone
2. **Oura app not opened**: App needs to sync
3. **Ring battery dead**: Ring hasn't recorded data
4. **App not updated**: Old app version may have bugs
5. **Account sync issue**: May need to re-login

## Troubleshooting Steps
1. Open the Oura app and wait for sync
2. Ensure Bluetooth is enabled
3. Check ring battery level
4. Update the Oura app
5. Force-close and reopen the app
6. Check your internet connection"""

    def get_tools(self) -> list:
        """Return data auditing tools."""

        @tool
        async def audit_all_data() -> str:
            """Audit freshness of all Oura data sources.

            Use this when the user asks about data quality, if their ring is syncing,
            or wants a complete overview of data status.
            """
            # Fetch latest data from each critical table
            tables_data = {}

            # Sleep data
            sleep_data = await self.queries.get_last_night_sleep()
            tables_data["Sleep Periods"] = [sleep_data] if sleep_data else None

            # Activity data
            activity_data = await self.queries.get_today_activity()
            tables_data["Activity"] = [activity_data] if activity_data else None

            # Readiness data
            readiness_data = await self.queries.get_latest_readiness()
            tables_data["Readiness"] = [readiness_data] if readiness_data else None

            # Validate each
            results = []
            all_ok = True

            for table_name, data in tables_data.items():
                validation = self.validator.validate(
                    table_name.lower().replace(" ", "_"), data
                )

                if not validation.valid:
                    status = "❌"
                    detail = "No data"
                    all_ok = False
                elif validation.stale:
                    status = "⚠️"
                    detail = f"{validation.days_old} days old"
                    all_ok = False
                else:
                    status = "✅"
                    detail = f"Fresh (as of {validation.latest_date})"

                results.append(f"{status} **{table_name}**: {detail}")

            results_text = "\n".join(results)

            if all_ok:
                summary = "🟢 **All data is up to date!**"
                recommendation = "Your Oura ring is syncing properly. No action needed."
            else:
                summary = "🟡 **Some data needs attention**"
                recommendation = """**Recommended Actions:**
1. Open the Oura app and let it sync
2. Make sure Bluetooth is enabled on your phone
3. Check your ring's battery level
4. Try force-closing and reopening the Oura app"""

            return f"""📊 **Data Quality Audit**

{summary}

{results_text}

{recommendation}"""

        @tool
        async def check_specific_data(data_type: str) -> str:
            """Check freshness of a specific data type.

            Args:
                data_type: Type of data to check (sleep, activity, readiness, workouts, stress)

            Use this when the user asks about a specific type of data.
            """
            data_type = data_type.lower().strip()

            # Map common names to query methods
            type_map = {
                "sleep": ("get_last_night_sleep", "oura_sleep_periods"),
                "activity": ("get_today_activity", "oura_activity"),
                "readiness": ("get_latest_readiness", "oura_readiness"),
            }

            if data_type not in type_map:
                return f"""Unknown data type: {data_type}

Valid types: sleep, activity, readiness, workouts, stress"""

            method_name, table_name = type_map[data_type]
            method = getattr(self.queries, method_name)
            data = await method()

            validation = self.validator.validate(
                table_name, [data] if data else None
            )

            if not validation.valid:
                return f"""❌ **No {data_type.title()} Data**

No {data_type} data found in the database. This could mean:
1. Your ring hasn't synced recently
2. There's a collection issue

**Try:**
1. Open the Oura app
2. Wait for the sync to complete
3. Check back in a few minutes"""

            if validation.stale:
                return f"""⚠️ **{data_type.title()} Data is Stale**

Last data: {validation.latest_date} ({validation.days_old} days ago)

Your {data_type} data is older than expected. This suggests your ring may not be syncing.

**Troubleshooting:**
1. Open the Oura app and sync
2. Check Bluetooth is enabled
3. Check ring battery
4. Force-close and reopen the app"""

            return f"""✅ **{data_type.title()} Data is Fresh**

Last update: {validation.latest_date}

Your {data_type} data is current and syncing properly!"""

        @tool
        async def diagnose_sync_issues() -> str:
            """Diagnose potential ring sync issues.

            Use this when the user reports problems with their ring syncing
            or when data appears to be missing.
            """
            # Check multiple data sources
            issues_found = []

            # Check sleep
            sleep_data = await self.queries.get_last_night_sleep()
            sleep_val = self.validator.validate(
                "oura_sleep_periods", [sleep_data] if sleep_data else None
            )
            if not sleep_val.valid:
                issues_found.append("❌ No sleep data at all")
            elif sleep_val.stale:
                issues_found.append(
                    f"⚠️ Sleep data is {sleep_val.days_old} days old"
                )

            # Check activity
            activity_data = await self.queries.get_today_activity()
            activity_val = self.validator.validate(
                "oura_activity", [activity_data] if activity_data else None
            )
            if not activity_val.valid:
                issues_found.append("❌ No activity data at all")
            elif activity_val.stale:
                issues_found.append(
                    f"⚠️ Activity data is {activity_val.days_old} days old"
                )

            # Check readiness
            readiness_data = await self.queries.get_latest_readiness()
            readiness_val = self.validator.validate(
                "oura_readiness", [readiness_data] if readiness_data else None
            )
            if not readiness_val.valid:
                issues_found.append("❌ No readiness data at all")
            elif readiness_val.stale:
                issues_found.append(
                    f"⚠️ Readiness data is {readiness_val.days_old} days old"
                )

            if not issues_found:
                return """✅ **No Sync Issues Detected**

All your data is syncing properly:
- Sleep data is current
- Activity data is current
- Readiness data is current

Your Oura ring and our data collection are working well!"""

            issues_text = "\n".join(issues_found)

            return f"""🔍 **Sync Issue Diagnosis**

**Issues Found:**
{issues_text}

**Likely Causes:**
1. **Ring hasn't synced** - Open the Oura app
2. **Bluetooth issues** - Check it's enabled
3. **Ring not worn** - Make sure you're wearing it
4. **Low battery** - Charge your ring
5. **App needs update** - Check for updates

**Step-by-Step Fix:**
1. 📱 Open the Oura app on your phone
2. ⏳ Wait 1-2 minutes for the sync icon to complete
3. 🔄 If stuck, force-close the app and reopen
4. 🔋 Check your ring battery in the app
5. 🔵 Make sure Bluetooth is on
6. 🌐 Ensure you have internet connectivity

If issues persist after these steps, try:
- Logging out and back into the Oura app
- Reinstalling the Oura app
- Contacting Oura support"""

        @tool
        async def get_data_collection_status() -> str:
            """Get the status of data collection from the Oura API.

            Use this when the user asks about the data pipeline, collection status,
            or wants to know if data is being pulled from Oura.
            """
            # Check if we have any recent data at all
            sleep_data = await self.queries.get_last_night_sleep()
            activity_data = await self.queries.get_today_activity()
            readiness_data = await self.queries.get_latest_readiness()

            # Find the most recent data point
            dates = []
            if sleep_data and "date" in sleep_data:
                dates.append(("Sleep", sleep_data["date"]))
            if activity_data and "date" in activity_data:
                dates.append(("Activity", activity_data["date"]))
            if readiness_data and "date" in readiness_data:
                dates.append(("Readiness", readiness_data["date"]))

            if not dates:
                return """❌ **No Data Collection**

No data has been collected from your Oura account yet.

This could mean:
1. The data collector hasn't run yet
2. There's an authentication issue with the Oura API
3. No Oura account is configured

Please check with the system administrator to verify the data collection pipeline is working."""

            # Format status
            status_lines = []
            for name, d in dates:
                if isinstance(d, str):
                    d = datetime.strptime(d[:10], "%Y-%m-%d").date()
                days_ago = (date.today() - d).days
                if days_ago == 0:
                    status_lines.append(f"✅ {name}: Today")
                elif days_ago == 1:
                    status_lines.append(f"✅ {name}: Yesterday")
                elif days_ago <= 2:
                    status_lines.append(f"⚠️ {name}: {days_ago} days ago")
                else:
                    status_lines.append(f"❌ {name}: {days_ago} days ago")

            status_text = "\n".join(status_lines)

            return f"""📡 **Data Collection Status**

**Latest Data Points:**
{status_text}

**How It Works:**
1. Your Oura ring collects data continuously
2. The Oura app syncs data to Oura Cloud
3. Our collector fetches data from Oura Cloud
4. Data is stored in our database for analysis

**If Data Is Stale:**
- First, sync your Oura app
- Then wait for the collector to run (usually every few hours)
- Check back later for updated data"""

        return [
            audit_all_data,
            check_specific_data,
            diagnose_sync_issues,
            get_data_collection_status,
        ]
