PANIC_KEYWORDS = [
    "buy gold now", "stock up", "prices rising", "shortage", "hoarding",
    "collapse", "crisis", "run on banks", "sell everything", "market crash",
    "losing savings", "hyperinflation", "panic buying", "food shortage",
    "fuel shortage", "empty shelves", "supply shortage", "price spike",
    "bank run", "economic collapse", "financial collapse", "flee", "flee country",
    "currency crisis", "mass exodus", "flee the city",
]

BOYCOTT_KEYWORDS = [
    "boycott", "ban", "avoid", "stop buying", "never again", "cancel",
    "protest", "refuse to buy", "don't buy", "do not buy", "stop purchasing",
    "pull out", "divest", "sanctions", "consumer backlash", "brand boycott",
    "trade ban", "import ban", "blacklist",
]

TRUST_COLLAPSE_KEYWORDS = [
    "government lying", "government is lying", "don't trust", "can't trust",
    "worthless currency", "currency is worthless", "currency worthless",
    "buy bitcoin", "buying bitcoin", "bitcoin instead",
    "buy gold", "buying gold",
    "currency collapse", "central bank", "inflation stealing",
    "corrupt", "fake news", "cover up", "propaganda",
    "deep state", "rigged", "they're hiding", "losing faith",
    "government failed", "institution failed", "system broken",
    "fiat worthless", "escape the system", "dollar collapse",
]


def _score(matches):
    # Each match adds 3 points; capped at 10.
    # 1 match -> 3,  2 -> 6,  3 -> 9,  4+ -> 10
    return min(10, matches * 3)


def detect_signals(text):
    text_lower = text.lower()

    panic_hits      = [kw for kw in PANIC_KEYWORDS       if kw in text_lower]
    boycott_hits    = [kw for kw in BOYCOTT_KEYWORDS      if kw in text_lower]
    trust_hits      = [kw for kw in TRUST_COLLAPSE_KEYWORDS if kw in text_lower]

    return {
        "panic":          _score(len(panic_hits)),
        "boycott":        _score(len(boycott_hits)),
        "trust_collapse": _score(len(trust_hits)),
        "matched_keywords": {
            "panic":          panic_hits,
            "boycott":        boycott_hits,
            "trust_collapse": trust_hits,
        },
    }


def analyze_articles(articles):
    results = []
    for article in articles:
        title       = article.get("title")       or ""
        description = article.get("description") or ""
        text        = title + " " + description
        signals     = detect_signals(text)
        results.append({**article, "psychology": signals})
    return results


if __name__ == "__main__":
    samples = [
        "People are panic buying gold and hoarding food as the crisis deepens",
        "Boycott all Chinese products, never buying from them again",
        "The government is lying, currency is worthless, buying bitcoin instead",
    ]

    for text in samples:
        print(f"\nText    : {text}")
        signals = detect_signals(text)
        print(f"  Panic          : {signals['panic']}/10  -> {signals['matched_keywords']['panic']}")
        print(f"  Boycott        : {signals['boycott']}/10  -> {signals['matched_keywords']['boycott']}")
        print(f"  Trust Collapse : {signals['trust_collapse']}/10  -> {signals['matched_keywords']['trust_collapse']}")
