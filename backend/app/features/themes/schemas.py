from datetime import datetime
from typing import Literal
from pydantic import BaseModel

SyncSourceKey = Literal["fmp", "trends", "polygon", "etf", "etf_signals"]


# ---------------------------------------------------------------------------
# Sync schemas (existing)
# ---------------------------------------------------------------------------

class SyncSourceStatus(BaseModel):
    source: SyncSourceKey
    label: str
    description: str
    status: Literal["idle", "running", "error"]
    last_synced_at: str | None
    is_stale: bool
    stale_after_hours: int
    error: str | None


class SyncStatusResponse(BaseModel):
    sources: list[SyncSourceStatus]


class SyncTriggerRequest(BaseModel):
    source: SyncSourceKey | Literal["all"]


class SyncTriggerResponse(BaseModel):
    triggered: list[SyncSourceKey]
    skipped: list[SyncSourceKey]


# ---------------------------------------------------------------------------
# Theme schemas
# ---------------------------------------------------------------------------

class TickerOut(BaseModel):
    symbol: str
    company_name: str | None
    market_cap_tier: str | None


class SignalBreakdown(BaseModel):
    buying_tickers: list[str]
    selling_tickers: list[str]
    total_usd: float
    large_buys_count: int
    congress_tickers: list[str]
    contracts_count: int


class ThemeScoreOut(BaseModel):
    score: float
    level: str
    velocity: float | None
    lifecycle_stage: str | None
    unique_companies_buying: int
    unique_companies_selling: int
    total_value_accumulated: float
    csuite_count: int
    congress_signal: bool
    sentiment_signal: bool
    unusual_options_count: int
    contracts_count: int
    trend_velocity: float | None
    options_anomaly: float | None
    signal_breakdown: dict | None
    scored_at: datetime | None
    # Synthesis (filled daily by synthesis worker for score > 45)
    thesis: str | None = None
    watch_for: str | None = None
    confidence: str | None = None
    synthesized_at: datetime | None = None


class ThemeOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    category: str | None
    benchmark_etf: str | None
    score: ThemeScoreOut | None
    top_tickers: list[str]


class ThemeDetailOut(ThemeOut):
    tickers: list[TickerOut]
    history: list["HistoryPoint"]


class HistoryPoint(BaseModel):
    scored_at: datetime
    score: float
    velocity: float | None
    lifecycle_stage: str | None


class ThemeListResponse(BaseModel):
    themes: list[ThemeOut]
    last_scored_at: datetime | None


class InsiderSignalOut(BaseModel):
    symbol: str
    issuer_name: str | None
    insider_name: str
    insider_title: str | None
    transaction_type: str
    total_value: float | None
    is_congress: bool
    filing_date: datetime


class ContractSignalOut(BaseModel):
    recipient_name: str | None
    symbol: str | None
    award_amount: float | None
    agency_name: str | None
    description: str | None
    award_date: datetime | None
    theme_id: str | None


# ---------------------------------------------------------------------------
# Watchlist schemas
# ---------------------------------------------------------------------------

class WatchlistItem(BaseModel):
    theme_id: str
    slug: str
    name: str
    added_at: datetime


class WatchlistResponse(BaseModel):
    items: list[WatchlistItem]


class WatchlistAddResponse(BaseModel):
    theme_id: str
    slug: str
    added: bool  # False if already watching
