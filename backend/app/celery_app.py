from celery import Celery
from app.config import settings

celery = Celery(
    "osf",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.market_indices",
        "app.workers.insider_data",
        "app.workers.congress_data",
        "app.workers.contracts_data",
        "app.workers.options_data",
        "app.workers.sentiment",
        "app.workers.theme_intelligence",   # includes run_pipeline
        "app.workers.trend_signals",
        "app.workers.realtime_push",
        "app.workers.sec_activist",
        "app.workers.sec_13f",
        "app.workers.sec_8k",
        "app.workers.short_interest",
        "app.workers.nih_grants",
        "app.workers.patents",
        "app.workers.macro_data",
        "app.workers.sec_formd",
        "app.workers.synthesis",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/New_York",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

celery.conf.beat_schedule = {
    # Market indices — every 30s
    "fetch-market-indices": {
        "task": "app.workers.market_indices.fetch",
        "schedule": 30.0,
    },
    # EDGAR Form 4 insider filings — every 15 min
    "poll-sec-edgar": {
        "task": "app.workers.insider_data.poll_sec_edgar",
        "schedule": 900.0,
    },
    # Congressional trades — daily (disclosures trickle in slowly)
    "fetch-congress-trades": {
        "task": "app.workers.congress_data.fetch_congress_trades",
        "schedule": 86_400.0,   # 24 hours
    },
    # Government contracts — daily
    "fetch-gov-contracts": {
        "task": "app.workers.contracts_data.fetch_gov_contracts",
        "schedule": 86_400.0,   # 24 hours
    },
    # Unusual options — every 60s
    "cache-unusual-options": {
        "task": "app.workers.options_data.cache_unusual",
        "schedule": 60.0,
    },
    # News sentiment — every 3 min
    "fetch-and-score-sentiment": {
        "task": "app.workers.sentiment.fetch_and_score",
        "schedule": 180.0,
    },
    # Theme intelligence scoring — every 15 min
    "score-all-themes": {
        "task": "app.workers.theme_intelligence.score_all_themes",
        "schedule": 900.0,
    },
    # Google Trends velocity — weekly (pytrends has soft rate limits)
    "sync-trends": {
        "task": "app.workers.theme_intelligence.sync_trends",
        "schedule": 604_800.0,  # 7 days
    },
    # ETF holdings expansion — weekly
    "sync-etf": {
        "task": "app.workers.theme_intelligence.sync_etf",
        "schedule": 604_800.0,  # 7 days
    },
    # Polygon EOD options volume — daily
    "sync-polygon": {
        "task": "app.workers.theme_intelligence.sync_polygon",
        "schedule": 86_400.0,  # 24 hours
    },
    # Theme-ETF flow + options snapshot — daily (yfinance, no API key needed)
    "sync-etf-signals": {
        "task": "app.workers.theme_intelligence.sync_etf_signals",
        "schedule": 86_400.0,  # 24 hours
    },
    # FMP ticker classification — weekly (250 calls/day limit)
    "sync-fmp": {
        "task": "app.workers.theme_intelligence.sync_fmp",
        "schedule": 604_800.0,  # 7 days
    },
    # 13D/G activist stakes — daily (EDGAR, free)
    "fetch-activist-stakes": {
        "task": "app.workers.sec_activist.fetch_activist_stakes",
        "schedule": 86_400.0,  # 24 hours
    },
    # 13F institutional holdings — quarterly (EDGAR, free)
    "fetch-institutional-holdings": {
        "task": "app.workers.sec_13f.fetch_institutional_holdings",
        "schedule": 7_776_000.0,  # 90 days
    },
    # 8-K M&A + AI deal signals — weekly (EDGAR, free)
    "fetch-8k-signals": {
        "task": "app.workers.sec_8k.fetch_8k_signals",
        "schedule": 604_800.0,  # 7 days
    },
    # FINRA short interest — every 2 weeks (bi-monthly flat file release)
    "fetch-short-interest": {
        "task": "app.workers.short_interest.fetch_short_interest",
        "schedule": 1_209_600.0,  # 14 days
    },
    # NIH grants — quarterly (Biotech theme only)
    "fetch-nih-grants": {
        "task": "app.workers.nih_grants.fetch_nih_grants",
        "schedule": 7_776_000.0,  # 90 days
    },
    # USPTO patent signals — quarterly
    "fetch-patent-signals": {
        "task": "app.workers.patents.fetch_patent_signals",
        "schedule": 7_776_000.0,  # 90 days
    },
    # FRED macro data — daily (requires FRED_API_KEY)
    "fetch-macro-data": {
        "task": "app.workers.macro_data.fetch_macro_data",
        "schedule": 86_400.0,  # 24 hours
    },
    # Form D VC raises / AI ecosystem — weekly (EDGAR, free)
    "fetch-formd-signals": {
        "task": "app.workers.sec_formd.fetch_formd_signals",
        "schedule": 604_800.0,  # 7 days
    },
    # Claude Sonnet synthesis — daily for themes scoring > 45
    "synthesize-themes": {
        "task": "app.workers.synthesis.synthesize_themes",
        "schedule": 86_400.0,  # 24 hours
    },
    # Trend reversal signals — every 15 min
    "scan-trend-signals": {
        "task": "app.workers.trend_signals.scan",
        "schedule": 900.0,
    },
    # Real-time quote push — every 15s
    "push-realtime-quotes": {
        "task": "app.workers.realtime_push.push_quotes",
        "schedule": 15.0,
    },
}
