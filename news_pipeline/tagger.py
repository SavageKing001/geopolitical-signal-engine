REGION_KEYWORDS = {
    "Europe": [
        "russia", "ukraine", "nato", "europe", "european", "eu", "germany",
        "france", "uk", "britain", "poland", "finland", "sweden", "belarus",
        "baltics", "moldova", "hungary", "serbia", "kosovo"
    ],
    "Middle East": [
        "israel", "iran", "iraq", "syria", "saudi", "yemen", "gaza",
        "palestine", "lebanon", "hezbollah", "hamas", "jordan", "egypt",
        "qatar", "uae", "persian gulf", "middle east"
    ],
    "Asia": [
        "china", "japan", "korea", "taiwan", "india", "pakistan",
        "afghanistan", "myanmar", "south china sea", "asia", "beijing",
        "tokyo", "delhi", "islamabad", "pyongyang", "seoul", "hong kong"
    ],
    "Americas": [
        "us", "usa", "united states", "america", "american", "canada",
        "mexico", "brazil", "venezuela", "colombia", "cuba", "haiti",
        "washington", "pentagon", "congress"
    ],
    "Africa": [
        "africa", "sudan", "ethiopia", "nigeria", "libya", "somalia",
        "mali", "sahel", "congo", "mozambique", "kenya", "egypt",
        "south africa", "chad", "niger"
    ],
}

EVENT_KEYWORDS = {
    "conflict": [
        "war", "conflict", "military", "troops", "missile", "invasion",
        "ceasefire", "attack", "strike", "coup", "bombing", "shelling",
        "offensive", "siege", "combat", "battle"
    ],
    "sanction": [
        "sanction", "embargo", "ban", "restrict", "freeze", "blacklist",
        "penalty", "punish"
    ],
    "trade": [
        "trade", "tariff", "supply chain", "export", "import", "deal",
        "agreement", "wto", "commerce"
    ],
    "election": [
        "election", "vote", "voting", "ballot", "referendum", "president",
        "minister", "parliament", "democracy", "campaign", "poll"
    ],
    "natural disaster": [
        "earthquake", "flood", "hurricane", "typhoon", "tsunami",
        "disaster", "storm", "wildfire", "drought", "famine"
    ],
    "economic": [
        "inflation", "currency", "oil", "energy", "gdp", "recession",
        "economy", "financial", "debt", "market", "interest rate"
    ],
}

URGENCY_KEYWORDS = {
    "high": [
        "war", "attack", "strike", "invasion", "missile", "nuclear",
        "coup", "crisis", "emergency", "urgent", "imminent", "breaking",
        "explosion", "killed", "casualties", "bombing"
    ],
    "medium": [
        "sanction", "embargo", "tension", "conflict", "protest", "threat",
        "warning", "standoff", "escalat", "dispute", "clash"
    ],
}


def tag_article(article):
    text = (article.get("title", "") + " " + (article.get("description") or "")).lower()

    region = "Global"
    for reg, keywords in REGION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            region = reg
            break

    event_type = "general"
    for etype, keywords in EVENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            event_type = etype
            break

    urgency = "low"
    if any(kw in text for kw in URGENCY_KEYWORDS["high"]):
        urgency = "high"
    elif any(kw in text for kw in URGENCY_KEYWORDS["medium"]):
        urgency = "medium"

    return {"region": region, "event_type": event_type, "urgency": urgency}


def tag_all(articles):
    return [{"article": a, "tags": tag_article(a)} for a in articles]
