from news_pipeline.fetcher import fetch_news
from news_pipeline.verifier import filter_articles
from news_pipeline.tagger import tag_all
from company_database.sector_mapper import get_affected_companies
from sentiment_layer.reddit_scraper import get_community_sentiment
from signal_engine.scorer import generate_signals
from gold_module.gold_signal import generate_gold_signal

from collections import Counter


def run_analysis(keyword, event_type, region):
    # ------------------------------------------------------------------ #
    # Step 1 — Header
    # ------------------------------------------------------------------ #
    print(f"\n{'#' * 70}")
    print(f"  GEOPOLITICAL SIGNAL ENGINE")
    print(f"  Keyword    : {keyword}")
    print(f"  Event type : {event_type}")
    print(f"  Region     : {region}")
    print(f"{'#' * 70}")

    # ------------------------------------------------------------------ #
    # Step 2 — Fetch and filter news
    # ------------------------------------------------------------------ #
    articles = fetch_news(keyword)
    print(f"\n[Step 2] News fetch complete: {len(articles)} article(s) passed the filter.")

    # ------------------------------------------------------------------ #
    # Step 3 — Tag articles
    # ------------------------------------------------------------------ #
    tagged_entries = tag_all(articles) if articles else []

    if tagged_entries:
        regions     = [e["tags"]["region"]     for e in tagged_entries]
        event_types = [e["tags"]["event_type"] for e in tagged_entries]
        top_region     = Counter(regions).most_common(1)[0][0]
        top_event_type = Counter(event_types).most_common(1)[0][0]
    else:
        top_region     = region       # fall back to caller-supplied values
        top_event_type = event_type

    print(f"\n[Step 3] Tagging complete.")
    print(f"  Most common region     : {top_region}")
    print(f"  Most common event type : {top_event_type}")

    # ------------------------------------------------------------------ #
    # Step 4 — Company signals
    # ------------------------------------------------------------------ #
    print(f"\n[Step 4] Generating company signals...")
    company_results = generate_signals(event_type, region, keyword)

    # ------------------------------------------------------------------ #
    # Step 5 — Gold signal
    # ------------------------------------------------------------------ #
    print(f"\n[Step 5] Generating gold signal...")
    gold = generate_gold_signal(event_type, region, keyword)
    print(f"\n  GOLD VERDICT: {gold['signal']}  |  Score: {gold['final_score']:+.2f}"
          f"  |  Confidence: {gold['confidence']}")
    print(f"  Reason: {gold['reasoning']}")

    # ------------------------------------------------------------------ #
    # Step 6 — Final summary
    # ------------------------------------------------------------------ #
    up      = sum(1 for c in company_results if c["signal"] == "UP")
    down    = sum(1 for c in company_results if c["signal"] == "DOWN")
    neutral = sum(1 for c in company_results if c["signal"] == "NEUTRAL")
    psych   = get_community_sentiment(keyword)

    print(f"\n{'=' * 70}")
    print(f"  FINAL SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total companies analyzed : {len(company_results)}")
    print(f"  Signals — UP: {up}  DOWN: {down}  NEUTRAL: {neutral}")
    print(f"  Gold direction           : {gold['signal']}")
    print(f"  Overall community mood   : {psych['overall_mood'].upper()}")
    print(f"    panic={psych['avg_panic']}  "
          f"boycott={psych['avg_boycott']}  "
          f"trust_collapse={psych['avg_trust_collapse']}")
    print(f"{'=' * 70}\n")


def get_analysis_data(keyword, event_type, region):
    articles        = fetch_news(keyword)
    tagged_entries  = tag_all(articles) if articles else []
    company_results = generate_signals(event_type, region, keyword)
    gold            = generate_gold_signal(event_type, region, keyword)
    psych           = get_community_sentiment(keyword)

    up      = sum(1 for c in company_results if c["signal"] == "UP")
    down    = sum(1 for c in company_results if c["signal"] == "DOWN")
    neutral = sum(1 for c in company_results if c["signal"] == "NEUTRAL")

    return {
        "keyword":      keyword,
        "event_type":   event_type,
        "region":       region,
        "articles_found": len(articles),
        "company_signals": company_results,
        "gold_signal":  gold,
        "psychology_summary": {
            "avg_panic":          psych["avg_panic"],
            "avg_boycott":        psych["avg_boycott"],
            "avg_trust_collapse": psych["avg_trust_collapse"],
            "overall_mood":       psych["overall_mood"],
        },
        "summary": {
            "up_count":      up,
            "down_count":    down,
            "neutral_count": neutral,
            "total":         len(company_results),
        },
    }


if __name__ == "__main__":
    run_analysis("Iran war",            "conflict", "Middle East")
    run_analysis("China trade tariffs", "trade",    "Asia")
