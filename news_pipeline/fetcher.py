import os
import sys
from dotenv import load_dotenv
from .verifier import filter_articles
from .tagger import tag_all
from newsapi import NewsApiClient

load_dotenv()

API_KEY = os.getenv("NEWSAPI_KEY")

if API_KEY is None:
    print("ERROR: NEWSAPI_KEY not found in .env file")
    sys.exit(1)

# Connect to NewsAPI
newsapi = NewsApiClient(api_key=API_KEY)

def fetch_news(keyword):
    print(f"\nFetching news for: {keyword}")
    print("-" * 50)

    response = newsapi.get_everything(
        q=keyword,
        language="en",
        sort_by="publishedAt",
        page_size=5
    )

    articles = response["articles"]
    articles = filter_articles(articles)

    if not articles:
        print("No articles found.")
        return []

    tagged = tag_all(articles)

    for i, entry in enumerate(tagged, 1):
        article = entry["article"]
        tags = entry["tags"]
        print(f"\nArticle {i}")
        print(f"Title   : {article['title']}")
        print(f"Source  : {article['source']['name']}")
        print(f"Date    : {article['publishedAt']}")
        print(f"URL     : {article['url']}")
        print(f"Region  : {tags['region']}  |  Event: {tags['event_type']}  |  Urgency: {tags['urgency']}")
        print("-" * 50)

    return articles


if __name__ == "__main__":
    for keyword in ["Ukraine conflict", "US China trade", "Middle East tension"]:
        fetch_news(keyword)
