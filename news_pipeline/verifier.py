# Keywords that indicate an article is genuinely geopolitical
GEOPOLITICAL_KEYWORDS = [
    "war", "conflict", "sanction", "military", "troops", "missile",
    "trade", "tariff", "embargo", "invasion", "ceasefire", "treaty",
    "tension", "attack", "strike", "nuclear", "diplomat", "government",
    "president", "minister", "election", "protest", "coup", "crisis",
    "oil", "energy", "supply chain", "economy", "inflation", "currency"
]

# Keywords that immediately disqualify an article
NOISE_KEYWORDS = [
    "upsc", "exam", "quiz", "photos", "art", "celebrity",
    "entertainment", "recipe", "fashion", "sports", "gossip",
    "exclusive", "protest"
]

def is_relevant(article):
    title = article["title"].lower()
    description = (article.get("description") or "").lower()
    text = title + " " + description

    # Immediately reject if noise keyword found in title
    for noise in NOISE_KEYWORDS:
        if noise in title:
            return False

    # Require at least two geopolitical keywords across title + description
    matches = sum(1 for kw in GEOPOLITICAL_KEYWORDS if kw in text)
    return matches >= 2

def filter_articles(articles):
    relevant = [a for a in articles if is_relevant(a)]
    rejected = len(articles) - len(relevant)
    
    print(f"  Filtered: {len(relevant)} kept, {rejected} rejected")
    return relevant