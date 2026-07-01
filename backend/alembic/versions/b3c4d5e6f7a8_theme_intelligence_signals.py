"""theme_intelligence_signals

Revision ID: b3c4d5e6f7a8
Revises: 7452ffddfa65
Create Date: 2026-06-10 06:00:00.000000

Adds:
  - theme_score_history  (time-series score snapshots)
  - gov_contracts        (USASpending contract awards)
  - trend_signals        (Google Trends velocity per theme)
  - options_signals      (Polygon EOD options anomalies)
  - Extends theme_scores: velocity, lifecycle_stage, unique_companies_selling,
                          contracts_count, trend_velocity, options_anomaly
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = '7452ffddfa65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend theme_scores with new signal columns
    op.add_column('theme_scores', sa.Column('velocity', sa.Float(), nullable=True))
    op.add_column('theme_scores', sa.Column('lifecycle_stage', sa.String(length=20), nullable=True))
    op.add_column('theme_scores', sa.Column('unique_companies_selling', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('theme_scores', sa.Column('contracts_count', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('theme_scores', sa.Column('trend_velocity', sa.Float(), nullable=True))
    op.add_column('theme_scores', sa.Column('options_anomaly', sa.Float(), nullable=True))

    # Theme score history — time-series for the 12-week chart
    op.create_table(
        'theme_score_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('lifecycle_stage', sa.String(length=20), nullable=True),
        sa.Column('unique_companies_buying', sa.Integer(), nullable=True),
        sa.Column('signal_breakdown', sa.JSON(), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_theme_score_history_theme_id', 'theme_score_history', ['theme_id'])
    op.create_index('ix_theme_score_history_scored_at', 'theme_score_history', ['scored_at'])

    # Government contracts from USASpending
    op.create_table(
        'gov_contracts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=True),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('symbol', sa.String(length=10), nullable=True),
        sa.Column('award_amount', sa.Float(), nullable=True),
        sa.Column('agency_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('award_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('usaspending_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('usaspending_id'),
    )
    op.create_index('ix_gov_contracts_theme_id', 'gov_contracts', ['theme_id'])
    op.create_index('ix_gov_contracts_award_date', 'gov_contracts', ['award_date'])
    op.create_index('ix_gov_contracts_symbol', 'gov_contracts', ['symbol'])

    # Google Trends velocity per theme per week
    op.create_table(
        'trend_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('theme_id', sa.String(), nullable=False),
        sa.Column('keyword', sa.String(length=100), nullable=True),
        sa.Column('interest_score', sa.Float(), nullable=True),
        sa.Column('prev_week_score', sa.Float(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('week_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_trend_signals_theme_id', 'trend_signals', ['theme_id'])
    op.create_index('ix_trend_signals_week_start', 'trend_signals', ['week_start'])

    # Polygon EOD options volume anomalies per ticker
    op.create_table(
        'options_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('symbol', sa.String(length=10), nullable=False),
        sa.Column('call_volume', sa.Integer(), nullable=True),
        sa.Column('put_volume', sa.Integer(), nullable=True),
        sa.Column('total_volume', sa.Integer(), nullable=True),
        sa.Column('avg_30d_volume', sa.Integer(), nullable=True),
        sa.Column('anomaly_ratio', sa.Float(), nullable=True),
        sa.Column('signal_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'signal_date'),
    )
    op.create_index('ix_options_signals_symbol', 'options_signals', ['symbol'])
    op.create_index('ix_options_signals_signal_date', 'options_signals', ['signal_date'])


def downgrade() -> None:
    op.drop_index('ix_options_signals_signal_date', table_name='options_signals')
    op.drop_index('ix_options_signals_symbol', table_name='options_signals')
    op.drop_table('options_signals')
    op.drop_index('ix_trend_signals_week_start', table_name='trend_signals')
    op.drop_index('ix_trend_signals_theme_id', table_name='trend_signals')
    op.drop_table('trend_signals')
    op.drop_index('ix_gov_contracts_symbol', table_name='gov_contracts')
    op.drop_index('ix_gov_contracts_award_date', table_name='gov_contracts')
    op.drop_index('ix_gov_contracts_theme_id', table_name='gov_contracts')
    op.drop_table('gov_contracts')
    op.drop_index('ix_theme_score_history_scored_at', table_name='theme_score_history')
    op.drop_index('ix_theme_score_history_theme_id', table_name='theme_score_history')
    op.drop_table('theme_score_history')
    op.drop_column('theme_scores', 'options_anomaly')
    op.drop_column('theme_scores', 'trend_velocity')
    op.drop_column('theme_scores', 'contracts_count')
    op.drop_column('theme_scores', 'unique_companies_selling')
    op.drop_column('theme_scores', 'lifecycle_stage')
    op.drop_column('theme_scores', 'velocity')
