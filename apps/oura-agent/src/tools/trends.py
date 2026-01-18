"""Trends and insights tools for Oura Health Agent.

These tools provide comprehensive health trend analysis and correlations.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_weekly_health_summary(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get a comprehensive weekly health summary.

    Use this when the user asks for a weekly summary, overall health status,
    or a complete overview of their health data.

    Returns:
        Weekly health summary
    """
    data = await queries.get_weekly_summary(db_session)

    if not data:
        return "Not enough data for a weekly summary. Need at least a few days of data."

    return f"""Weekly Health Summary:

Overall Scores (7-Day Average):
- Sleep Score: {data.get('avg_sleep_score', 'N/A')}/100
- Readiness Score: {data.get('avg_readiness_score', 'N/A')}/100
- Activity Score: {data.get('avg_activity_score', 'N/A')}/100

Sleep:
- Average Duration: {data.get('avg_sleep_duration', 'N/A')} hours
- Average Efficiency: {data.get('avg_sleep_efficiency', 'N/A')}%
- Best Sleep Night: {data.get('best_sleep_day', 'N/A')} ({data.get('best_sleep_score', 'N/A')})

Activity:
- Average Daily Steps: {data.get('avg_steps', 'N/A'):,}
- Total Workouts: {data.get('total_workouts', 'N/A')}
- Active Calories (weekly): {data.get('total_active_calories', 'N/A'):,} kcal

Recovery:
- Average HRV: {data.get('avg_hrv', 'N/A')} ms
- Average Resting HR: {data.get('avg_resting_hr', 'N/A')} bpm

Weekly Highlights:
- Best Day: {data.get('best_overall_day', 'N/A')}
- Area to Focus: {data.get('lowest_category', 'N/A')}

Recommendation: {data.get('weekly_recommendation', 'Keep up the good work and maintain consistency!')}"""


@tool
async def get_health_score_trends(
    days: Annotated[int, "Number of days to analyze (default 14)"] = 14,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Get trends for all health scores over time.

    Use this when the user asks about their overall health trends, score history,
    or how their health metrics have been trending.

    Args:
        days: Number of days to analyze (default 14)

    Returns:
        Health score trends
    """
    data = await queries.get_score_trends(db_session, days)

    if not data or len(data) == 0:
        return f"No health score data found for the last {days} days."

    sleep_scores = [d.get('sleep_score', 0) for d in data if d.get('sleep_score')]
    readiness_scores = [d.get('readiness_score', 0) for d in data if d.get('readiness_score')]
    activity_scores = [d.get('activity_score', 0) for d in data if d.get('activity_score')]

    def trend_direction(scores):
        if len(scores) < 4:
            return "insufficient data"
        recent = sum(scores[:len(scores)//2]) / (len(scores)//2)
        older = sum(scores[len(scores)//2:]) / (len(scores)//2)
        if recent > older + 3:
            return "improving ↑"
        elif recent < older - 3:
            return "declining ↓"
        return "stable →"

    recent_data = "\n".join([
        f"- {d.get('day', 'N/A')}: Sleep {d.get('sleep_score', 'N/A')}, "
        f"Readiness {d.get('readiness_score', 'N/A')}, Activity {d.get('activity_score', 'N/A')}"
        for d in data[:7]
    ])

    return f"""Health Score Trends (Last {days} Days):

Score Averages:
- Sleep: {sum(sleep_scores)/len(sleep_scores):.0f}/100 - {trend_direction(sleep_scores)}
- Readiness: {sum(readiness_scores)/len(readiness_scores):.0f}/100 - {trend_direction(readiness_scores)}
- Activity: {sum(activity_scores)/len(activity_scores):.0f}/100 - {trend_direction(activity_scores)}

Recent Days:
{recent_data}

Interpretation:
- ↑ Improving: Positive changes in recent days
- → Stable: Consistent scores
- ↓ Declining: May need attention

Focus on the score with the lowest trend for potential improvement areas."""


@tool
async def compare_periods(
    metric: Annotated[str, "Metric to compare (sleep_score, steps, hrv, etc.)"],
    days1: Annotated[int, "First period - recent days (default 7)"] = 7,
    days2: Annotated[int, "Second period - older days to compare (default 7)"] = 7,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Compare a health metric between two time periods.

    Use this when the user wants to compare this week to last week,
    or compare different time periods.

    Args:
        metric: The metric to compare
        days1: Number of recent days (default 7)
        days2: Number of older days for comparison (default 7)

    Returns:
        Period comparison
    """
    data = await queries.compare_periods(db_session, metric, days1, days2)

    if not data:
        return f"Not enough data to compare {metric} between periods."

    recent_avg = data.get('recent_avg', 0)
    older_avg = data.get('older_avg', 0)
    diff = recent_avg - older_avg
    pct_change = (diff / older_avg * 100) if older_avg != 0 else 0

    return f"""Period Comparison: {metric.replace('_', ' ').title()}

Recent {days1} Days:
- Average: {recent_avg:.1f}
- High: {data.get('recent_high', 'N/A')}
- Low: {data.get('recent_low', 'N/A')}

Previous {days2} Days:
- Average: {older_avg:.1f}
- High: {data.get('older_high', 'N/A')}
- Low: {data.get('older_low', 'N/A')}

Change:
- Difference: {diff:+.1f}
- Percent Change: {pct_change:+.1f}%

Trend: {'Improving' if diff > 0 else 'Declining' if diff < 0 else 'Stable'}

Note: Consider what factors might have contributed to this change."""


@tool
async def get_day_of_week_patterns(
    days: Annotated[int, "Number of days to analyze (default 28)"] = 28,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Analyze health patterns by day of week.

    Use this when the user asks about their best/worst days, weekly patterns,
    or which days they perform better on.

    Args:
        days: Number of days to analyze (default 28)

    Returns:
        Day of week pattern analysis
    """
    data = await queries.get_day_patterns(db_session, days)

    if not data:
        return f"Not enough data to analyze day of week patterns. Need at least 4 weeks of data."

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    pattern_data = "\n".join([
        f"- {day}: Sleep {data.get(day, {}).get('sleep_score', 'N/A')}, "
        f"Readiness {data.get(day, {}).get('readiness_score', 'N/A')}, "
        f"Steps {data.get(day, {}).get('steps', 'N/A'):,}"
        for day in day_order if day in data
    ])

    # Find best and worst days
    sleep_by_day = [(day, data.get(day, {}).get('sleep_score', 0)) for day in day_order if day in data]
    best_sleep_day = max(sleep_by_day, key=lambda x: x[1])[0] if sleep_by_day else "N/A"
    worst_sleep_day = min(sleep_by_day, key=lambda x: x[1])[0] if sleep_by_day else "N/A"

    return f"""Day of Week Patterns (Last {days} Days):

Average by Day:
{pattern_data}

Insights:
- Best Sleep Day: {best_sleep_day}
- Worst Sleep Day: {worst_sleep_day}

Common Patterns:
- Weekend sleep often differs from weekday sleep
- Monday readiness affected by weekend activities
- Friday activity may be lower due to work fatigue

Use these patterns to:
- Plan intense workouts on high-readiness days
- Prioritize sleep on days where it tends to be poor
- Adjust weekend habits if they impact Monday readiness"""


@tool
async def get_correlations(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Analyze correlations between different health metrics.

    Use this when the user asks how metrics relate to each other,
    what affects their sleep, or correlations in their data.

    Returns:
        Correlation analysis
    """
    data = await queries.get_correlations(db_session)

    if not data:
        return "Not enough data to analyze correlations. Need at least 2 weeks of data."

    correlations = []

    # Sleep and Readiness
    if 'sleep_readiness_corr' in data:
        corr = data['sleep_readiness_corr']
        if abs(corr) > 0.5:
            correlations.append(f"- Sleep → Readiness: {'Strong positive' if corr > 0 else 'Strong negative'} ({corr:.2f})")

    # Activity and Sleep
    if 'activity_sleep_corr' in data:
        corr = data['activity_sleep_corr']
        if abs(corr) > 0.3:
            correlations.append(f"- Activity → Sleep: {'Positive' if corr > 0 else 'Negative'} ({corr:.2f})")

    # HRV and Readiness
    if 'hrv_readiness_corr' in data:
        corr = data['hrv_readiness_corr']
        if abs(corr) > 0.5:
            correlations.append(f"- HRV → Readiness: {'Strong positive' if corr > 0 else 'Strong negative'} ({corr:.2f})")

    if not correlations:
        correlations.append("No strong correlations found yet. Keep tracking for more insights.")

    return f"""Correlation Analysis:

Key Relationships Found:
{chr(10).join(correlations)}

What Correlations Mean:
- Positive correlation: Metrics tend to move together
- Negative correlation: When one goes up, the other goes down
- Strong (>0.5): Reliable relationship
- Moderate (0.3-0.5): Some relationship

Your Data Suggests:
{data.get('insight', 'Continue tracking to uncover personal patterns.')}

Common Correlations:
- Better sleep usually leads to better readiness
- Moderate activity often improves sleep quality
- High HRV typically correlates with better recovery"""


@tool
async def get_best_and_worst_days(
    metric: Annotated[str, "Metric to analyze (sleep_score, readiness_score, steps, hrv)"],
    days: Annotated[int, "Number of days to analyze (default 30)"] = 30,
    db_session: Annotated[any, "Database session (injected)"] = None,
    queries: Annotated[any, "OuraDataQueries instance (injected)"] = None,
) -> str:
    """Find the best and worst days for a specific metric.

    Use this when the user asks about their best sleep day, worst readiness,
    or peak performance days.

    Args:
        metric: The metric to analyze
        days: Number of days to look back (default 30)

    Returns:
        Best and worst days analysis
    """
    data = await queries.get_best_worst_days(db_session, metric, days)

    if not data:
        return f"Not enough {metric.replace('_', ' ')} data to analyze."

    best_days = data.get('best_days', [])[:3]
    worst_days = data.get('worst_days', [])[:3]

    best_list = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('value', 'N/A')}"
        for d in best_days
    ])

    worst_list = "\n".join([
        f"- {d.get('day', 'N/A')}: {d.get('value', 'N/A')}"
        for d in worst_days
    ])

    return f"""Best and Worst Days: {metric.replace('_', ' ').title()} (Last {days} Days)

Top 3 Best Days:
{best_list}

Bottom 3 Days:
{worst_list}

Statistics:
- Average: {data.get('average', 'N/A')}
- Standard Deviation: {data.get('std_dev', 'N/A')}
- Days Analyzed: {data.get('count', 'N/A')}

Consider:
- What did you do differently on your best days?
- What factors contributed to your worst days?
- Use this insight to replicate good days and avoid patterns that lead to poor days."""
