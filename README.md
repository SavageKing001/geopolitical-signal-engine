# Geopolitical Signal Engine

A signal generation system that maps geopolitical events to small and mid cap stock movements before the market prices them in.

---

## The Problem

When a conflict breaks out in the Middle East or sanctions hit a major economy, institutional desks react within minutes using Bloomberg terminals, satellite data, and dedicated geopolitical risk teams. The move in large caps happens fast and is already priced in before most people open their news app.

What gets missed is the second-order effect. A Greek shipping company re-routing around a war zone. An Indian seed company whose supply chain runs through a sanctions-hit country. A Turkish grocery chain hit by consumer boycotts triggered by a trade dispute nobody is associating with groceries yet.

These small and mid cap companies have real exposure. They just aren't being watched. By the time the market notices, the move has already happened.

---

## Our Approach — What Makes This Different

**1. Second-order supply chain mapping**
We don't just track the obvious. A conflict in the Middle East doesn't only affect oil majors — it affects shipping companies, agricultural importers, and defence contractors across Europe and Asia. We map companies by their `revenue_exposure` and `supply_chain_dependencies`, not just their headline sector.

**2. Human psychology signals**
Markets don't move only on facts — they move on panic, boycotts, and collapsing trust in institutions. We detect these three psychological signals from community text (Reddit, news comments) and use them as a separate scoring layer. A story that generates panic language scores differently from one that generates boycott sentiment, and that difference matters for which sectors move.

**3. Focus on small and mid cap**
Institutional research coverage drops off sharply below $5B market cap. That's where mispricing lives. Our company database is deliberately focused on overlooked names with real geopolitical exposure — not Apple, not ExxonMobil.

**4. Noise filtering before signal generation**
News APIs return a lot of garbage — celebrity gossip, exam prep articles, sports, and entertainment that happen to contain the word "crisis" or "conflict". We filter on dual-keyword matching across title and description before any article reaches the signal layer. If it doesn't read like a geopolitical article, it doesn't generate a signal.

---

## How It Works

```
Geopolitical Event
      │
      ▼
News Fetch & Filter        — Pulls articles from NewsAPI, rejects noise using keyword verification
      │
      ▼
Event Tagging              — Labels each article with region, event type, and urgency
      │
      ▼
Company Mapping            — Finds companies affected by sector, regional revenue, and supply chain exposure
      │
      ▼
Psychology Analysis        — Detects panic, boycott, and trust_collapse signals from community text
      │
      ▼
Signal Generation          — Combines geo score, relevance score, and psychology into a final directional signal
      │
      ▼
Dashboard Output           — Flask web UI showing signal table, gold verdict, and mood summary
```

---

## Project Structure

```
geopolitical-signal-engine/
│
├── main.py                          Entry point — runs full pipeline, exposes get_analysis_data()
│
├── news_pipeline/
│   ├── fetcher.py                   Connects to NewsAPI, fetches articles by keyword
│   ├── verifier.py                  Filters noise, requires 2+ geopolitical keyword matches
│   └── tagger.py                    Tags each article with region, event type, urgency
│
├── company_database/
│   ├── companies.json               20 small/mid cap companies with exposure metadata
│   └── sector_mapper.py             Maps event+region → affected sectors → matching companies
│
├── sentiment_layer/
│   ├── psychology_signals.py        Detects panic, boycott, trust_collapse from text
│   └── reddit_scraper.py            Fetches Reddit posts/comments and scores them (mock mode by default)
│
├── signal_engine/
│   └── scorer.py                    Combines all inputs into a final UP/DOWN/NEUTRAL signal per company
│
├── gold_module/
│   └── gold_signal.py               Standalone gold price direction signal based on event + psychology
│
├── dashboard/
│   ├── app.py                       Flask web server
│   └── templates/
│       ├── index.html               Input form
│       └── results.html             Signal output page
│
└── backtesting/                     (Planned — see Roadmap)
```

---

## Setup & Installation

**Clone the repo**
```bash
git clone https://github.com/yourname/geopolitical-signal-engine.git
cd geopolitical-signal-engine
```

**Install dependencies**
```bash
pip install flask requests newsapi-python
```

**Add your NewsAPI key**

Open `news_pipeline/fetcher.py` and replace the placeholder:
```python
API_KEY = "your_newsapi_key_here"
```

Get a free key at [newsapi.org](https://newsapi.org).

**Run the web dashboard**
```bash
python dashboard/app.py
```
Then open `http://localhost:5000` in your browser.

**Run the terminal version**
```bash
python main.py
```

---

## Example Output

The following was generated for `keyword="Iran war"`, `event_type=conflict`, `region=Middle East`.

```
Psychology: panic=7.6  boycott=0.6  trust_collapse=0.6  mood=panic

  SIGNAL    SCORE  CONF      DRIVER           SECTOR            NAME
  -------  ------  --------  ---------------  ----------------  ----------------------------
  UP        +2.80  medium    panic            energy            Vaalco Energy
  UP        +2.30  medium    panic            energy            Kosmos Energy
  UP        +2.30  medium    panic            energy            Karoon Energy
  UP        +2.30  medium    panic            energy            Transportadora de Gas del Sur
  UP        +1.20  low       panic            shipping          Euroseas
  UP        +1.20  low       panic            shipping          Pangaea Logistics Solutions
  UP        +1.20  low       panic            shipping          Himalaya Shipping

GOLD: BULLISH  |  Score: +6.50  |  Confidence: high
Reason: A conflict event in Middle East carries inherent geopolitical risk
        that historically drives gold upward.
```

---

## Current Limitations & Honest Caveats

- **Reddit scraper runs on mock data by default.** The live Reddit API rate-limits unauthenticated requests aggressively. Real-time Reddit sentiment requires switching `use_mock=False` and adding proper rate limiting or PRAW authentication. The mock data is realistic but hardcoded.

- **Company database covers 20 companies.** This was built to prove the mapping logic works. The signal quality improves directly with database size. Expanding to 100+ companies is the next meaningful step (see Roadmap).

- **Signals are directional only.** The output is UP / DOWN / NEUTRAL with a confidence level. There are no price targets, no entry/exit points, and no position sizing guidance.

- **No backtesting yet.** We haven't validated whether the signals have historically correlated with actual price movements. The backtesting module exists as a placeholder. Until that validation exists, treat every signal as a starting point for research, not a trade recommendation.

- **This is a research tool, not financial advice.** Nothing in this project should be used to make investment decisions without independent analysis.

---

## Roadmap

**Phase 6 — Backtesting**
Run historical geopolitical events through the pipeline and compare generated signals against actual price movements in the weeks following. Build a hit-rate metric per sector and event type.

**Google Trends integration**
Add Google Trends as a third data source alongside NewsAPI and Reddit. Rising search volume for a company's name or sector following an event is an early liquidity signal before price moves.

**Expand company database to 100+**
Add more companies per sector, expand geographic coverage to include Southeast Asia, Latin America, and Eastern Europe more thoroughly. Add a script to auto-suggest new candidates based on supply chain data.

**Price target estimation**
Move beyond directional signals. Use historical volatility and event magnitude to generate a probability-weighted price range for the 5-day and 30-day windows following an event.

---

## Tech Stack

| Component | Tool |
|---|---|
| Language | Python 3.11 |
| Web framework | Flask 3.x |
| News data | NewsAPI (`newsapi-python`) |
| Reddit data | Public JSON API (mock), PRAW (planned) |
| HTTP client | Requests |
| Templating | Jinja2 (via Flask) |
