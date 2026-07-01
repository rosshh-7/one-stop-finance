"""phase2: new signal tables + synthesis columns on theme_scores

Revision ID: c1d2e3f4a5b6
Revises: 7d60a48c6196
Create Date: 2026-06-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'c1d2e3f4a5b6'
down_revision = '7d60a48c6196'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Synthesis columns on theme_scores -----------------------------------
    op.add_column('theme_scores', sa.Column('thesis', sa.Text(), nullable=True))
    op.add_column('theme_scores', sa.Column('watch_for', sa.String(500), nullable=True))
    op.add_column('theme_scores', sa.Column('confidence', sa.String(20), nullable=True))
    op.add_column('theme_scores', sa.Column('synthesized_at', sa.DateTime(timezone=True), nullable=True))

    # --- activist_stakes ------------------------------------------------------
    op.create_table(
        'activist_stakes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('filer_name', sa.String(255), nullable=True),
        sa.Column('filer_cik', sa.String(20), nullable=True),
        sa.Column('shares_held', sa.Integer(), nullable=True),
        sa.Column('pct_of_class', sa.Float(), nullable=True),
        sa.Column('filing_type', sa.String(10), nullable=False),
        sa.Column('filed_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_new', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'filer_cik', 'filed_date'),
    )
    op.create_index('ix_activist_stakes_ticker', 'activist_stakes', ['ticker'])
    op.create_index('ix_activist_stakes_filed_date', 'activist_stakes', ['filed_date'])

    # --- institutional_holdings -----------------------------------------------
    op.create_table(
        'institutional_holdings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('institution', sa.String(255), nullable=True),
        sa.Column('institution_cik', sa.String(20), nullable=True),
        sa.Column('shares_held', sa.Integer(), nullable=True),
        sa.Column('market_value', sa.Float(), nullable=True),
        sa.Column('is_new_position', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('quarter', sa.String(10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'institution_cik', 'quarter'),
    )
    op.create_index('ix_institutional_holdings_ticker', 'institutional_holdings', ['ticker'])
    op.create_index('ix_institutional_holdings_quarter', 'institutional_holdings', ['quarter'])

    # --- short_interest -------------------------------------------------------
    op.create_table(
        'short_interest',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('short_interest', sa.Integer(), nullable=True),
        sa.Column('float_shares', sa.Integer(), nullable=True),
        sa.Column('short_ratio', sa.Float(), nullable=True),
        sa.Column('settlement_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker', 'settlement_date'),
    )
    op.create_index('ix_short_interest_ticker', 'short_interest', ['ticker'])
    op.create_index('ix_short_interest_settlement_date', 'short_interest', ['settlement_date'])

    # --- nih_grants -----------------------------------------------------------
    op.create_table(
        'nih_grants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('nih_project_id', sa.String(100), nullable=True, unique=True),
        sa.Column('project_title', sa.String(500), nullable=True),
        sa.Column('fiscal_year', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('theme_slug', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_nih_grants_theme_slug', 'nih_grants', ['theme_slug'])

    # --- patent_signals -------------------------------------------------------
    op.create_table(
        'patent_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('patent_id', sa.String(50), nullable=False, unique=True),
        sa.Column('ticker', sa.String(10), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('theme_slug', sa.String(100), nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('grant_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_patent_signals_ticker', 'patent_signals', ['ticker'])
    op.create_index('ix_patent_signals_theme_slug', 'patent_signals', ['theme_slug'])
    op.create_index('ix_patent_signals_grant_date', 'patent_signals', ['grant_date'])

    # --- macro_signals --------------------------------------------------------
    op.create_table(
        'macro_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('series_id', sa.String(50), nullable=False),
        sa.Column('series_name', sa.String(100), nullable=True),
        sa.Column('observation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('prev_value', sa.Float(), nullable=True),
        sa.Column('pct_change', sa.Float(), nullable=True),
        sa.Column('theme_relevance', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('series_id', 'observation_date'),
    )
    op.create_index('ix_macro_signals_series_id', 'macro_signals', ['series_id'])
    op.create_index('ix_macro_signals_observation_date', 'macro_signals', ['observation_date'])

    # --- eightk_signals -------------------------------------------------------
    op.create_table(
        'eightk_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('accession_number', sa.String(50), nullable=False, unique=True),
        sa.Column('ticker', sa.String(10), nullable=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('filed_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('signal_type', sa.String(50), nullable=True),
        sa.Column('deal_amount', sa.Float(), nullable=True),
        sa.Column('description', sa.String(1000), nullable=True),
        sa.Column('theme_slugs', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_eightk_signals_ticker', 'eightk_signals', ['ticker'])
    op.create_index('ix_eightk_signals_filed_date', 'eightk_signals', ['filed_date'])

    # --- formd_signals --------------------------------------------------------
    op.create_table(
        'formd_signals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('accession_number', sa.String(50), nullable=False, unique=True),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('filed_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount_raised', sa.Float(), nullable=True),
        sa.Column('is_ai_related', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('theme_slugs', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_formd_signals_filed_date', 'formd_signals', ['filed_date'])


def downgrade() -> None:
    op.drop_table('formd_signals')
    op.drop_table('eightk_signals')
    op.drop_table('macro_signals')
    op.drop_table('patent_signals')
    op.drop_table('nih_grants')
    op.drop_table('short_interest')
    op.drop_table('institutional_holdings')
    op.drop_table('activist_stakes')
    op.drop_column('theme_scores', 'synthesized_at')
    op.drop_column('theme_scores', 'confidence')
    op.drop_column('theme_scores', 'watch_for')
    op.drop_column('theme_scores', 'thesis')
