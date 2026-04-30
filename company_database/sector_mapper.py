import json
import os

GEOPOLITICAL_IMPACT_MAP = {
    "conflict": {
        # Middle East: rare-earth supply routes + phosphate transit affected
        "Middle East": ["energy", "shipping", "mining and metals", "fertilizers and chemicals"],
        # Asia: rare earths and lithium processing concentrated here
        "Asia":        ["semiconductors", "mining and metals", "shipping", "consumer goods"],
        # Europe: fertilizers first (Russia/Belarus are top exporters hit by war);
        #         nickel/palladium (Russia) also impacted
        "Europe":      ["fertilizers and chemicals", "energy", "defence",
                        "agriculture", "shipping", "mining and metals"],
        "Americas":    ["agriculture", "energy", "consumer goods"],
        # Africa: mining highest priority — Congo cobalt, South African platinum
        "Africa":      ["mining and metals", "energy", "agriculture", "shipping"],
        "Global":      ["energy", "shipping", "defence"],
    },
    "sanction": {
        # Europe: fertilizers highest priority (Belarus potash sanctions);
        #         critical minerals are a primary sanction lever
        "Europe":      ["fertilizers and chemicals", "energy", "agriculture",
                        "shipping", "consumer goods", "mining and metals"],
        "Asia":        ["semiconductors", "consumer goods", "shipping", "mining and metals"],
        "Middle East": ["energy", "shipping", "mining and metals"],
        "Americas":    ["energy", "agriculture", "mining and metals"],
        "Africa":      ["energy", "agriculture", "mining and metals"],
        "Global":      ["energy", "semiconductors", "shipping", "mining and metals"],
    },
    "trade": {
        # Asia: China controls rare-earth processing; fertilizer inputs routed here
        "Asia":        ["semiconductors", "consumer goods", "shipping",
                        "agriculture", "mining and metals", "fertilizers and chemicals"],
        # Americas: Brazil is the world's largest fertilizer importer
        "Americas":    ["agriculture", "energy", "consumer goods", "fertilizers and chemicals"],
        "Europe":      ["energy", "consumer goods", "agriculture"],
        "Middle East": ["energy", "shipping"],
        "Africa":      ["agriculture", "energy"],
        # Global trade disputes: critical minerals highest priority
        "Global":      ["mining and metals", "semiconductors", "consumer goods",
                        "shipping", "agriculture"],
    },
    "election": {
        # Africa: mining royalties are the primary election issue
        "Africa":      ["mining and metals", "energy", "agriculture"],
        # Americas: fertilizer import policy is a major agricultural election issue
        "Americas":    ["energy", "agriculture", "consumer goods", "fertilizers and chemicals"],
        "Asia":        ["semiconductors", "consumer goods"],
        "Europe":      ["energy", "defence"],
        "Middle East": ["energy", "defence"],
        "Global":      ["energy"],
    },
    "natural disaster": {
        "Asia":        ["agriculture", "semiconductors", "shipping"],
        "Americas":    ["agriculture", "energy"],
        "Africa":      ["agriculture"],
        "Europe":      ["energy", "agriculture"],
        "Middle East": ["energy", "shipping"],
        "Global":      ["agriculture", "shipping"],
    },
    "economic": {
        # All regions: both new sectors are macro-sensitive and get affected
        "Asia":        ["semiconductors", "consumer goods", "shipping",
                        "mining and metals", "fertilizers and chemicals"],
        "Americas":    ["energy", "agriculture", "consumer goods",
                        "mining and metals", "fertilizers and chemicals"],
        "Europe":      ["energy", "consumer goods", "defence",
                        "mining and metals", "fertilizers and chemicals"],
        "Middle East": ["energy", "mining and metals", "fertilizers and chemicals"],
        "Africa":      ["energy", "agriculture", "mining and metals", "fertilizers and chemicals"],
        "Global":      ["energy", "semiconductors", "consumer goods",
                        "mining and metals", "fertilizers and chemicals"],
    },
    "general": {
        "Middle East": ["energy", "shipping"],
        "Asia":        ["semiconductors", "shipping"],
        "Europe":      ["energy", "defence"],
        "Americas":    ["agriculture", "energy"],
        "Africa":      ["energy", "agriculture"],
        "Global":      ["energy", "shipping"],
    },
}

_COMPANIES_PATH = os.path.join(os.path.dirname(__file__), "companies.json")


def get_affected_sectors(event_type, region):
    event_map = GEOPOLITICAL_IMPACT_MAP.get(event_type, GEOPOLITICAL_IMPACT_MAP["general"])
    sectors = event_map.get(region, event_map.get("Global", []))
    return list(dict.fromkeys(sectors))  # deduplicate, preserve order


def _load_companies():
    with open(_COMPANIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _region_to_countries(region):
    """Rough mapping from tagger region labels to country/area strings for matching."""
    return {
        "Middle East": [
            "middle east", "israel", "iran", "iraq", "syria", "saudi",
            "yemen", "gaza", "palestine", "lebanon", "jordan", "egypt",
            "qatar", "uae", "kuwait", "oman", "bahrain",
        ],
        "Asia": [
            "asia", "china", "japan", "south korea", "taiwan", "india",
            "pakistan", "bangladesh", "myanmar", "vietnam", "philippines",
            "malaysia", "indonesia", "singapore", "thailand", "sri lanka",
        ],
        "Europe": [
            "europe", "russia", "ukraine", "germany", "france", "uk",
            "poland", "norway", "finland", "sweden", "italy", "spain",
            "netherlands", "belgium", "turkey",
        ],
        "Americas": [
            "americas", "usa", "united states", "canada", "mexico",
            "brazil", "argentina", "chile", "colombia", "venezuela",
            "peru", "uruguay",
        ],
        "Africa": [
            "africa", "nigeria", "ghana", "senegal", "ethiopia", "kenya",
            "south africa", "egypt", "libya", "sudan", "mali", "niger",
            "gabon", "equatorial guinea", "mauritania", "morocco",
        ],
        "Global": [],  # global events touch everywhere — skip geo-filter
    }.get(region, [])


def get_affected_companies(event_type, region):
    affected_sectors = get_affected_sectors(event_type, region)
    companies = _load_companies()
    region_terms = [t.lower() for t in _region_to_countries(region)]
    is_global = region == "Global"

    scored = []
    for company in companies:
        if company["sector"] not in affected_sectors:
            continue

        score = 1  # base: sector match

        # Bonus for sector being higher-priority in the impact list
        try:
            priority = affected_sectors.index(company["sector"])
            score += max(0, len(affected_sectors) - priority)
        except ValueError:
            pass

        if not is_global:
            exposure_lower  = [c.lower() for c in company["revenue_exposure"]]
            supply_lower    = [c.lower() for c in company["supply_chain_dependencies"]]

            if any(term in " ".join(exposure_lower) for term in region_terms):
                score += 3  # direct revenue exposure to the region
            if any(term in " ".join(supply_lower) for term in region_terms):
                score += 2  # supply chain dependency on the region

        scored.append({**company, "relevance_score": score})

    scored.sort(key=lambda c: c["relevance_score"], reverse=True)
    return scored


if __name__ == "__main__":
    test_cases = [
        ("conflict", "Middle East"),
        ("trade",    "Asia"),
        ("conflict", "Africa"),
        ("sanction", "Europe"),
    ]

    for event_type, region in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Event: {event_type.upper()}  |  Region: {region}")
        print(f"Affected sectors: {get_affected_sectors(event_type, region)}")
        print("-" * 60)
        results = get_affected_companies(event_type, region)
        if not results:
            print("  No matching companies found.")
        for c in results:
            print(f"  [{c['relevance_score']:2d}]  {c['ticker']:<14}  {c['sector']:<28}  {c['name']}")
