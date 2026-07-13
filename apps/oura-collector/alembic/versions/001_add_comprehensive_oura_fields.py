"""Add comprehensive Oura data fields and time-series tables

Revision ID: 001
Revises:
Create Date: 2026-07-13

This migration adds:
- 10 new fields to oura_sleep_periods table
- 6 new fields to oura_activity table
- 1 new contributor to oura_readiness table
- 2 new time-series tables: oura_sleep_phase_timeseries, oura_activity_met_timeseries
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade database schema"""

    # Add new columns to oura_sleep_periods table
    op.add_column('oura_sleep_periods', sa.Column('period_number', sa.Integer(), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('low_battery_alert', sa.Boolean(), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('sleep_score_delta', sa.Float(), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('readiness_score_delta', sa.Float(), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('sleep_algorithm_version', sa.String(50), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('sleep_analysis_reason', sa.String(100), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('ring_id', sa.String(50), nullable=True))
    op.add_column('oura_sleep_periods', sa.Column('lowest_heart_rate', sa.Float(), nullable=True))

    # Add new columns to oura_activity table
    op.add_column('oura_activity', sa.Column('sedentary_met_minutes', sa.Float(), nullable=True))
    op.add_column('oura_activity', sa.Column('target_meters', sa.Integer(), nullable=True))
    op.add_column('oura_activity', sa.Column('meters_to_target', sa.Integer(), nullable=True))
    op.add_column('oura_activity', sa.Column('equivalent_walking_distance', sa.Float(), nullable=True))

    # Add new column to oura_readiness table for sleep_regularity contributor
    op.add_column('oura_readiness', sa.Column('score_sleep_regularity', sa.Integer(), nullable=True))

    # Create new SleepPhaseTimeSeries table
    op.create_table(
        'oura_sleep_phase_timeseries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sleep_period_id', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('sleep_phase_5_min', sa.String(50), nullable=True),
        sa.Column('sleep_phase_30_sec', sa.String(50), nullable=True),
        sa.Column('movement_30_sec', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for SleepPhaseTimeSeries
    op.create_index('idx_sleep_phase_period', 'oura_sleep_phase_timeseries', ['sleep_period_id'])
    op.create_index('idx_sleep_phase_timestamp', 'oura_sleep_phase_timeseries', ['timestamp'])

    # Create new ActivityMetTimeSeries table
    op.create_table(
        'oura_activity_met_timeseries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('activity_date', sa.Date(), nullable=False),
        sa.Column('class_5_min', sa.String(50), nullable=True),
        sa.Column('met_interval', sa.Integer(), nullable=True),
        sa.Column('met_items', sa.JSON(), nullable=True),
        sa.Column('met_timestamp', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create index for ActivityMetTimeSeries
    op.create_index('idx_activity_met_date', 'oura_activity_met_timeseries', ['activity_date'])


def downgrade():
    """Downgrade database schema"""

    # Drop indexes
    op.drop_index('idx_activity_met_date', table_name='oura_activity_met_timeseries')
    op.drop_index('idx_sleep_phase_timestamp', table_name='oura_sleep_phase_timeseries')
    op.drop_index('idx_sleep_phase_period', table_name='oura_sleep_phase_timeseries')

    # Drop new tables
    op.drop_table('oura_activity_met_timeseries')
    op.drop_table('oura_sleep_phase_timeseries')

    # Remove columns from oura_readiness
    op.drop_column('oura_readiness', 'score_sleep_regularity')

    # Remove columns from oura_activity
    op.drop_column('oura_activity', 'equivalent_walking_distance')
    op.drop_column('oura_activity', 'meters_to_target')
    op.drop_column('oura_activity', 'target_meters')
    op.drop_column('oura_activity', 'sedentary_met_minutes')

    # Remove columns from oura_sleep_periods
    op.drop_column('oura_sleep_periods', 'lowest_heart_rate')
    op.drop_column('oura_sleep_periods', 'ring_id')
    op.drop_column('oura_sleep_periods', 'sleep_analysis_reason')
    op.drop_column('oura_sleep_periods', 'sleep_algorithm_version')
    op.drop_column('oura_sleep_periods', 'readiness_score_delta')
    op.drop_column('oura_sleep_periods', 'sleep_score_delta')
    op.drop_column('oura_sleep_periods', 'low_battery_alert')
    op.drop_column('oura_sleep_periods', 'period_number')
