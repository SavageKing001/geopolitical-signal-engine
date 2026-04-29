from sentiment_layer.reddit_scraper import get_community_sentiment

GOLD_TRIGGER_MAP = {
    "conflict":         3,
    "sanction":         2,
    "election":         1,
    "economic":         2,
    "trade":            1,
    "natural disaster": 1,
    "general":          0,
}

GOLD_REGION_MULTIPLIER = {
    "Middle East": 1.5,
    "Global":      1.4,
    "Europe":      1.3,
    "Asia":        1.2,
    "Americas":    1.1,
    "Africa":      1.0,
}


def generate_gold_signal(event_type, region, keyword):
    base_score  = GOLD_TRIGGER_MAP.get(event_type, 0)
    multiplier  = GOLD_REGION_MULTIPLIER.get(region, 1.0)
    geo_score   = round(base_score * multiplier, 2)

    psych       = get_community_sentiment(keyword)
    panic       = psych["avg_panic"]
    trust       = psych["avg_trust_collapse"]
    boycott     = psych["avg_boycott"]

    psychology_bonus = 0.0
    if panic > 5:
        psychology_bonus += 2
    if trust > 5:
        psychology_bonus += 3
    if boycott > 5:
        psychology_bonus += 1

    final_score = round(geo_score + psychology_bonus, 2)

    if final_score >= 4:
        signal = "BULLISH"
    elif final_score <= -1:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    if abs(final_score) >= 6:
        confidence = "high"
    elif abs(final_score) >= 3:
        confidence = "medium"
    else:
        confidence = "low"

    # Primary driver: whichever contributed most to the final score
    contributions = {
        "geo_event":     geo_score,
        "panic":         2.0 if panic > 5 else 0.0,
        "trust_collapse": 3.0 if trust > 5 else 0.0,
        "boycott":       1.0 if boycott > 5 else 0.0,
    }
    primary_driver = max(contributions, key=contributions.get)

    reasoning = _build_reasoning(event_type, region, primary_driver,
                                  signal, panic, trust, boycott)

    return {
        "event_type":       event_type,
        "region":           region,
        "keyword":          keyword,
        "base_score":       base_score,
        "geo_score":        geo_score,
        "psychology_bonus": psychology_bonus,
        "final_score":      final_score,
        "signal":           signal,
        "confidence":       confidence,
        "primary_driver":   primary_driver,
        "reasoning":        reasoning,
        "psychology": {
            "avg_panic":          panic,
            "avg_boycott":        boycott,
            "avg_trust_collapse": trust,
            "overall_mood":       psych["overall_mood"],
        },
    }


def _build_reasoning(event_type, region, primary_driver, signal, panic, trust, boycott):
    signal_word = {"BULLISH": "upward", "BEARISH": "downward", "NEUTRAL": "sideways"}.get(signal, "sideways")

    if primary_driver == "trust_collapse":
        return (f"High institutional trust collapse (score {trust:.1f}/10) is the dominant force "
                f"driving gold {signal_word} as investors flee to safe-haven assets.")
    if primary_driver == "panic":
        return (f"Elevated public panic (score {panic:.1f}/10) around the {region} {event_type} "
                f"is pushing gold {signal_word} through safe-haven demand.")
    if primary_driver == "geo_event":
        return (f"A {event_type} event in {region} carries inherent geopolitical risk "
                f"that historically drives gold {signal_word}.")
    if primary_driver == "boycott":
        return (f"Trade boycott sentiment (score {boycott:.1f}/10) is creating currency uncertainty "
                f"that supports a {signal_word} move in gold.")
    return f"Mixed signals from {region} {event_type} event suggest a {signal_word} trend for gold."


if __name__ == "__main__":
    scenarios = [
        ("conflict", "Middle East", "Iran war"),
        ("trade",    "Asia",        "China trade"),
        ("economic", "Europe",      "Europe recession"),
    ]

    for event_type, region, keyword in scenarios:
        r = generate_gold_signal(event_type, region, keyword)
        print(f"\n{'=' * 65}")
        print(f"  {r['signal']:<8}  |  Score: {r['final_score']:+.2f}  |  Confidence: {r['confidence']}")
        print(f"  Event   : {r['event_type'].upper()} in {r['region']}  (keyword: \"{r['keyword']}\")")
        print(f"  Scores  : base={r['base_score']}  x{GOLD_REGION_MULTIPLIER.get(r['region'], 1.0)}"
              f"  geo={r['geo_score']}  psych_bonus=+{r['psychology_bonus']}")
        print(f"  Mood    : panic={r['psychology']['avg_panic']}  "
              f"boycott={r['psychology']['avg_boycott']}  "
              f"trust_collapse={r['psychology']['avg_trust_collapse']}")
        print(f"  Driver  : {r['primary_driver']}")
        print(f"  Reason  : {r['reasoning']}")
