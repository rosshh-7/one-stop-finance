"""
Keyword + sector-exclusion config used by the FMP/Haiku classifier.

- EXCLUDED_FMP_SECTORS / _INDUSTRIES bail out before the LLM call so a Haiku
  hallucination can't slot a food/retail co into Semiconductors.
- THEME_INDUSTRY_KEYWORDS powers the deterministic fallback when the
  Anthropic API key is unavailable. Multi-word phrases only — bare words
  ("battery", "solar", "defense") match unrelated descriptions too easily.
- Minimum 2 keyword hits for the FMP-profile path (descriptions are short
  and targeted — 2 hits is still cheap evidence).
"""

EXCLUDED_FMP_SECTORS: frozenset[str] = frozenset({
    "Consumer Defensive",
    "Consumer Staples",
    "Food Beverage & Tobacco",
    "Food & Staples Retailing",
    "Beverages",
    "Tobacco",
    "Household Products",
    "Personal Products",
    "Retail",
    "Restaurants",
    "Hotels Restaurants & Leisure",
    "Specialty Retail",
    "Textiles Apparel & Luxury Goods",
    "Food Products",
    "Agricultural Products",
    "Agriculture",
    "Packaged Foods & Meats",
    "Hypermarkets & Super Centers",
    "Drug Retail",
    "General Merchandise Stores",
})

EXCLUDED_FMP_INDUSTRIES: frozenset[str] = frozenset({
    "Food Processing", "Food Distribution", "Confectioners",
    "Farm Products", "Agricultural Inputs", "Grocery Stores",
    "Discount Stores", "Department Stores", "Apparel Stores",
    "Apparel Manufacturing", "Footwear & Accessories",
    "Restaurants", "Fast Food", "Casual Dining",
    "Beverages - Alcoholic", "Beverages - Non-Alcoholic",
    "Tobacco", "Household & Personal Products",
    "Drug Stores", "Packaged Foods",
    "Specialty Chemicals",  # historical miscategorisation of food cos
})

MIN_KEYWORD_HITS = 2

# theme slug → multi-word industry keywords (matched against FMP sector/industry/description)
THEME_INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "semiconductors": [
        "semiconductor", "integrated circuit", "wafer fabrication", "ic design",
        "silicon carbide", "gallium nitride", "microelectronics",
        "semiconductor foundry", "semiconductor fab", "eda software",
        "electronic design automation", "memory chip", "nand flash",
        "dram memory", "flash memory", "analog semiconductor", "mixed signal ic",
        "power semiconductor", "rf semiconductor", "compound semiconductor",
    ],
    "ai-infrastructure": [
        "artificial intelligence", "machine learning", "deep learning",
        "data center", "gpu computing", "neural network", "ai chip",
        "inference accelerator", "large language model", "generative ai",
        "ai hardware", "ai accelerator", "tensor processing",
    ],
    "ai-datacenter-infra": [
        "data center cooling", "liquid cooling", "data center power",
        "thermal management", "data center infrastructure", "colocation",
        "hyperscale data center", "edge data center", "data center construction",
    ],
    "photonics-optical": [
        "optoelectronic", "fiber optic", "optical networking",
        "optical component", "lidar sensor", "photovoltaic",
        "light emitting diode", "optical transceiver", "coherent optics",
        "photonic integrated", "wavelength division", "optical amplifier",
        "infrared sensor", "photonic chip", "fiberoptic cable",
        "optical communication", "laser diode", "photon detector",
    ],
    "cybersecurity": [
        "cybersecurity", "cyber security", "network security", "endpoint security",
        "firewall", "encryption", "identity management", "zero trust",
        "threat detection", "siem", "soar", "vulnerability management",
        "penetration testing", "cloud security", "information security",
        "intrusion detection", "security operations",
    ],
    "defense-aerospace": [
        "defense contractor", "defense systems", "defense electronics",
        "defense technology", "military systems", "military electronics",
        "aerospace defense", "missile systems", "unmanned aerial",
        "radar systems", "sonar systems", "intelligence surveillance",
        "ballistic missile", "armament", "munitions", "combat system",
        "naval warfare", "avionics", "satellite communications defense",
        "space defense", "tactical systems",
    ],
    "grid-power-infra": [
        "power grid", "electric utility infrastructure", "transmission grid",
        "smart grid", "grid inverter", "power electronics", "grid energy storage",
        "microgrid", "substation equipment", "transformer manufacturer",
        "switchgear", "power management system", "distributed energy resource",
        "grid modernization", "high voltage",
    ],
    "nuclear-energy": [
        "nuclear energy", "nuclear power", "uranium mining", "nuclear reactor",
        "small modular reactor", "uranium enrichment", "nuclear fuel",
        "thorium reactor", "nuclear fission", "atomic energy",
        "radioactive material", "nuclear waste management",
    ],
    "clean-energy": [
        "solar energy", "solar panel", "solar power", "wind energy",
        "renewable energy", "clean energy", "green hydrogen", "fuel cell",
        "biofuel", "sustainable energy", "offshore wind", "onshore wind",
        "geothermal energy", "tidal energy", "biomass energy",
        "energy transition", "solar farm",
    ],
    "biotech-genomics": [
        "biotechnology", "genomics", "crispr", "gene therapy",
        "gene editing", "mrna vaccine", "rna therapy", "dna sequencing",
        "cell therapy", "immunotherapy", "oncology drug", "biopharmaceutical",
        "drug discovery platform", "precision medicine", "proteomics",
        "clinical-stage biopharmaceutical", "gene expression", "cell biology",
    ],
    "cloud-saas": [
        "cloud computing", "saas", "software as a service", "platform as a service",
        "paas", "subscription software", "crm software", "erp software",
        "devops platform", "cloud infrastructure", "cloud native",
        "multicloud", "cloud application",
    ],
    "ev-battery-tech": [
        "electric vehicle", "ev charging", "ev powertrain", "ev battery",
        "lithium-ion battery", "solid state battery", "battery management system",
        "energy storage system", "battery cell", "battery pack",
        "ev manufacturer", "charging infrastructure", "cathode material",
        "anode material", "electrolyte material", "battery recycling",
    ],
    "space-satellite": [
        "satellite", "space launch", "orbital mechanics", "earth observation",
        "remote sensing satellite", "space exploration", "launch vehicle",
        "rocket propulsion", "microsatellite", "cubesat", "space technology",
        "geostationary orbit", "low earth orbit", "lunar mission", "spacecraft",
    ],
    "quantum-computing": [
        "quantum computing", "quantum computer", "qubit", "quantum cryptography",
        "quantum key distribution", "quantum annealing", "quantum hardware",
        "quantum software", "post-quantum cryptography", "quantum networking",
    ],
    "drone-autonomous": [
        "drone manufacturer", "uav", "unmanned aerial vehicle", "autonomous vehicle",
        "evtol", "air taxi", "urban air mobility", "autonomous flight system",
        "unmanned systems", "robotic aircraft", "delivery drone",
        "autonomous driving", "self-driving",
    ],
    "fintech-payments": [
        "fintech", "financial technology", "payment processing", "digital payment",
        "neobank", "digital banking", "cryptocurrency", "blockchain technology",
        "buy now pay later", "bnpl", "insurtech", "regtech", "wealthtech",
        "peer to peer lending", "digital wallet",
    ],
    "humanoid-robotics": [
        "humanoid robot", "industrial robot", "robotic actuator",
        "service robot", "robot motion", "robot control", "robotic arm",
    ],
    "glp1-supply-chain": [
        "glp-1", "glp1", "obesity drug", "weight loss drug", "incretin",
        "ozempic", "wegovy", "mounjaro", "semaglutide", "tirzepatide",
    ],
    "critical-minerals": [
        "rare earth", "critical minerals", "lithium mining", "cobalt mining",
        "nickel mining", "graphite mining", "rare earth element",
        "rare earth oxide", "rare earth processing",
    ],
    "spatial-computing-ar": [
        "augmented reality", "mixed reality", "spatial computing",
        "ar glasses", "vr headset", "extended reality", "ar platform",
    ],
    "synthetic-biology": [
        "synthetic biology", "engineered organism", "dna synthesis",
        "biomanufacturing", "cell programming", "biological engineering",
    ],
    "carbon-capture": [
        "carbon capture", "direct air capture", "carbon sequestration",
        "carbon removal", "ccus", "carbon storage", "ccus technology",
    ],
    "longevity-biotech": [
        "longevity research", "anti-aging therapy", "senolytic",
        "cellular reprogramming", "rapamycin", "healthspan",
    ],
    "water-technology": [
        "water purification", "water treatment", "desalination",
        "water infrastructure", "smart water", "water scarcity",
        "membrane filtration",
    ],
    "digital-defense-leo": [
        "leo satellite", "military satellite", "low earth orbit defense",
        "milsatcom", "tactical satellite", "satellite communications defense",
    ],
}


def is_excluded_profile(profile: dict) -> bool:
    sector = (profile.get("sector") or "").strip()
    industry = (profile.get("industry") or "").strip()
    return sector in EXCLUDED_FMP_SECTORS or industry in EXCLUDED_FMP_INDUSTRIES


def keyword_classify(profile: dict) -> list[str]:
    """Return theme slugs matching the profile via multi-word keyword hits."""
    if is_excluded_profile(profile):
        return []
    search = " ".join([
        profile.get("industry") or "",
        profile.get("sector") or "",
        profile.get("description") or "",
        profile.get("company_name") or "",
    ]).lower()
    matched: list[tuple[str, int]] = []
    for slug, keywords in THEME_INDUSTRY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in search)
        if hits >= MIN_KEYWORD_HITS:
            matched.append((slug, hits))
    matched.sort(key=lambda x: -x[1])
    return [slug for slug, _ in matched[:3]]
