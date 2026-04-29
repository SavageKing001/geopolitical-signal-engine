import time
import requests
from .psychology_signals import detect_signals

GEOPOLITICAL_SUBREDDITS = [
    "worldnews", "geopolitics", "investing",
]

_HEADERS = {"User-Agent": "geopolitical-signal-bot/0.1"}
_BASE_URL = "https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"


def get_mock_posts(keyword):
    kw = keyword.lower()

    if any(w in kw for w in ("iran", "war", "conflict")):
        return [
            {
                "title": "People panic buying gold and hoarding food as Iran war fears deepen",
                "url": "https://reddit.com/mock/1",
                "score": 4821,
                "num_comments": 312,
            },
            {
                "title": "Oil prices rising fast, shortage fears grow as Middle East conflict escalates",
                "url": "https://reddit.com/mock/2",
                "score": 3104,
                "num_comments": 198,
            },
            {
                "title": "Market crash incoming — sell everything before this crisis triggers economic collapse",
                "url": "https://reddit.com/mock/3",
                "score": 2876,
                "num_comments": 441,
            },
            {
                "title": "Run on banks spreading, losing savings fast as Iran conflict disrupts global economy",
                "url": "https://reddit.com/mock/4",
                "score": 1593,
                "num_comments": 87,
            },
            {
                "title": "Hyperinflation fears surge, stock up on essentials now before supply shortage hits",
                "url": "https://reddit.com/mock/5",
                "score": 987,
                "num_comments": 203,
            },
        ]

    if any(w in kw for w in ("china", "trade")):
        return [
            {
                "title": "Boycott all Chinese goods immediately — stop buying from them until tariffs drop",
                "url": "https://reddit.com/mock/6",
                "score": 5210,
                "num_comments": 674,
            },
            {
                "title": "Never buying Chinese products again after these sanctions — blacklist keeps growing",
                "url": "https://reddit.com/mock/7",
                "score": 3987,
                "num_comments": 502,
            },
            {
                "title": "Consumer backlash surging: trade ban on Chinese imports gaining massive momentum",
                "url": "https://reddit.com/mock/8",
                "score": 2341,
                "num_comments": 289,
            },
            {
                "title": "Cancel all orders and divest from China now — import ban coming, don't wait",
                "url": "https://reddit.com/mock/9",
                "score": 1876,
                "num_comments": 143,
            },
            {
                "title": "Refuse to buy anything made in China — brand boycott movement spreading fast",
                "url": "https://reddit.com/mock/10",
                "score": 1204,
                "num_comments": 321,
            },
        ]

    if "gold" in kw:
        return [
            {
                "title": "Buy gold now before currency collapse — government is lying about real inflation",
                "url": "https://reddit.com/mock/11",
                "score": 6102,
                "num_comments": 891,
            },
            {
                "title": "Buying bitcoin and gold — dollar becoming worthless currency, don't trust the Fed",
                "url": "https://reddit.com/mock/12",
                "score": 4450,
                "num_comments": 563,
            },
            {
                "title": "Central bank inflation stealing our savings — escape the system, buy gold now",
                "url": "https://reddit.com/mock/13",
                "score": 3312,
                "num_comments": 417,
            },
            {
                "title": "Fiat worthless and system is rigged — gold price rising as trust collapses everywhere",
                "url": "https://reddit.com/mock/14",
                "score": 2198,
                "num_comments": 278,
            },
            {
                "title": "Can't trust government anymore — dollar collapse incoming, losing faith in institutions",
                "url": "https://reddit.com/mock/15",
                "score": 1743,
                "num_comments": 194,
            },
        ]

    return [
        {
            "title": "Global crisis deepening — panic buying and hoarding reported across multiple countries",
            "url": "https://reddit.com/mock/16",
            "score": 2341,
            "num_comments": 187,
        },
        {
            "title": "Government failed again — losing faith as economic collapse fears spread worldwide",
            "url": "https://reddit.com/mock/17",
            "score": 1876,
            "num_comments": 143,
        },
        {
            "title": "Sanctions and trade ban expanding rapidly — boycott pressure on multiple nations intensifying",
            "url": "https://reddit.com/mock/18",
            "score": 1204,
            "num_comments": 95,
        },
    ]


def fetch_reddit_posts(subreddit, limit=10):
    url = _BASE_URL.format(subreddit=subreddit, limit=limit)
    try:
        response = requests.get(url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        children = response.json()["data"]["children"]
        posts = []
        for child in children:
            d = child["data"]
            posts.append({
                "title":        d.get("title", ""),
                "url":          d.get("url", ""),
                "id":           d.get("id", ""),
                "score":        d.get("score", 0),
                "num_comments": d.get("num_comments", 0),
                "subreddit":    subreddit,
            })
        return posts
    except Exception as e:
        print(f"  [warning] Could not fetch r/{subreddit}: {e}")
        return []


def fetch_post_comments(post_url, limit=5):
    json_url = post_url.rstrip("/") + ".json"
    try:
        response = requests.get(json_url, headers=_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Reddit returns [post_listing, comments_listing]
        comment_listing = data[1]["data"]["children"]
        comments = []
        for child in comment_listing:
            if child["kind"] != "t1":
                continue
            body = child["data"].get("body", "").strip()
            if body and body != "[deleted]" and body != "[removed]":
                comments.append(body)
            if len(comments) >= limit:
                break
        return comments
    except Exception as e:
        print(f"  [warning] Could not fetch comments from {post_url}: {e}")
        return []


def search_reddit(keyword, subreddits=None, use_mock=True):
    if use_mock:
        matched = []
        for post in get_mock_posts(keyword):
            signals = detect_signals(post["title"])
            matched.append({
                **post,
                "subreddit":         "mock",
                "psychology":        signals,
                "comments_analyzed": 0,
            })
        return matched

    if subreddits is None:
        subreddits = GEOPOLITICAL_SUBREDDITS

    search_words = [w.lower() for w in keyword.split()]
    matched = []

    for subreddit in subreddits:
        posts = fetch_reddit_posts(subreddit)
        time.sleep(1)
        for post in posts:
            title_lower = post["title"].lower()
            if any(word in title_lower for word in search_words):
                comment_url = (
                    f"https://www.reddit.com/r/{subreddit}"
                    f"/comments/{post['id']}/"
                )
                comments = fetch_post_comments(comment_url, limit=5)
                combined_text = post["title"] + " " + " ".join(comments)
                signals = detect_signals(combined_text)
                matched.append({
                    **post,
                    "psychology":        signals,
                    "comments_analyzed": len(comments),
                })

    return matched


def get_community_sentiment(keyword):
    posts = search_reddit(keyword)

    if not posts:
        return {
            "keyword":            keyword,
            "total_posts_found":  0,
            "comments_analyzed":  0,
            "avg_panic":          0,
            "avg_boycott":        0,
            "avg_trust_collapse": 0,
            "overall_mood":       "neutral",
        }

    n = len(posts)
    avg_panic         = round(sum(p["psychology"]["panic"]          for p in posts) / n, 2)
    avg_boycott       = round(sum(p["psychology"]["boycott"]        for p in posts) / n, 2)
    avg_trust_collapse = round(sum(p["psychology"]["trust_collapse"] for p in posts) / n, 2)

    scores = {
        "panic":          avg_panic,
        "boycott":        avg_boycott,
        "trust_collapse": avg_trust_collapse,
    }
    overall_mood = max(scores, key=scores.get)
    if scores[overall_mood] == 0:
        overall_mood = "neutral"

    total_comments = sum(p.get("comments_analyzed", 0) for p in posts)

    return {
        "keyword":            keyword,
        "total_posts_found":  n,
        "comments_analyzed":  total_comments,
        "avg_panic":          avg_panic,
        "avg_boycott":        avg_boycott,
        "avg_trust_collapse": avg_trust_collapse,
        "overall_mood":       overall_mood,
    }


if __name__ == "__main__":
    test_keywords = ["Iran war", "China trade", "gold price"]

    for keyword in test_keywords:
        print(f"\n{'=' * 60}")
        print(f"Keyword: {keyword}")
        print("-" * 60)

        posts = search_reddit(keyword, use_mock=True)
        if not posts:
            print("  No matching posts found.")
        else:
            for p in posts[:5]:
                psych = p["psychology"]
                print(f"  [{p['subreddit']:<12}] {p['title'][:70]}")
                print(f"    panic={psych['panic']}  boycott={psych['boycott']}  "
                      f"trust_collapse={psych['trust_collapse']}  "
                      f"comments_analyzed={p['comments_analyzed']}")

        summary = get_community_sentiment(keyword)
        print(f"\nSummary:")
        print(f"  Total posts      : {summary['total_posts_found']}")
        print(f"  Comments analyzed: {summary['comments_analyzed']}")
        print(f"  Avg panic        : {summary['avg_panic']}/10")
        print(f"  Avg boycott      : {summary['avg_boycott']}/10")
        print(f"  Avg trust_coll   : {summary['avg_trust_collapse']}/10")
        print(f"  Overall mood     : {summary['overall_mood']}")
