from company_database.sector_mapper import get_affected_companies
from sentiment_layer.reddit_scraper import get_community_sentiment
from sentiment_layer.psychology_signals import detect_signals


def score_company(company, psychology_summary):
    sector  = company["sector"]
    panic   = psychology_summary["avg_panic"]
    boycott = psychology_summary["avg_boycott"]
    trust   = psychology_summary["avg_trust_collapse"]

    score = 0.0
    drivers = []

    if sector == "defence" and panic > 5:
        score += 3
        drivers.append("panic")
    if sector == "energy" and panic > 5:
        score += 2
        drivers.append("panic")
    if sector == "energy" and trust > 5:
        score += 2
        drivers.append("trust_collapse")
    if sector == "consumer goods" and boycott > 5:
        score -= 3
        drivers.append("boycott")
    if sector == "shipping" and panic > 5:
        score += 1
        drivers.append("panic")
    if sector == "agriculture" and panic > 5:
        score += 2
        drivers.append("panic")
    if sector == "semiconductors" and boycott > 5:
        score -= 2
        drivers.append("boycott")

    relevance_bonus = round(company["relevance_score"] / 10, 2)
    score = round(score + relevance_bonus, 2)

    if score > 1.0:
        signal = "UP"
    elif score < -1.0:
        signal = "DOWN"
    else:
        signal = "NEUTRAL"

    # Primary driver is whichever triggered the most score movement;
    # fall back to the highest raw psychology score if nothing triggered.
    if drivers:
        signal_driver = max(set(drivers), key=drivers.count)
    else:
        signal_driver = max(
            {"panic": panic, "boycott": boycott, "trust_collapse": trust},
            key=lambda k: {"panic": panic, "boycott": boycott, "trust_collapse": trust}[k],
        )

    abs_score = abs(score)
    if abs_score >= 4:
        confidence = "high"
    elif abs_score >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        **company,
        "final_score":    score,
        "signal":         signal,
        "signal_driver":  signal_driver,
        "confidence":     confidence,
    }


def generate_signals(event_type, region, keyword):
    companies        = get_affected_companies(event_type, region)
    psych_summary    = get_community_sentiment(keyword)

    results = [score_company(c, psych_summary) for c in companies]
    results.sort(key=lambda c: abs(c["final_score"]), reverse=True)

    print(f"\n{'=' * 80}")
    print(f"Event: {event_type.upper()}  |  Region: {region}  |  Keyword: \"{keyword}\"")
    print(f"Psychology: panic={psych_summary['avg_panic']}  "
          f"boycott={psych_summary['avg_boycott']}  "
          f"trust_collapse={psych_summary['avg_trust_collapse']}  "
          f"mood={psych_summary['overall_mood']}")
    print(f"{'-' * 80}")
    print(f"  {'SIGNAL':<7}  {'SCORE':>6}  {'CONF':<8}  {'DRIVER':<15}  {'SECTOR':<16}  NAME")
    print(f"  {'-'*7}  {'-'*6}  {'-'*8}  {'-'*15}  {'-'*16}  {'-'*30}")

    for c in results:
        score_str = f"{c['final_score']:+.2f}"
        print(f"  {c['signal']:<7}  {score_str:>6}  {c['confidence']:<8}  "
              f"{c['signal_driver']:<15}  {c['sector']:<16}  {c['name'][:40]}")

    return results


if __name__ == "__main__":
    scenarios = [
        ("conflict", "Middle East", "Iran war"),
        ("trade",    "Asia",        "China trade"),
    ]

    for event_type, region, keyword in scenarios:
        generate_signals(event_type, region, keyword)
