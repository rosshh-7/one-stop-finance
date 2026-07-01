import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class ConvergenceLevel(str, enum.Enum):
    ALERT = "alert"
    WATCH = "watch"
    QUIET = "quiet"


class Theme(Base, TimestampMixin):
    __tablename__ = "themes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500))
    category: Mapped[str | None] = mapped_column(String(50), index=True)
    benchmark_etf: Mapped[str | None] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    tickers: Mapped[list["ThemeTicker"]] = relationship("ThemeTicker", back_populates="theme", lazy="selectin")
    score: Mapped["ThemeScore"] = relationship("ThemeScore", back_populates="theme", uselist=False, lazy="selectin")
    history: Mapped[list["ThemeScoreHistory"]] = relationship("ThemeScoreHistory", back_populates="theme")
    contracts: Mapped[list["GovContract"]] = relationship("GovContract", back_populates="theme")
    trend_signals: Mapped[list["TrendSignal"]] = relationship("TrendSignal", back_populates="theme")
    etf_signals: Mapped[list["ThemeETFSignal"]] = relationship("ThemeETFSignal", back_populates="theme")
    watchers: Mapped[list["UserThemeWatchlist"]] = relationship("UserThemeWatchlist", back_populates="theme")


class ThemeTicker(Base):
    __tablename__ = "theme_tickers"
    __table_args__ = (UniqueConstraint("theme_id", "symbol"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    market_cap_tier: Mapped[str | None] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    theme: Mapped["Theme"] = relationship("Theme", back_populates="tickers")


class ThemeScore(Base):
    __tablename__ = "theme_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), unique=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    level: Mapped[ConvergenceLevel] = mapped_column(Enum(ConvergenceLevel), default=ConvergenceLevel.QUIET)

    # Core insider signals
    unique_companies_buying: Mapped[int] = mapped_column(Integer, default=0)
    unique_companies_selling: Mapped[int] = mapped_column(Integer, default=0)
    total_value_accumulated: Mapped[float] = mapped_column(Float, default=0.0)
    csuite_count: Mapped[int] = mapped_column(Integer, default=0)
    congress_signal: Mapped[bool] = mapped_column(Boolean, default=False)
    unusual_options_count: Mapped[int] = mapped_column(Integer, default=0)
    sentiment_signal: Mapped[bool] = mapped_column(Boolean, default=False)

    # Extended signals
    contracts_count: Mapped[int] = mapped_column(Integer, default=0)
    trend_velocity: Mapped[float | None] = mapped_column(Float)
    options_anomaly: Mapped[float | None] = mapped_column(Float)

    # Velocity & lifecycle
    velocity: Mapped[float | None] = mapped_column(Float)
    lifecycle_stage: Mapped[str | None] = mapped_column(String(20))

    # Full breakdown JSON
    signal_breakdown: Mapped[dict | None] = mapped_column(JSON)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Synthesis (Claude Sonnet — runs daily for score > 45)
    thesis: Mapped[str | None] = mapped_column(Text)
    watch_for: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[str | None] = mapped_column(String(20))
    synthesized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    theme: Mapped["Theme"] = relationship("Theme", back_populates="score")


class ThemeScoreHistory(Base):
    __tablename__ = "theme_score_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), nullable=False, index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    velocity: Mapped[float | None] = mapped_column(Float)
    lifecycle_stage: Mapped[str | None] = mapped_column(String(20))
    unique_companies_buying: Mapped[int | None] = mapped_column(Integer)
    signal_breakdown: Mapped[dict | None] = mapped_column(JSON)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    theme: Mapped["Theme"] = relationship("Theme", back_populates="history")


class GovContract(Base):
    __tablename__ = "gov_contracts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str | None] = mapped_column(String, ForeignKey("themes.id"), index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255))
    symbol: Mapped[str | None] = mapped_column(String(10), index=True)
    award_amount: Mapped[float | None] = mapped_column(Float)
    agency_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(1000))
    award_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    usaspending_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    theme: Mapped["Theme | None"] = relationship("Theme", back_populates="contracts")


class TrendSignal(Base):
    __tablename__ = "trend_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), nullable=False, index=True)
    keyword: Mapped[str | None] = mapped_column(String(100))
    interest_score: Mapped[float | None] = mapped_column(Float)
    prev_week_score: Mapped[float | None] = mapped_column(Float)
    velocity: Mapped[float | None] = mapped_column(Float)
    week_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    theme: Mapped["Theme"] = relationship("Theme", back_populates="trend_signals")


class OptionsSignal(Base):
    __tablename__ = "options_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    call_volume: Mapped[int | None] = mapped_column(Integer)
    put_volume: Mapped[int | None] = mapped_column(Integer)
    total_volume: Mapped[int | None] = mapped_column(Integer)
    avg_30d_volume: Mapped[int | None] = mapped_column(Integer)
    anomaly_ratio: Mapped[float | None] = mapped_column(Float)
    signal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ThemeETFSignal(Base):
    """
    Daily flow + options snapshot for each theme's benchmark ETF.

    Flow signals (volume / 30d baseline + price action) approximate
    institutional rotation; options signals (put/call, OTM call OI, IV
    percentile) approximate positioning conviction. Both are aggregated
    at the ETF level and consumed by _score_theme().
    """
    __tablename__ = "theme_etf_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), nullable=False, index=True)
    etf_symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    signal_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Flow signals
    volume:           Mapped[int | None]   = mapped_column(Integer)
    avg_30d_volume:   Mapped[int | None]   = mapped_column(Integer)
    vol_ratio:        Mapped[float | None] = mapped_column(Float)
    price_change_pct: Mapped[float | None] = mapped_column(Float)

    # Options signals
    put_call_ratio:   Mapped[float | None] = mapped_column(Float)
    otm_call_oi:      Mapped[int | None]   = mapped_column(Integer)
    total_call_oi:    Mapped[int | None]   = mapped_column(Integer)
    iv_percentile:    Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    theme: Mapped["Theme"] = relationship("Theme", back_populates="etf_signals")


class UserThemeWatchlist(Base):
    __tablename__ = "user_theme_watchlist"
    __table_args__ = (UniqueConstraint("user_id", "theme_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    theme_id: Mapped[str] = mapped_column(String, ForeignKey("themes.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="theme_watchlist")
    theme: Mapped["Theme"] = relationship("Theme", back_populates="watchers")


# ---------------------------------------------------------------------------
# New signal tables (Phase 2 collectors)
# ---------------------------------------------------------------------------

class ActivistStake(Base):
    """13D/G activist stake filings from SEC EDGAR."""
    __tablename__ = "activist_stakes"
    __table_args__ = (UniqueConstraint("ticker", "filer_cik", "filed_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    filer_name: Mapped[str | None] = mapped_column(String(255))
    filer_cik: Mapped[str | None] = mapped_column(String(20))
    shares_held: Mapped[int | None] = mapped_column(Integer)
    pct_of_class: Mapped[float | None] = mapped_column(Float)
    filing_type: Mapped[str] = mapped_column(String(10))  # '13D' or '13G'
    filed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_new: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class InstitutionalHolding(Base):
    """13F institutional holdings delta — new positions this quarter."""
    __tablename__ = "institutional_holdings"
    __table_args__ = (UniqueConstraint("ticker", "institution_cik", "quarter"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    institution: Mapped[str | None] = mapped_column(String(255))
    institution_cik: Mapped[str | None] = mapped_column(String(20))
    shares_held: Mapped[int | None] = mapped_column(Integer)
    market_value: Mapped[float | None] = mapped_column(Float)
    is_new_position: Mapped[bool] = mapped_column(Boolean, default=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # "2025Q1"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ShortInterest(Base):
    """FINRA short interest flat files (bi-monthly)."""
    __tablename__ = "short_interest"
    __table_args__ = (UniqueConstraint("ticker", "settlement_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    short_interest: Mapped[int | None] = mapped_column(Integer)
    float_shares: Mapped[int | None] = mapped_column(Integer)
    short_ratio: Mapped[float | None] = mapped_column(Float)
    settlement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NihGrant(Base):
    """NIH Reporter grant awards — Biotech & Genomics theme only."""
    __tablename__ = "nih_grants"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    nih_project_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    project_title: Mapped[str | None] = mapped_column(String(500))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    total_cost: Mapped[float | None] = mapped_column(Float)
    keywords: Mapped[list | None] = mapped_column(JSON)
    theme_slug: Mapped[str | None] = mapped_column(String(100), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PatentSignal(Base):
    """USPTO PatentsView patent grants by theme company."""
    __tablename__ = "patent_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    patent_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(10), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    theme_slug: Mapped[str | None] = mapped_column(String(100), index=True)
    title: Mapped[str | None] = mapped_column(String(500))
    grant_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MacroSignal(Base):
    """FRED macro series observations — sector alignment indicators."""
    __tablename__ = "macro_signals"
    __table_args__ = (UniqueConstraint("series_id", "observation_date"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    series_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    series_name: Mapped[str | None] = mapped_column(String(100))
    observation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    value: Mapped[float | None] = mapped_column(Float)
    prev_value: Mapped[float | None] = mapped_column(Float)
    pct_change: Mapped[float | None] = mapped_column(Float)
    theme_relevance: Mapped[list | None] = mapped_column(JSON)  # list of theme slugs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EightKSignal(Base):
    """8-K M&A announcements and AI deal signals from SEC EDGAR."""
    __tablename__ = "eightk_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    accession_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(10), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255))
    filed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    signal_type: Mapped[str | None] = mapped_column(String(50))  # 'ma', 'ai_deal', 'expansion'
    deal_amount: Mapped[float | None] = mapped_column(Float)
    description: Mapped[str | None] = mapped_column(String(1000))
    theme_slugs: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FormDSignal(Base):
    """SEC Form D VC raises — AI ecosystem and early-stage funding signals."""
    __tablename__ = "formd_signals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    accession_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    filed_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    amount_raised: Mapped[float | None] = mapped_column(Float)
    is_ai_related: Mapped[bool] = mapped_column(Boolean, default=False)
    theme_slugs: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
