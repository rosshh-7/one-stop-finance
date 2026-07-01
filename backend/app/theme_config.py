"""
Theme Intelligence configuration — 25 cross-GICS themes.

Each theme has:
  - name / slug / description / category / benchmark_etf
  - tickers: list of {symbol, company_name, market_cap_tier}

THEME_ETF_MAP   → theme name → ETF ticker (for volume anomaly detection)
THEME_TREND_KEYWORDS → theme name → Google Trends search terms
"""

from typing import TypedDict


class TickerEntry(TypedDict):
    symbol: str
    company_name: str
    market_cap_tier: str  # large | mid | small | micro


class ThemeEntry(TypedDict):
    name: str
    slug: str
    description: str
    category: str
    benchmark_etf: str
    tickers: list[TickerEntry]


THEME_CONFIG: list[ThemeEntry] = [
    {
        "name": "Semiconductors",
        "slug": "semiconductors",
        "description": "Chip designers, fabs, and equipment makers driving modern computing",
        "category": "Technology",
        "benchmark_etf": "SOXX",
        "tickers": [
            {"symbol": "NVDA",  "company_name": "NVIDIA",                   "market_cap_tier": "large"},
            {"symbol": "AMD",   "company_name": "Advanced Micro Devices",   "market_cap_tier": "large"},
            {"symbol": "INTC",  "company_name": "Intel",                    "market_cap_tier": "large"},
            {"symbol": "TSM",   "company_name": "Taiwan Semiconductor",     "market_cap_tier": "large"},
            {"symbol": "ASML",  "company_name": "ASML Holding",             "market_cap_tier": "large"},
            {"symbol": "QCOM",  "company_name": "Qualcomm",                 "market_cap_tier": "large"},
            {"symbol": "AVGO",  "company_name": "Broadcom",                 "market_cap_tier": "large"},
            {"symbol": "AMAT",  "company_name": "Applied Materials",        "market_cap_tier": "large"},
            {"symbol": "LRCX",  "company_name": "Lam Research",             "market_cap_tier": "large"},
            {"symbol": "KLAC",  "company_name": "KLA Corporation",          "market_cap_tier": "large"},
            {"symbol": "MU",    "company_name": "Micron Technology",        "market_cap_tier": "large"},
            {"symbol": "MRVL",  "company_name": "Marvell Technology",       "market_cap_tier": "mid"},
            {"symbol": "ON",    "company_name": "ON Semiconductor",         "market_cap_tier": "mid"},
            {"symbol": "MPWR",  "company_name": "Monolithic Power Systems", "market_cap_tier": "mid"},
            {"symbol": "WOLF",  "company_name": "Wolfspeed",                "market_cap_tier": "mid"},
            {"symbol": "ACLS",  "company_name": "Axcelis Technologies",     "market_cap_tier": "small"},
            {"symbol": "ONTO",  "company_name": "Onto Innovation",          "market_cap_tier": "small"},
            {"symbol": "AEHR",  "company_name": "Aehr Test Systems",        "market_cap_tier": "small"},
        ],
    },
    {
        "name": "AI Infrastructure",
        "slug": "ai-infrastructure",
        "description": "Hardware, software and platforms powering AI model training and inference",
        "category": "Technology",
        "benchmark_etf": "BOTZ",
        "tickers": [
            {"symbol": "NVDA",  "company_name": "NVIDIA",               "market_cap_tier": "large"},
            {"symbol": "MSFT",  "company_name": "Microsoft",            "market_cap_tier": "large"},
            {"symbol": "AMZN",  "company_name": "Amazon",               "market_cap_tier": "large"},
            {"symbol": "GOOGL", "company_name": "Alphabet",             "market_cap_tier": "large"},
            {"symbol": "META",  "company_name": "Meta Platforms",       "market_cap_tier": "large"},
            {"symbol": "IBM",   "company_name": "IBM",                  "market_cap_tier": "large"},
            {"symbol": "ORCL",  "company_name": "Oracle",               "market_cap_tier": "large"},
            {"symbol": "SMCI",  "company_name": "Super Micro Computer", "market_cap_tier": "mid"},
            {"symbol": "ANET",  "company_name": "Arista Networks",      "market_cap_tier": "mid"},
            {"symbol": "DELL",  "company_name": "Dell Technologies",    "market_cap_tier": "large"},
            {"symbol": "AI",    "company_name": "C3.ai",                "market_cap_tier": "small"},
            {"symbol": "BBAI",  "company_name": "BigBear.ai",           "market_cap_tier": "small"},
        ],
    },
    {
        "name": "AI Data Center Infrastructure",
        "slug": "ai-datacenter-infra",
        "description": "Cooling, power delivery and physical infrastructure for AI data centers",
        "category": "Technology",
        "benchmark_etf": "DTCR",
        "tickers": [
            {"symbol": "VRT",   "company_name": "Vertiv Holdings",      "market_cap_tier": "large"},
            {"symbol": "SMCI",  "company_name": "Super Micro Computer", "market_cap_tier": "mid"},
            {"symbol": "GEV",   "company_name": "GE Vernova",           "market_cap_tier": "large"},
            {"symbol": "NVENT", "company_name": "nVent Electric",       "market_cap_tier": "mid"},
            {"symbol": "CDNS",  "company_name": "Cadence Design",       "market_cap_tier": "large"},
            {"symbol": "EATON", "company_name": "Eaton Corporation",    "market_cap_tier": "large"},
            {"symbol": "CARR",  "company_name": "Carrier Global",       "market_cap_tier": "large"},
        ],
    },
    {
        "name": "Cybersecurity",
        "slug": "cybersecurity",
        "description": "Network, endpoint and cloud security platforms protecting digital infrastructure",
        "category": "Technology",
        "benchmark_etf": "HACK",
        "tickers": [
            {"symbol": "CRWD",  "company_name": "CrowdStrike",   "market_cap_tier": "large"},
            {"symbol": "PANW",  "company_name": "Palo Alto Networks", "market_cap_tier": "large"},
            {"symbol": "FTNT",  "company_name": "Fortinet",      "market_cap_tier": "large"},
            {"symbol": "ZS",    "company_name": "Zscaler",       "market_cap_tier": "large"},
            {"symbol": "OKTA",  "company_name": "Okta",          "market_cap_tier": "mid"},
            {"symbol": "S",     "company_name": "SentinelOne",   "market_cap_tier": "mid"},
            {"symbol": "CYBR",  "company_name": "CyberArk",      "market_cap_tier": "mid"},
            {"symbol": "TENB",  "company_name": "Tenable Holdings", "market_cap_tier": "small"},
            {"symbol": "QLYS",  "company_name": "Qualys",        "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Cloud & SaaS",
        "slug": "cloud-saas",
        "description": "Cloud platforms and subscription software reshaping enterprise IT",
        "category": "Technology",
        "benchmark_etf": "CLOU",
        "tickers": [
            {"symbol": "MSFT",  "company_name": "Microsoft",     "market_cap_tier": "large"},
            {"symbol": "AMZN",  "company_name": "Amazon",        "market_cap_tier": "large"},
            {"symbol": "GOOGL", "company_name": "Alphabet",      "market_cap_tier": "large"},
            {"symbol": "CRM",   "company_name": "Salesforce",    "market_cap_tier": "large"},
            {"symbol": "NOW",   "company_name": "ServiceNow",    "market_cap_tier": "large"},
            {"symbol": "SNOW",  "company_name": "Snowflake",     "market_cap_tier": "mid"},
            {"symbol": "DDOG",  "company_name": "Datadog",       "market_cap_tier": "mid"},
            {"symbol": "NET",   "company_name": "Cloudflare",    "market_cap_tier": "mid"},
            {"symbol": "MDB",   "company_name": "MongoDB",       "market_cap_tier": "mid"},
            {"symbol": "GTLB",  "company_name": "GitLab",        "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Defense & Aerospace",
        "slug": "defense-aerospace",
        "description": "Defense contractors, weapons systems, and aerospace technology",
        "category": "Industrials",
        "benchmark_etf": "ITA",
        "tickers": [
            {"symbol": "LMT",   "company_name": "Lockheed Martin",  "market_cap_tier": "large"},
            {"symbol": "RTX",   "company_name": "RTX Corporation",  "market_cap_tier": "large"},
            {"symbol": "NOC",   "company_name": "Northrop Grumman", "market_cap_tier": "large"},
            {"symbol": "GD",    "company_name": "General Dynamics", "market_cap_tier": "large"},
            {"symbol": "BA",    "company_name": "Boeing",           "market_cap_tier": "large"},
            {"symbol": "LHX",   "company_name": "L3Harris Technologies", "market_cap_tier": "large"},
            {"symbol": "HII",   "company_name": "Huntington Ingalls", "market_cap_tier": "mid"},
            {"symbol": "KTOS",  "company_name": "Kratos Defense",   "market_cap_tier": "small"},
            {"symbol": "AVAV",  "company_name": "AeroVironment",    "market_cap_tier": "small"},
            {"symbol": "AXON",  "company_name": "Axon Enterprise",  "market_cap_tier": "mid"},
        ],
    },
    {
        "name": "Grid & Power Infrastructure",
        "slug": "grid-power-infra",
        "description": "Electric grid modernisation, power electronics and energy transmission",
        "category": "Utilities",
        "benchmark_etf": "GRID",
        "tickers": [
            {"symbol": "GEV",    "company_name": "GE Vernova",       "market_cap_tier": "large"},
            {"symbol": "ETR",    "company_name": "Entergy",          "market_cap_tier": "large"},
            {"symbol": "VST",    "company_name": "Vistra",           "market_cap_tier": "large"},
            {"symbol": "CEG",    "company_name": "Constellation Energy", "market_cap_tier": "large"},
            {"symbol": "NEE",    "company_name": "NextEra Energy",   "market_cap_tier": "large"},
            {"symbol": "AMETEK", "company_name": "Ametek",           "market_cap_tier": "mid"},
            {"symbol": "SHLS",   "company_name": "Shoals Technologies", "market_cap_tier": "small"},
            {"symbol": "STEM",   "company_name": "Stem Inc",         "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Nuclear Energy",
        "slug": "nuclear-energy",
        "description": "Uranium miners, nuclear utilities and small modular reactor developers",
        "category": "Energy",
        "benchmark_etf": "NLR",
        "tickers": [
            {"symbol": "CEG",   "company_name": "Constellation Energy", "market_cap_tier": "large"},
            {"symbol": "VST",   "company_name": "Vistra",           "market_cap_tier": "large"},
            {"symbol": "CCJ",   "company_name": "Cameco",           "market_cap_tier": "mid"},
            {"symbol": "BWX",   "company_name": "BWX Technologies", "market_cap_tier": "mid"},
            {"symbol": "SMR",   "company_name": "NuScale Power",    "market_cap_tier": "small"},
            {"symbol": "OKLO",  "company_name": "Oklo",             "market_cap_tier": "small"},
            {"symbol": "UEC",   "company_name": "Uranium Energy Corp", "market_cap_tier": "small"},
            {"symbol": "NXE",   "company_name": "NexGen Energy",    "market_cap_tier": "small"},
            {"symbol": "LTBR",  "company_name": "Lightbridge",      "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Clean Energy",
        "slug": "clean-energy",
        "description": "Solar, wind, hydrogen and other renewable energy technologies",
        "category": "Energy",
        "benchmark_etf": "ICLN",
        "tickers": [
            {"symbol": "NEE",   "company_name": "NextEra Energy",   "market_cap_tier": "large"},
            {"symbol": "ENPH",  "company_name": "Enphase Energy",   "market_cap_tier": "mid"},
            {"symbol": "FSLR",  "company_name": "First Solar",      "market_cap_tier": "mid"},
            {"symbol": "RUN",   "company_name": "Sunrun",           "market_cap_tier": "mid"},
            {"symbol": "PLUG",  "company_name": "Plug Power",       "market_cap_tier": "small"},
            {"symbol": "BLDP",  "company_name": "Ballard Power",    "market_cap_tier": "small"},
            {"symbol": "ARRY",  "company_name": "Array Technologies", "market_cap_tier": "small"},
            {"symbol": "CLNE",  "company_name": "Clean Energy Fuels", "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Biotech & Genomics",
        "slug": "biotech-genomics",
        "description": "Gene editing, mRNA therapeutics, and precision medicine platforms",
        "category": "Healthcare",
        "benchmark_etf": "ARKG",
        "tickers": [
            {"symbol": "MRNA",  "company_name": "Moderna",              "market_cap_tier": "large"},
            {"symbol": "REGN",  "company_name": "Regeneron",            "market_cap_tier": "large"},
            {"symbol": "VRTX",  "company_name": "Vertex Pharmaceuticals", "market_cap_tier": "large"},
            {"symbol": "ILMN",  "company_name": "Illumina",             "market_cap_tier": "large"},
            {"symbol": "CRSP",  "company_name": "CRISPR Therapeutics",  "market_cap_tier": "mid"},
            {"symbol": "EDIT",  "company_name": "Editas Medicine",      "market_cap_tier": "small"},
            {"symbol": "BEAM",  "company_name": "Beam Therapeutics",    "market_cap_tier": "small"},
            {"symbol": "NTLA",  "company_name": "Intellia Therapeutics", "market_cap_tier": "small"},
            {"symbol": "ALNY",  "company_name": "Alnylam Pharmaceuticals", "market_cap_tier": "mid"},
            {"symbol": "RXRX",  "company_name": "Recursion Pharma",     "market_cap_tier": "small"},
        ],
    },
    {
        "name": "EV & Battery Tech",
        "slug": "ev-battery-tech",
        "description": "Electric vehicles, lithium mining, charging infrastructure and battery technology",
        "category": "Consumer",
        "benchmark_etf": "LIT",
        "tickers": [
            {"symbol": "TSLA",  "company_name": "Tesla",             "market_cap_tier": "large"},
            {"symbol": "GM",    "company_name": "General Motors",    "market_cap_tier": "large"},
            {"symbol": "F",     "company_name": "Ford Motor",        "market_cap_tier": "large"},
            {"symbol": "RIVN",  "company_name": "Rivian Automotive", "market_cap_tier": "mid"},
            {"symbol": "ALB",   "company_name": "Albemarle",         "market_cap_tier": "mid"},
            {"symbol": "MP",    "company_name": "MP Materials",      "market_cap_tier": "mid"},
            {"symbol": "CHPT",  "company_name": "ChargePoint",       "market_cap_tier": "small"},
            {"symbol": "EVGO",  "company_name": "EVgo",              "market_cap_tier": "small"},
            {"symbol": "LAC",   "company_name": "Lithium Americas",  "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Space & Satellite",
        "slug": "space-satellite",
        "description": "Launch vehicles, satellite constellations and earth observation platforms",
        "category": "Industrials",
        "benchmark_etf": "UFO",
        "tickers": [
            {"symbol": "RKLB",  "company_name": "Rocket Lab",        "market_cap_tier": "small"},
            {"symbol": "AST",   "company_name": "AST SpaceMobile",   "market_cap_tier": "small"},
            {"symbol": "LUNR",  "company_name": "Intuitive Machines", "market_cap_tier": "small"},
            {"symbol": "PL",    "company_name": "Planet Labs",        "market_cap_tier": "small"},
            {"symbol": "IRDM",  "company_name": "Iridium Communications", "market_cap_tier": "mid"},
            {"symbol": "VSAT",  "company_name": "Viasat",             "market_cap_tier": "mid"},
            {"symbol": "SPIR",  "company_name": "Spire Global",       "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Quantum Computing",
        "slug": "quantum-computing",
        "description": "Trapped-ion, superconducting and photonic quantum computing hardware and software",
        "category": "Technology",
        "benchmark_etf": "QTUM",
        "tickers": [
            {"symbol": "IBM",   "company_name": "IBM",               "market_cap_tier": "large"},
            {"symbol": "GOOGL", "company_name": "Alphabet",          "market_cap_tier": "large"},
            {"symbol": "MSFT",  "company_name": "Microsoft",         "market_cap_tier": "large"},
            {"symbol": "IONQ",  "company_name": "IonQ",              "market_cap_tier": "small"},
            {"symbol": "RGTI",  "company_name": "Rigetti Computing",  "market_cap_tier": "micro"},
            {"symbol": "QUBT",  "company_name": "Quantum Computing Inc", "market_cap_tier": "micro"},
            {"symbol": "QBTS",  "company_name": "D-Wave Quantum",    "market_cap_tier": "micro"},
            {"symbol": "ARQQ",  "company_name": "Arqit Quantum",     "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Drone & Autonomous Systems",
        "slug": "drone-autonomous",
        "description": "Military and commercial drones, eVTOL air taxis and autonomous ground vehicles",
        "category": "Industrials",
        "benchmark_etf": "IFLY",
        "tickers": [
            {"symbol": "AVAV",  "company_name": "AeroVironment",     "market_cap_tier": "small"},
            {"symbol": "KTOS",  "company_name": "Kratos Defense",    "market_cap_tier": "small"},
            {"symbol": "JOBY",  "company_name": "Joby Aviation",     "market_cap_tier": "small"},
            {"symbol": "ACHR",  "company_name": "Archer Aviation",   "market_cap_tier": "small"},
            {"symbol": "RCAT",  "company_name": "Red Cat Holdings",  "market_cap_tier": "micro"},
            {"symbol": "ONDS",  "company_name": "Ondas Holdings",    "market_cap_tier": "micro"},
            {"symbol": "UAVS",  "company_name": "AgEagle Aerial",    "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Fintech & Payments",
        "slug": "fintech-payments",
        "description": "Digital payments, neobanks, BNPL and blockchain financial infrastructure",
        "category": "Financials",
        "benchmark_etf": "FINX",
        "tickers": [
            {"symbol": "V",     "company_name": "Visa",              "market_cap_tier": "large"},
            {"symbol": "MA",    "company_name": "Mastercard",        "market_cap_tier": "large"},
            {"symbol": "PYPL",  "company_name": "PayPal",            "market_cap_tier": "large"},
            {"symbol": "SQ",    "company_name": "Block",             "market_cap_tier": "mid"},
            {"symbol": "AFRM",  "company_name": "Affirm Holdings",   "market_cap_tier": "mid"},
            {"symbol": "SOFI",  "company_name": "SoFi Technologies", "market_cap_tier": "small"},
            {"symbol": "COIN",  "company_name": "Coinbase",          "market_cap_tier": "mid"},
            {"symbol": "HOOD",  "company_name": "Robinhood",         "market_cap_tier": "small"},
            {"symbol": "UPST",  "company_name": "Upstart Holdings",  "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Photonics & Optical",
        "slug": "photonics-optical",
        "description": "Fiber optics, coherent transmission, LiDAR and photonic integrated circuits",
        "category": "Technology",
        "benchmark_etf": "SOXX",
        "tickers": [
            {"symbol": "COHR",  "company_name": "Coherent Corp",     "market_cap_tier": "large"},
            {"symbol": "VIAV",  "company_name": "Viavi Solutions",   "market_cap_tier": "mid"},
            {"symbol": "MTSI",  "company_name": "MACOM Technology",  "market_cap_tier": "mid"},
            {"symbol": "LITE",  "company_name": "Lumentum Holdings", "market_cap_tier": "mid"},
            {"symbol": "AAOI",  "company_name": "Applied Optoelectronics", "market_cap_tier": "small"},
            {"symbol": "LPTH",  "company_name": "LightPath Technologies", "market_cap_tier": "micro"},
            {"symbol": "CLFD",  "company_name": "Clearfield",        "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Humanoid Robotics",
        "slug": "humanoid-robotics",
        "description": "Humanoid and industrial robots, actuators and AI motion control systems",
        "category": "Technology",
        "benchmark_etf": "ROBO",
        "tickers": [
            {"symbol": "TSLA",  "company_name": "Tesla (Optimus)",   "market_cap_tier": "large"},
            {"symbol": "ABB",   "company_name": "ABB Ltd",           "market_cap_tier": "large"},
            {"symbol": "TER",   "company_name": "Teradyne",          "market_cap_tier": "mid"},
            {"symbol": "ISRG",  "company_name": "Intuitive Surgical", "market_cap_tier": "large"},
            {"symbol": "NVDA",  "company_name": "NVIDIA (motion AI)", "market_cap_tier": "large"},
            {"symbol": "BRSH",  "company_name": "Bruush Oral Care",  "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "GLP-1 Supply Chain",
        "slug": "glp1-supply-chain",
        "description": "Ozempic and Wegovy supply chain — manufacturers, device makers, and CDMO beneficiaries",
        "category": "Healthcare",
        "benchmark_etf": "XLV",
        "tickers": [
            {"symbol": "NVO",   "company_name": "Novo Nordisk",      "market_cap_tier": "large"},
            {"symbol": "LLY",   "company_name": "Eli Lilly",         "market_cap_tier": "large"},
            {"symbol": "WST",   "company_name": "West Pharmaceutical", "market_cap_tier": "mid"},
            {"symbol": "HIMS",  "company_name": "Hims & Hers",       "market_cap_tier": "small"},
            {"symbol": "RDUS",  "company_name": "Radius Health",     "market_cap_tier": "small"},
            {"symbol": "AMGN",  "company_name": "Amgen",             "market_cap_tier": "large"},
        ],
    },
    {
        "name": "Critical Minerals & Rare Earth",
        "slug": "critical-minerals",
        "description": "Domestic rare earth, lithium and cobalt supply chains for defense and EV decoupling",
        "category": "Materials",
        "benchmark_etf": "REMX",
        "tickers": [
            {"symbol": "MP",    "company_name": "MP Materials",      "market_cap_tier": "mid"},
            {"symbol": "UUUU",  "company_name": "Energy Fuels",      "market_cap_tier": "small"},
            {"symbol": "NXE",   "company_name": "NexGen Energy",     "market_cap_tier": "small"},
            {"symbol": "LAC",   "company_name": "Lithium Americas",  "market_cap_tier": "small"},
            {"symbol": "LTHM",  "company_name": "Livent Corporation", "market_cap_tier": "mid"},
            {"symbol": "ALB",   "company_name": "Albemarle",         "market_cap_tier": "mid"},
            {"symbol": "FCX",   "company_name": "Freeport-McMoRan",  "market_cap_tier": "large"},
        ],
    },
    {
        "name": "Spatial Computing & AR",
        "slug": "spatial-computing-ar",
        "description": "Augmented and mixed reality hardware, software and enterprise adoption platforms",
        "category": "Technology",
        "benchmark_etf": "XLK",
        "tickers": [
            {"symbol": "AAPL",  "company_name": "Apple (Vision Pro)", "market_cap_tier": "large"},
            {"symbol": "META",  "company_name": "Meta (Quest)",       "market_cap_tier": "large"},
            {"symbol": "MSFT",  "company_name": "Microsoft (HoloLens)", "market_cap_tier": "large"},
            {"symbol": "IMMR",  "company_name": "Immersion Corporation", "market_cap_tier": "micro"},
            {"symbol": "MVIS",  "company_name": "MicroVision",        "market_cap_tier": "micro"},
            {"symbol": "VUZI",  "company_name": "Vuzix Corporation",  "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Synthetic Biology",
        "slug": "synthetic-biology",
        "description": "Engineering organisms for materials, pharmaceuticals, food and industrial chemicals",
        "category": "Healthcare",
        "benchmark_etf": "ARKG",
        "tickers": [
            {"symbol": "TWST",  "company_name": "Twist Bioscience",  "market_cap_tier": "small"},
            {"symbol": "DNAY",  "company_name": "Codex DNA",         "market_cap_tier": "micro"},
            {"symbol": "SRNA",  "company_name": "Sarepta Therapeutics", "market_cap_tier": "mid"},
            {"symbol": "AMRS",  "company_name": "Amyris",            "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Carbon Capture & Climate Tech",
        "slug": "carbon-capture",
        "description": "Direct air capture, carbon sequestration and IRA-funded climate technology",
        "category": "Energy",
        "benchmark_etf": "ICLN",
        "tickers": [
            {"symbol": "CTRA",  "company_name": "Coterra Energy",    "market_cap_tier": "mid"},
            {"symbol": "CLMT",  "company_name": "Calumet Specialty", "market_cap_tier": "small"},
            {"symbol": "OXY",   "company_name": "Occidental Petroleum (DAC)", "market_cap_tier": "large"},
            {"symbol": "NRGV",  "company_name": "Energy Vault",      "market_cap_tier": "micro"},
        ],
    },
    {
        "name": "Longevity & Anti-Aging Biotech",
        "slug": "longevity-biotech",
        "description": "Senolytic therapies, longevity research platforms and anti-aging drug development",
        "category": "Healthcare",
        "benchmark_etf": "ARKG",
        "tickers": [
            {"symbol": "UNITY", "company_name": "Unity Biotechnology", "market_cap_tier": "micro"},
            {"symbol": "HLVX",  "company_name": "HilleVax",           "market_cap_tier": "small"},
            {"symbol": "REGN",  "company_name": "Regeneron",          "market_cap_tier": "large"},
            {"symbol": "BIIB",  "company_name": "Biogen",             "market_cap_tier": "large"},
        ],
    },
    {
        "name": "Water Technology",
        "slug": "water-technology",
        "description": "Water scarcity solutions, purification, infrastructure and smart water management",
        "category": "Utilities",
        "benchmark_etf": "PHO",
        "tickers": [
            {"symbol": "XYL",   "company_name": "Xylem",             "market_cap_tier": "large"},
            {"symbol": "PNR",   "company_name": "Pentair",           "market_cap_tier": "large"},
            {"symbol": "AWK",   "company_name": "American Water Works", "market_cap_tier": "large"},
            {"symbol": "FELE",  "company_name": "Franklin Electric",  "market_cap_tier": "mid"},
            {"symbol": "MSEX",  "company_name": "Middlesex Water",   "market_cap_tier": "small"},
            {"symbol": "CWCO",  "company_name": "Consolidated Water", "market_cap_tier": "small"},
        ],
    },
    {
        "name": "Digital Defense & LEO Comms",
        "slug": "digital-defense-leo",
        "description": "Military low-earth orbit communications, GPS alternatives and satellite-based ISR",
        "category": "Industrials",
        "benchmark_etf": "ITA",
        "tickers": [
            {"symbol": "RKLB",  "company_name": "Rocket Lab",         "market_cap_tier": "small"},
            {"symbol": "AST",   "company_name": "AST SpaceMobile",    "market_cap_tier": "small"},
            {"symbol": "IRDM",  "company_name": "Iridium Communications", "market_cap_tier": "mid"},
            {"symbol": "VSAT",  "company_name": "Viasat",             "market_cap_tier": "mid"},
            {"symbol": "HII",   "company_name": "Huntington Ingalls", "market_cap_tier": "mid"},
            {"symbol": "BKSY",  "company_name": "BlackSky Technology", "market_cap_tier": "micro"},
        ],
    },
]

# Fast lookup: theme slug → theme entry
THEME_BY_SLUG: dict[str, ThemeEntry] = {t["slug"]: t for t in THEME_CONFIG}

# ETF proxy per theme (for volume anomaly detection)
THEME_ETF_MAP: dict[str, str] = {t["name"]: t["benchmark_etf"] for t in THEME_CONFIG}

# All unique tickers across all themes → set of theme names
TICKER_THEMES: dict[str, list[str]] = {}
for _theme in THEME_CONFIG:
    for _ticker in _theme["tickers"]:
        TICKER_THEMES.setdefault(_ticker["symbol"], []).append(_theme["name"])

# Google Trends keyword map (theme name → search terms)
THEME_TREND_KEYWORDS: dict[str, list[str]] = {
    "Semiconductors":                  ["semiconductor stocks", "chip stocks ETF"],
    "AI Infrastructure":               ["AI infrastructure stocks", "data center stocks"],
    "AI Data Center Infrastructure":   ["data center cooling stocks", "AI power stocks"],
    "Cybersecurity":                    ["cybersecurity stocks", "cyber ETF"],
    "Cloud & SaaS":                     ["cloud stocks", "SaaS stocks"],
    "Defense & Aerospace":              ["defense stocks", "aerospace ETF"],
    "Grid & Power Infrastructure":      ["power grid stocks", "grid infrastructure ETF"],
    "Nuclear Energy":                   ["nuclear energy stocks", "SMR stocks"],
    "Clean Energy":                     ["clean energy stocks", "solar stocks ETF"],
    "Biotech & Genomics":               ["biotech stocks", "CRISPR stocks"],
    "EV & Battery Tech":                ["EV stocks", "battery stocks lithium"],
    "Space & Satellite":                ["space stocks", "satellite internet stocks"],
    "Quantum Computing":                ["quantum computing stocks", "quantum ETF"],
    "Drone & Autonomous Systems":       ["drone stocks", "autonomous vehicle stocks"],
    "Fintech & Payments":               ["fintech stocks", "payment stocks"],
    "Photonics & Optical":              ["photonics stocks", "fiber optic stocks"],
    "Humanoid Robotics":                ["humanoid robot stocks", "robot ETF"],
    "GLP-1 Supply Chain":               ["GLP-1 stocks", "Ozempic stocks obesity drug"],
    "Critical Minerals & Rare Earth":   ["rare earth stocks", "critical minerals ETF"],
    "Spatial Computing & AR":           ["spatial computing stocks", "AR glasses stocks"],
    "Synthetic Biology":                ["synthetic biology stocks", "biotech genomics"],
    "Carbon Capture & Climate Tech":    ["carbon capture stocks", "climate tech investment"],
    "Longevity & Anti-Aging Biotech":   ["longevity stocks", "anti-aging biotech"],
    "Water Technology":                 ["water stocks", "water scarcity investment"],
    "Digital Defense & LEO Comms":      ["LEO satellite stocks", "military satellite"],
}

# C-suite title keywords for insider conviction scoring
CSUITE_KEYWORDS = (
    "ceo", "cfo", "coo", "president", "chairman", "chief",
    "director", "founder", "general counsel",
)
