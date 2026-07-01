# Theme Intelligence Architecture

## Purpose

A continuously-running pipeline that surfaces emerging investment themes before media
consensus forms. It aggregates signals across insider transactions, government contracts,
congressional trades, ETF flows, institutional moves, macro data, and public interest
momentum — scoring each theme 0–100 and computing velocity so users can see whether
a theme is building or fading.

Integrated into the one-stop-finance dashboard under the `/themes` (Theme Intelligence)
route. The sector-monitoring-system is the reference implementation — this is a clean
rebuild scoped to the dashboard's needs.

**Edge over media:** Media covers themes after price moves. This system reads structural
signals (insider clusters, contract awards, ETF inflows) that precede price moves by
2–6 weeks. The synthesis across multiple independent sources is the actual advantage —
no single source alone is actionable.

---

## Clarifications

### 1. Insider Trade Types Included

SEC Form 4 uses transaction codes. We are selective — not all insider transactions
carry signal:

| Code | Type | Include? | Reason |
|------|------|----------|--------|
| P | Open-market purchase | **YES — primary bullish signal** | Real money conviction buy |
| S | Open-market sale | **YES — negative/cooling signal** | Mass selling = theme fading |
| A | Grant / Award | No | Compensation, not conviction |
| M | Option exercise | No | Compensation event |
| M+S | Exercise then immediate sale | No | Compensation liquidation, filter out |
| F | Tax withholding | No | Automatic, not discretionary |
| G | Gift | No | No market conviction |
| D | Disposition | No | Non-market transactions |
| W | Will / Inheritance | No | No market conviction |

Additional EDGAR forms included:

| Form | What it captures | Signal type |
|------|-----------------|-------------|
| 13D | Activist stake > 5% | Strong bullish — someone building a position |
| 13G | Passive stake > 5% | Institutional conviction |
| Form 3 | New insider initial filing | New large stakeholder entering |

**Core rule:** A theme signal requires MULTIPLE DIFFERENT COMPANIES transacting — not
multiple insiders at the same company. 3+ unique companies buying = genuine theme signal.

**Cooling signal:** If 3+ companies in the same theme show insider selling in a 2-week
window, the theme score receives a 30% penalty regardless of buy-side activity.

---

### 2. Data Sources — All Free, No Paid APIs

| Source | Cost | Daily Limit | What It Provides |
|--------|------|-------------|-----------------|
| SEC EDGAR | Free | 10 req/sec | Form 4, 13D/G, 8-K, 13F, Form D |
| USASpending.gov | Free | No limit | Federal contract awards |
| HouseStockWatcher | Free | No limit | House congressional trades |
| SenatStockWatcher | Free | No limit | Senate congressional trades |
| FRED | Free (key required) | No limit | Macro series: rates, output, orders |
| GDELT | Free | No limit | Real-time global news, sentiment-scored |
| pytrends | Free (unofficial) | Soft limits | Google Trends theme keyword velocity |
| NIH Reporter | Free | No limit | Biotech/Genomics grant signals |
| FINRA | Free (flat files) | Bi-monthly release | Short interest per ticker |
| USPTO (PatentsView) | Free | No limit | Patent filing velocity by company |
| yfinance | Free (unofficial) | Soft limits | ETF holdings, supplemental only |
| FMP | Free tier | 250 calls/day | Company profiles for Haiku classification |
| Polygon.io | Free tier | Unlimited REST | EOD options volume (15-min delay) |

**Alpha Vantage excluded** — 25 calls/day free tier is insufficient for any
multi-ticker pipeline. GDELT replaces it for news sentiment (free, no rate limit).

**FMP scoped to classification only** — 250 calls/day used exclusively for the weekly
Claude Haiku theme sync, not real-time polling.

**yfinance marked supplemental** — unofficial scraping, can break. Used only for
ETF constituent warm-up, never on a critical path.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES (ALL FREE)                        │
│                                                                       │
│  SEC EDGAR    USASpending   House/Senate   FRED     GDELT  pytrends  │
│  (Form 4 P+S, (gov          Watcher        (macro   (news  (trend    │
│  13D, 8-K,    contracts)    (congress       data)    events) momentum)│
│  13F, Form D)               trades)                                   │
│                                                                       │
│  NIH Reporter  FINRA        USPTO          Polygon.io   yfinance     │
│  (bio grants)  (short       (patents)      (EOD options  (ETF        │
│                interest)                   volume)       holdings)    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         COLLECTOR LAYER                               │
│                                                                       │
│  insider_collector    congress_collector    contract_collector        │
│  (P buys + S sells    (house + senate       (USASpending +            │
│  + 13D/13G/Form3)     watcher APIs)         SAM.gov awards)          │
│                                                                       │
│  eightk_collector     thirteenf_collector   formd_collector          │
│  (M&A signals,        (institutional        (VC raises,               │
│  AI deals)            13F delta quarterly)  AI ecosystem)            │
│                                                                       │
│  etf_collector        news_collector        macro_collector          │
│  (yfinance holdings   (GDELT events +       (FRED series:            │
│  + Polygon EOD vol)   RSS feeds)            rates, output)           │
│                                                                       │
│  options_collector    short_collector       trend_collector          │
│  (Polygon EOD         (FINRA flat files     (pytrends theme          │
│  unusual volume)      bi-monthly)           keyword velocity)        │
│                                                                       │
│  nih_collector        patent_collector      activist_collector       │
│  (NIH grants by       (USPTO filings by     (13D/G new               │
│  theme keyword)       theme company)        activist stakes)         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      NORMALISATION LAYER                              │
│                                                                       │
│  ticker_to_theme()  ← DB-persisted Haiku classifications (primary)  │
│                     ← Static THEME_TICKER_MAP (curated per theme)   │
│                     ← ETF holdings expansion (yfinance)             │
│                     ← FMP keyword fallback (unknown tickers)        │
│                                                                       │
│  filter_noise()     ← Remove A, F, G, D, W transaction codes       │
│  deduplicate()      ← One record per insider per ticker per day     │
│  normalise_amount() ← USD normalisation across transaction types    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      SIGNAL SCORING ENGINE                            │
│                                                                       │
│  Per-theme inputs:                                                    │
│    unique_companies_buying    — primary score driver                 │
│    unique_companies_selling   — cooling penalty modifier             │
│    csuite_count               — C-suite conviction bonus             │
│    total_usd                  — dollar size bonus                    │
│    congress_boost             — congressional corroboration          │
│    ai_ecosystem_signals       — Form D + 8-K AI deals               │
│    activist_stake_filed       — 13D new filing in theme ticker       │
│    options_anomaly_score      — EOD vol vs 30d avg                  │
│    etf_inflow_score           — volume anomaly vs 30d avg            │
│    short_interest_ratio       — high short + buying = amplifier      │
│    macro_alignment_score      — FRED sector data trending right way  │
│    trend_velocity             — pytrends WoW delta                   │
│    institutional_delta        — new 13F positions this quarter       │
│    gov_contract_count         — contracts awarded to theme (30d)    │
│    nih_grant_count            — Biotech theme only                  │
│    patent_velocity            — USPTO new filings by theme companies │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    VELOCITY & LIFECYCLE ENGINE                        │
│                                                                       │
│  velocity       = score_this_week − score_last_week                 │
│  signal_age_weight → recent signals weighted higher (decay curve)   │
│                                                                       │
│  lifecycle_stage:                                                     │
│    EMERGING  → score < 50,  velocity > +10                          │
│    BUILDING  → score 50-70, velocity > 0                            │
│    PEAK      → score >= 70, |velocity| <= 5                         │
│    FADING    → velocity < -5                                         │
│    COOLING   → insider selling cluster detected (3+ companies)      │
│    STABLE    → all other                                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   SYNTHESIS LAYER (Claude Sonnet)                     │
│                                                                       │
│  Per qualifying theme (score > 45):                                  │
│    • 2-3 sentence plain-language thesis                              │
│    • Which signals are converging and why                            │
│    • Lifecycle stage context                                          │
│    • What confirmation signal to watch next week                     │
│    • Confidence level (signal count based)                           │
│                                                                       │
│  Model: claude-sonnet-4-6 (quality matters for user-facing output)  │
│  Haiku reserved for ticker classification only (high-volume task)   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                 BACKEND API (Express — existing)                      │
│                                                                       │
│  GET  /api/themes              → all themes scored + ranked          │
│  GET  /api/themes/trending     → top 5 by velocity                  │
│  GET  /api/themes/cooling      → themes with negative velocity       │
│  GET  /api/themes/:name        → single theme full breakdown         │
│  GET  /api/themes/:name/history→ 12-week score history              │
│  GET  /api/signals/insider     → raw insider buy/sell feed          │
│  GET  /api/signals/congress    → raw congress trade feed             │
│  GET  /api/signals/contracts   → raw gov contract awards            │
│  POST /api/sync/themes         → trigger Haiku classification sync  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              FRONTEND — /themes (ThemesPage.tsx)                     │
│                                                                       │
│  Theme Grid (score + velocity + lifecycle badge)                     │
│  Theme Detail Drawer (signal breakdown + thesis + watch signals)     │
│  Trending Themes Panel (top 5 by velocity this week)                │
│  Cooling Alert Panel (themes with selling clusters)                  │
│  12-week Score History Chart (per theme)                             │
│  Signal Feed (raw insider/congress/contract events)                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Theme Definitions (25 Total)

### Original 15

| Theme | ETF Proxy | Core Signal Tickers |
|-------|-----------|---------------------|
| Semiconductors | SOXX | NVDA, AMD, ASML, TSM, AMAT, LRCX, KLAC, MU |
| AI Infrastructure | BOTZ | NVDA, MSFT, AMZN, GOOGL, SMCI, ANET, DELL |
| Photonics & Optical | SOXX (proxy) | COHR, VIAV, LITE, MTSI, LPTH, AAOI |
| Cybersecurity | HACK | CRWD, PANW, ZS, OKTA, FTNT, S, CYBR |
| Defense & Aerospace | ITA | LMT, RTX, NOC, GD, BA, KTOS, AVAV, HII |
| Grid & Power Infra | GRID | GEV, ETR, VST, CEG, AMETEK, GE |
| Nuclear Energy | NLR | CEG, CCJ, BWX, SMR, OKLO, LTBR, UEC |
| Clean Energy | ICLN | NEE, ENPH, FSLR, PLUG, BLDP, RUN |
| Biotech & Genomics | ARKG | CRSP, EDIT, BEAM, NTLA, ALNY, ILMN, MRNA |
| Cloud & SaaS | CLOU | MSFT, SNOW, DDOG, NET, NOW, CRM, GTLB |
| EV & Battery Tech | LIT | TSLA, ALB, RIVN, CHPT, MP, LAC, EVGO |
| Space & Satellite | UFO | RKLB, AST, LUNR, PL, IRDM, VSAT |
| Quantum Computing | QTUM | IONQ, RGTI, QUBT, IBM, QBTS, ARQQ |
| Drone & Autonomous | IFLY | AVAV, KTOS, JOBY, RCAT, ACHR, ONDS |
| Fintech & Payments | FINX | V, MA, AFRM, SOFI, COIN, PYPL, HOOD |

### 10 New Themes

| Theme | ETF Proxy | Why Now | Core Signal Tickers |
|-------|-----------|---------|---------------------|
| Humanoid Robotics | ROBO | Tesla Optimus, Figure, 1X capex wave | TSLA, ABB, NVDA, BKNG, TER |
| GLP-1 Supply Chain | LLY/NVO proxy | Ozempic demand outpacing capacity — suppliers & devices moving | NVO, LLY, WST, HIMS, RDUS |
| Critical Minerals | REMX | US-China decoupling forcing domestic rare earth supply | MP, UUUU, NXE, LAC, LTHM |
| AI Data Center Infra | DTCR | Cooling, power delivery, liquid cooling — separate from AI Infrastructure | VRT, NVENT, SMCI, GEV, CDNS |
| Spatial Computing / AR | META proxy | Apple Vision Pro ecosystem + enterprise AR adoption | AAPL, IMMR, MVIS, UNITY |
| Synthetic Biology | No pure ETF | Engineering organisms for materials, food, therapeutics | TWST, DNAY, SRNA |
| Carbon Capture | No pure ETF | IRA funding unlocking investable companies | CTRA, CLMT, XPRT |
| Longevity Biotech | No pure ETF | New funding wave around anti-aging research | UNITY, HLVX, LIFE |
| Water Technology | PHO | Climate scarcity + US infrastructure spend | XYLEM, PNR, AWK, FELE |
| Digital Defense & LEO | No pure ETF | Starshield, GPS alternatives, military LEO comms | RKLB, AST, IRDM, VSAT |

---

## Scoring Model

### Base Score (unique companies buying)

```
6+ companies  →  90
5  companies  →  82
4  companies  →  72
3  companies  →  60   ← genuine theme threshold
2  companies  →  38
1  company    →  18   (low signal, show for visibility)
0  companies  →   0   (AI/macro signals only)
```

### Bonus Stack

```python
bonus = 0.0

# Insider conviction
if csuite_count >= 1:           bonus += 10.0
if total_usd > 5_000_000:       bonus += 8.0
elif total_usd > 1_000_000:     bonus += 4.0
if any_single_buy > 1_000_000:  bonus += 5.0

# Multi-source corroboration
if congress_trades_exist:       bonus += 8.0
if activist_stake_filed:        bonus += 12.0  # 13D — someone building a position

# AI ecosystem (Form D + 8-K AI deals)
if ai_companies >= 3:           bonus += 15.0
elif ai_companies == 2:         bonus += 10.0
elif ai_companies == 1:         bonus += 6.0
if ai_usd >= 1_000_000_000:     bonus += 8.0

# Market signals
if options_vol_ratio >= 2.0:    bonus += 7.0   # options volume > 2x 30d avg
if etf_inflow_anomaly:          bonus += 6.0   # ETF inflow spike
if trend_velocity >= 20:        bonus += 5.0   # Google Trends +20% WoW
if macro_aligned:               bonus += 4.0   # FRED data trending correctly
if gov_contracts >= 3:          bonus += 6.0   # 3+ contracts in theme this month
if short_high and buying:       bonus += 8.0   # high short + insider buying
if institutional_new_pos >= 2:  bonus += 5.0   # 2+ new 13F positions this quarter

final_score = min(100.0, base + bonus)
```

### Cooling Modifier

```python
if selling_companies >= 3:
    final_score *= 0.70     # 30% penalty, stage → COOLING
elif selling_companies == 2:
    final_score *= 0.85     # 15% penalty
```

### Velocity

```python
velocity        = score_this_week - score_last_week   # range: -100 to +100

lifecycle_stage = (
    "EMERGING"  if score < 50  and velocity > 10  else
    "BUILDING"  if score < 70  and velocity > 0   else
    "PEAK"      if score >= 70 and abs(velocity) <= 5 else
    "FADING"    if velocity < -5                   else
    "COOLING"   if selling_cluster_detected        else
    "STABLE"
)
```

---

## Database Schema (New Tables)

```sql
-- Insider sells (mirror of insider_buys)
CREATE TABLE IF NOT EXISTS insider_sells (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker           TEXT NOT NULL,
    company          TEXT,
    insider_name     TEXT,
    insider_role     TEXT,
    amount_usd       REAL,
    shares           INTEGER,
    price_per_share  REAL,
    transaction_date TEXT,
    filed_date       TEXT,
    sector           TEXT,
    source           TEXT DEFAULT 'edgar',
    created_at       TEXT DEFAULT (datetime('now'))
);

-- Theme scores with full signal breakdown per pipeline run
CREATE TABLE IF NOT EXISTS theme_scores_history (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    theme                  TEXT NOT NULL,
    score                  REAL NOT NULL,
    unique_companies_buy   INTEGER DEFAULT 0,
    unique_companies_sell  INTEGER DEFAULT 0,
    total_usd              REAL DEFAULT 0,
    csuite_count           INTEGER DEFAULT 0,
    congress_boost         INTEGER DEFAULT 0,
    ai_signal_count        INTEGER DEFAULT 0,
    options_anomaly        REAL DEFAULT 0,
    trend_velocity         REAL DEFAULT 0,
    gov_contract_count     INTEGER DEFAULT 0,
    short_interest_ratio   REAL DEFAULT 0,
    institutional_delta    INTEGER DEFAULT 0,
    activist_stake         INTEGER DEFAULT 0,
    signal_sources         TEXT,   -- JSON array
    tickers                TEXT,   -- JSON array
    run_date               TEXT NOT NULL,
    created_at             TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_theme_scores_theme_date
    ON theme_scores_history(theme, run_date);

-- Velocity and lifecycle stage per theme per week
CREATE TABLE IF NOT EXISTS theme_velocity (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme           TEXT NOT NULL,
    score           REAL NOT NULL,
    prev_score      REAL,
    velocity        REAL,
    lifecycle_stage TEXT,
    week_start      TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- EOD options volume anomalies per ticker
CREATE TABLE IF NOT EXISTS options_signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    call_volume     INTEGER,
    put_volume      INTEGER,
    total_volume    INTEGER,
    avg_30d_volume  INTEGER,
    anomaly_ratio   REAL,
    signal_date     TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- FINRA short interest (bi-monthly flat file)
CREATE TABLE IF NOT EXISTS short_interest (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    short_interest  INTEGER,
    float_shares    INTEGER,
    short_ratio     REAL,
    settlement_date TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(ticker, settlement_date)
);

-- 13F institutional holdings delta (quarterly)
CREATE TABLE IF NOT EXISTS institutional_holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    institution     TEXT,
    shares_held     INTEGER,
    market_value    REAL,
    is_new_position INTEGER DEFAULT 0,
    quarter         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Google Trends velocity per theme
CREATE TABLE IF NOT EXISTS trend_signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    theme           TEXT NOT NULL,
    keyword         TEXT,
    interest_score  REAL,
    prev_week_score REAL,
    velocity        REAL,
    week_start      TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- Activist stakes from 13D/G filings
CREATE TABLE IF NOT EXISTS activist_stakes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    filer_name      TEXT,
    shares_held     INTEGER,
    pct_of_class    REAL,
    filing_type     TEXT,   -- '13D' or '13G'
    filed_date      TEXT NOT NULL,
    is_new          INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- NIH grants (Biotech & Genomics theme only)
CREATE TABLE IF NOT EXISTS nih_grants (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_title   TEXT,
    fiscal_year     INTEGER,
    total_cost      REAL,
    keywords        TEXT,   -- JSON array
    theme_match     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## Pipeline Schedule

```
Every 15 min (market hours 9:30am–4:00pm ET)
└── news_collector.run()          ← GDELT + RSS sentiment refresh

Every day at 6:00am ET
├── insider_collector.run()       ← Form 4 P buys + S sells (prior 2 days)
├── activist_collector.run()      ← 13D/G new filings
├── contract_collector.run()      ← USASpending new awards
├── congress_collector.run()      ← House/Senate watcher new disclosures
├── etf_collector.run()           ← ETF volume anomaly (yfinance)
├── options_collector.run()       ← Polygon EOD options volume
├── macro_collector.run()         ← FRED updated series
├── trend_collector.run()         ← pytrends weekly refresh
├── theme_agent.score()           ← Recalculate all 25 theme scores
├── velocity_agent.compute()      ← WoW deltas + lifecycle stages
└── theme_synthesiser.run()       ← Claude Sonnet synthesis for score > 45

Every week (Sunday 2:00am ET)
├── eightk_collector.run()        ← 8-K M&A + AI deal scan (7-day window)
└── theme_classifier.sync()       ← Haiku re-classify new unknown tickers

Every 2 weeks (FINRA release: 1st and 15th of month)
└── short_collector.run()         ← FINRA short interest flat file

Every quarter (Feb/May/Aug/Nov, first Monday)
├── thirteenf_collector.run()     ← 13F institutional holdings delta
├── nih_collector.run()           ← NIH grant keyword scan
└── patent_collector.run()        ← USPTO patent velocity
```

---

## Google Trends Keyword Map

```python
THEME_TREND_KEYWORDS = {
    "Semiconductors":           ["semiconductor stocks", "chip stocks"],
    "AI Infrastructure":        ["AI infrastructure stocks", "data center stocks"],
    "Humanoid Robotics":        ["humanoid robot stocks", "robot ETF"],
    "GLP-1 Supply Chain":       ["GLP-1 stocks", "Ozempic stocks", "obesity drug stocks"],
    "Nuclear Energy":           ["nuclear energy stocks", "SMR stocks"],
    "Quantum Computing":        ["quantum computing stocks", "quantum ETF"],
    "Spatial Computing / AR":   ["spatial computing stocks", "AR glasses stocks"],
    "Critical Minerals":        ["rare earth stocks", "critical minerals ETF"],
    "Water Technology":         ["water stocks", "water scarcity investment"],
    "Carbon Capture":           ["carbon capture stocks", "climate tech investment"],
    "Cybersecurity":            ["cybersecurity stocks", "cyber ETF"],
    "Defense & Aerospace":      ["defense stocks", "aerospace ETF"],
    "Biotech & Genomics":       ["biotech stocks", "CRISPR stocks"],
    "EV & Battery Tech":        ["EV stocks", "battery stocks", "lithium stocks"],
    "Space & Satellite":        ["space stocks", "satellite internet stocks"],
}
```

---

## Frontend Components (ThemesPage.tsx)

```
ThemesPage
├── TrendingThemesPanel       — top 5 by velocity this week (EMERGING/BUILDING)
├── CoolingAlertsPanel        — themes with selling clusters or negative velocity
├── ThemeGrid
│   └── ThemeCard (× 25)
│       ├── Score gauge (0-100)
│       ├── Velocity badge (+12 / -5)
│       ├── Lifecycle chip (EMERGING / BUILDING / PEAK / FADING / COOLING)
│       └── Top 3 signal sources (icons)
├── ThemeDetailDrawer (on card click)
│   ├── Signal breakdown (insider, congress, contracts, options, trends)
│   ├── Plain-language thesis (Claude Sonnet output)
│   ├── Watch signal for next week
│   ├── Buying tickers list
│   └── 12-week score history chart
└── SignalFeed
    ├── Latest insider buys/sells
    ├── Latest congress trades
    └── Latest gov contract awards
```

---

## API Response Schema

### GET /api/themes

```json
{
  "generated_at": "2026-06-10T06:00:00Z",
  "themes": [
    {
      "name": "Semiconductors",
      "score": 84,
      "velocity": 12,
      "lifecycle_stage": "BUILDING",
      "unique_companies_buying": 5,
      "unique_companies_selling": 0,
      "total_usd": 8200000,
      "csuite_count": 3,
      "congress_boost": true,
      "activist_stake": false,
      "signal_sources": ["insider_buys", "congress", "etf_inflow", "options_anomaly"],
      "tickers": ["NVDA", "AMD", "AMAT", "MRVL", "ON"],
      "thesis": "Five semiconductor companies saw C-suite open-market purchases totalling $8.2M this week, corroborated by two congressional buys and a 2.4x options volume spike.",
      "watch_for": "ASML earnings guidance next week — upside would confirm the theme.",
      "confidence": "high"
    }
  ]
}
```

---

## Environment Variables Required

```bash
# Existing (already in .env)
ANTHROPIC_API_KEY=      # Claude Haiku (classification) + Sonnet (synthesis)
EDGAR_USER_AGENT=       # "Your Name your@email.com" — SEC requirement
FMP_KEY=                # 250 free calls/day — batch Haiku classification only

# New (free keys, instant signup)
FRED_API_KEY=           # fred.stlouisfed.org — macro data
POLYGON_API_KEY=        # polygon.io — EOD options volume (free tier)

# No key needed at all
# USASpending.gov, HouseStockWatcher, SenatStockWatcher,
# GDELT, NIH Reporter, FINRA, pytrends, USPTO PatentsView
```

---

## Key Design Decisions

**SQLite over PostgreSQL** — single-process pipeline, no concurrent writes. SQLite at
this scale (< 1M rows per table) is faster for sequential single-process writes and
requires zero infrastructure.

**Separate insider_sells table** — keeps existing insider_buys queries unchanged. Sells
are a different signal type: queried separately, applied as a cooling modifier, never
mixed with buys in the same score calculation.

**Sonnet for synthesis, Haiku for classification** — classification is high-volume
batch (hundreds of tickers weekly, ~$0.01 per sync). Synthesis is low-volume
user-facing (25 themes once daily) where reasoning quality directly affects user trust.

**GDELT over Alpha Vantage** — Alpha Vantage's 25 calls/day free tier is unusable for
any multi-ticker pipeline. GDELT processes global news with no rate limit, 15-minute
cadence, and entity tagging built in.

**Velocity as a first-class output** — a static score tells users where a theme is.
Velocity tells them whether to act now or wait. The EMERGING stage (low score, rising
fast) is often more actionable than PEAK (high score, slowing).

---

## Honest Gaps

| Gap | Why | Workaround |
|-----|-----|------------|
| Real-time options sweeps | Requires Unusual Whales ~$50/mo | EOD Polygon volume anomaly as proxy |
| Real-time short interest | FINRA is bi-monthly, Ortex is paid | FINRA + price divergence as proxy |
| International insider filings | Non-US exchanges have different systems | US-listed ADRs caught via EDGAR |
| Congressional trade real-time | 45-day disclosure lag is federal law | Treat as corroboration, not lead signal |
| Alternative data (satellite, credit card) | All paid | Not needed for theme-level scoring |
