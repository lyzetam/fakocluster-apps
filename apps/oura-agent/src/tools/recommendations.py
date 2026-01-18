"""Recommendation tools for Oura Health Agent.

These tools provide personalized health recommendations based on data analysis.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from langchain_core.tools import tool


@tool
async def get_sleep_recommendations(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get personalized sleep improvement recommendations.

    Use this when the user asks how to sleep better, for sleep advice,
    or ways to improve their sleep quality.

    Returns:
        Personalized sleep recommendations
    """
    data = await queries.get_sleep_analysis_for_recommendations(db_session)

    if not data:
        return "Not enough sleep data for recommendations. Track a few more nights!"

    recommendations = []
    priority_areas = []

    # Check efficiency
    efficiency = data.get('avg_efficiency', 0)
    if efficiency < 85:
        recommendations.append(
            "**Improve Sleep Efficiency**\n"
            "- Go to bed only when sleepy\n"
            "- If you can't sleep after 20 min, get up and do something relaxing\n"
            "- Keep bedroom for sleep only"
        )
        priority_areas.append("sleep efficiency")

    # Check duration
    duration = data.get('avg_duration', 0)
    if duration < 7:
        recommendations.append(
            "**Increase Sleep Duration**\n"
            f"- Current average: {duration:.1f} hours\n"
            "- Target: 7-9 hours\n"
            "- Try moving bedtime 15-30 minutes earlier"
        )
        priority_areas.append("sleep duration")

    # Check deep sleep
    deep_pct = data.get('avg_deep_pct', 0)
    if deep_pct < 15:
        recommendations.append(
            "**Boost Deep Sleep**\n"
            "- Exercise regularly (but not close to bedtime)\n"
            "- Keep bedroom cool (65-68°F / 18-20°C)\n"
            "- Avoid alcohol, which disrupts deep sleep"
        )
        priority_areas.append("deep sleep")

    # Check REM sleep
    rem_pct = data.get('avg_rem_pct', 0)
    if rem_pct < 20:
        recommendations.append(
            "**Improve REM Sleep**\n"
            "- Maintain consistent sleep schedule\n"
            "- Avoid sleep deprivation (REM rebounds after catch-up)\n"
            "- Limit caffeine, especially after noon"
        )
        priority_areas.append("REM sleep")

    # Check consistency
    consistency = data.get('bedtime_consistency', 0)
    if consistency < 70:
        recommendations.append(
            "**Improve Sleep Consistency**\n"
            "- Set fixed bedtime and wake time (even weekends)\n"
            "- Create a pre-sleep routine\n"
            "- Avoid sleeping in more than 1 hour on weekends"
        )
        priority_areas.append("consistency")

    # Check latency
    latency = data.get('avg_latency', 0)
    if latency > 20:
        recommendations.append(
            "**Reduce Time to Fall Asleep**\n"
            f"- Current average: {latency:.0f} minutes\n"
            "- Avoid screens 1 hour before bed\n"
            "- Try relaxation techniques or reading"
        )
        priority_areas.append("sleep latency")

    if not recommendations:
        recommendations.append(
            "**Your sleep looks good!**\n"
            "- Maintain your current habits\n"
            "- Focus on consistency\n"
            "- Consider optimizing recovery time"
        )

    priority_text = ", ".join(priority_areas[:2]) if priority_areas else "maintaining current habits"

    return f"""Personalized Sleep Recommendations:

Current Sleep Profile:
- Average Duration: {data.get('avg_duration', 'N/A'):.1f} hours
- Average Efficiency: {data.get('avg_efficiency', 'N/A'):.0f}%
- Average Sleep Score: {data.get('avg_score', 'N/A'):.0f}/100

Priority Focus Areas: {priority_text}

{chr(10).join(recommendations)}

General Sleep Hygiene Tips:
- Keep bedroom dark, quiet, and cool
- Limit caffeine after 2 PM
- Get morning sunlight exposure
- Regular exercise (not too close to bedtime)"""


@tool
async def get_activity_recommendations(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get personalized activity and exercise recommendations.

    Use this when the user asks how to be more active, for exercise advice,
    or ways to improve their activity levels.

    Returns:
        Personalized activity recommendations
    """
    data = await queries.get_activity_analysis_for_recommendations(db_session)

    if not data:
        return "Not enough activity data for recommendations. Keep tracking!"

    recommendations = []

    # Check step count
    avg_steps = data.get('avg_steps', 0)
    if avg_steps < 7500:
        recommendations.append(
            "**Increase Daily Steps**\n"
            f"- Current average: {avg_steps:,.0f} steps\n"
            "- Target: 7,500-10,000 steps\n"
            "- Add a 10-minute walk after meals\n"
            "- Take stairs instead of elevator"
        )
    elif avg_steps < 10000:
        recommendations.append(
            "**Good step count! Small boost possible:**\n"
            f"- Current average: {avg_steps:,.0f} steps\n"
            "- You're close to 10,000 - add one extra short walk"
        )

    # Check workout frequency
    workouts_per_week = data.get('workouts_per_week', 0)
    if workouts_per_week < 3:
        recommendations.append(
            "**Increase Workout Frequency**\n"
            f"- Current: {workouts_per_week:.1f} workouts/week\n"
            "- Target: 3-5 workouts per week\n"
            "- Start with 2-3 sessions, then build up"
        )

    # Check sedentary time
    sedentary = data.get('avg_sedentary', 0)
    if sedentary > 480:  # 8 hours
        recommendations.append(
            "**Reduce Sedentary Time**\n"
            f"- Current average: {sedentary/60:.1f} hours sitting\n"
            "- Take movement breaks every 30-60 minutes\n"
            "- Consider a standing desk\n"
            "- Set hourly movement reminders"
        )

    # Check high intensity
    high_intensity = data.get('avg_high_activity', 0)
    if high_intensity < 15:  # Less than 15 min/day average
        recommendations.append(
            "**Add More Intensity**\n"
            f"- Current high intensity: {high_intensity:.0f} min/day average\n"
            "- Try interval training 2x/week\n"
            "- Add hills to walks or increase pace briefly"
        )

    if not recommendations:
        recommendations.append(
            "**Your activity levels are excellent!**\n"
            "- Maintain variety in your workouts\n"
            "- Consider progressive challenges\n"
            "- Balance intensity with recovery"
        )

    return f"""Personalized Activity Recommendations:

Current Activity Profile:
- Average Daily Steps: {avg_steps:,.0f}
- Workouts per Week: {workouts_per_week:.1f}
- Average Activity Score: {data.get('avg_score', 'N/A'):.0f}/100

{chr(10).join(recommendations)}

Activity Guidelines (WHO Recommendations):
- 150-300 min moderate activity per week
- OR 75-150 min vigorous activity per week
- Strength training 2+ days per week
- Reduce sedentary time when possible"""


@tool
async def get_recovery_recommendations(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get personalized recovery and readiness recommendations.

    Use this when the user asks how to improve recovery, boost readiness,
    or optimize their rest and recuperation.

    Returns:
        Personalized recovery recommendations
    """
    data = await queries.get_recovery_analysis_for_recommendations(db_session)

    if not data:
        return "Not enough recovery data for recommendations."

    recommendations = []

    # Check readiness
    avg_readiness = data.get('avg_readiness', 0)
    if avg_readiness < 70:
        recommendations.append(
            "**Improve Overall Readiness**\n"
            f"- Current average: {avg_readiness:.0f}/100\n"
            "- Prioritize sleep quality and consistency\n"
            "- Balance training load with rest days\n"
            "- Monitor for signs of overtraining"
        )

    # Check HRV
    hrv_trend = data.get('hrv_trend', 'stable')
    if hrv_trend == 'declining':
        recommendations.append(
            "**HRV is Declining**\n"
            "- Consider reducing training intensity\n"
            "- Add more rest days\n"
            "- Practice stress management\n"
            "- Review sleep quality"
        )

    # Check resting HR
    rhr_trend = data.get('rhr_trend', 'stable')
    if rhr_trend == 'increasing':
        recommendations.append(
            "**Resting Heart Rate is Elevated**\n"
            "- This can indicate accumulated stress\n"
            "- Prioritize recovery for a few days\n"
            "- Check hydration and sleep\n"
            "- Reduce stimulant intake"
        )

    # Check temperature
    temp_deviation = data.get('avg_temp_deviation', 0)
    if abs(temp_deviation) > 0.5:
        recommendations.append(
            "**Body Temperature Variation**\n"
            f"- Recent deviation: {temp_deviation:+.1f}°C\n"
            "- Monitor for illness symptoms\n"
            "- Ensure adequate rest\n"
            "- Stay hydrated"
        )

    # Check sleep balance
    sleep_balance = data.get('sleep_balance_score', 100)
    if sleep_balance < 70:
        recommendations.append(
            "**Sleep Debt Detected**\n"
            "- Your sleep balance is low\n"
            "- Add 30-60 min extra sleep for a few nights\n"
            "- Avoid sleep debt accumulation"
        )

    if not recommendations:
        recommendations.append(
            "**Your recovery looks good!**\n"
            "- Maintain current habits\n"
            "- Continue balanced training\n"
            "- Listen to your body's signals"
        )

    return f"""Personalized Recovery Recommendations:

Current Recovery Profile:
- Average Readiness: {avg_readiness:.0f}/100
- HRV Trend: {hrv_trend.title()}
- RHR Trend: {rhr_trend.title()}

{chr(10).join(recommendations)}

Recovery Best Practices:
- Prioritize 7-9 hours of quality sleep
- Manage stress through breathing or meditation
- Balance hard training with recovery days
- Stay hydrated and well-nourished
- Listen to your body - rest when needed"""


@tool
async def get_personalized_insights(
    db_session: Annotated[any, "Database session (injected)"],
    queries: Annotated[any, "OuraDataQueries instance (injected)"],
) -> str:
    """Get personalized insights based on all available health data.

    Use this when the user asks for overall insights, what they should focus on,
    or general health advice personalized to their data.

    Returns:
        Personalized health insights
    """
    data = await queries.get_comprehensive_analysis(db_session)

    if not data:
        return "Not enough data for personalized insights. Keep tracking!"

    insights = []

    # Determine primary focus area
    sleep_score = data.get('avg_sleep_score', 70)
    readiness_score = data.get('avg_readiness_score', 70)
    activity_score = data.get('avg_activity_score', 70)

    lowest_score = min(sleep_score, readiness_score, activity_score)
    if lowest_score == sleep_score:
        focus_area = "sleep"
    elif lowest_score == readiness_score:
        focus_area = "recovery"
    else:
        focus_area = "activity"

    # Generate insights based on data patterns
    if data.get('weekend_sleep_difference', 0) > 60:
        insights.append(
            "You sleep significantly more on weekends - try to reduce this gap for better consistency."
        )

    if data.get('late_bedtime_impact', 0) > 10:
        insights.append(
            "Your sleep scores drop when you go to bed late. Earlier bedtimes correlate with better rest."
        )

    if data.get('workout_recovery_correlation', 0) > 0.5:
        insights.append(
            "Your readiness improves after moderate exercise days. Keep up the balanced activity!"
        )

    if data.get('hrv_alcohol_correlation', 0) < -0.3:
        insights.append(
            "Your HRV drops noticeably after nights with alcohol. Consider moderation for better recovery."
        )

    if not insights:
        insights.append(
            "Keep tracking consistently to uncover more personal patterns."
        )

    return f"""Personalized Health Insights:

Your Health Snapshot:
- Sleep Score: {sleep_score:.0f}/100
- Readiness Score: {readiness_score:.0f}/100
- Activity Score: {activity_score:.0f}/100

Primary Focus Area: {focus_area.title()}

Personal Patterns Discovered:
{chr(10).join([f"• {insight}" for insight in insights])}

Your Strengths:
- {data.get('strength_1', 'Consistent tracking habits')}
- {data.get('strength_2', 'Regular activity levels')}

Areas for Growth:
- {data.get('growth_1', 'Sleep consistency')}
- {data.get('growth_2', 'Recovery optimization')}

Next Steps:
1. Focus on your {focus_area} as it's currently your lowest area
2. Maintain what's working well
3. Review your data weekly to track progress"""
