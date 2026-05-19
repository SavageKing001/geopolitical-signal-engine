import sys
import os
import json
import re
import math
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from flask import Flask, render_template, request, jsonify
from company_database.sector_mapper import get_affected_companies
from sentiment_layer.psychology_signals import detect_signals

try:
    import feedparser as _feedparser
    FEEDPARSER_OK = True
except ImportError:
    FEEDPARSER_OK = False

try:
    import yfinance as _yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

app = Flask(__name__)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vaibhav_watchlist.json')
COMPANIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'company_database', 'companies.json',
)
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')

with open(COMPANIES_FILE, encoding='utf-8') as _f:
    ALL_COMPANIES = json.load(_f)

COMPANY_BY_TICKER = {c['ticker'].upper(): c for c in ALL_COMPANIES}
COMPANY_BY_NAME   = {c['name'].lower(): c for c in ALL_COMPANIES}

# ---------------------------------------------------------------------------
# Signal direction by sector × event_type
# ---------------------------------------------------------------------------
SECTOR_SIGNAL_MAP = {
    'energy':                    {'conflict':'UP',      'sanction':'UP',   'trade':'NEUTRAL', 'election':'NEUTRAL', 'economic':'DOWN',    'natural disaster':'UP'},
    'defence':                   {'conflict':'UP',      'sanction':'NEUTRAL','trade':'NEUTRAL','election':'NEUTRAL', 'economic':'NEUTRAL', 'natural disaster':'NEUTRAL'},
    'shipping':                  {'conflict':'UP',      'sanction':'DOWN', 'trade':'DOWN',    'election':'NEUTRAL', 'economic':'DOWN',    'natural disaster':'DOWN'},
    'semiconductors':            {'conflict':'NEUTRAL', 'sanction':'DOWN', 'trade':'DOWN',    'election':'NEUTRAL', 'economic':'DOWN',    'natural disaster':'NEUTRAL'},
    'agriculture':               {'conflict':'UP',      'sanction':'UP',   'trade':'NEUTRAL', 'election':'NEUTRAL', 'economic':'NEUTRAL', 'natural disaster':'DOWN'},
    'mining and metals':         {'conflict':'UP',      'sanction':'UP',   'trade':'DOWN',    'election':'NEUTRAL', 'economic':'DOWN',    'natural disaster':'NEUTRAL'},
    'consumer goods':            {'conflict':'DOWN',    'sanction':'DOWN', 'trade':'DOWN',    'election':'NEUTRAL', 'economic':'DOWN',    'natural disaster':'DOWN'},
    'fertilizers and chemicals': {'conflict':'UP',      'sanction':'UP',   'trade':'NEUTRAL', 'election':'NEUTRAL', 'economic':'NEUTRAL', 'natural disaster':'NEUTRAL'},
}

# Rough country → region mapping
REGION_COUNTRY_MAP = {
    'Middle East': ['iran','israel','iraq','saudi','syria','yemen','uae','kuwait',
                    'qatar','oman','bahrain','lebanon','gaza','jordan','egypt','persian'],
    'Asia':        ['china','japan','south korea','taiwan','india','pakistan',
                    'vietnam','philippines','malaysia','indonesia','singapore',
                    'thailand','bangladesh','myanmar','sri lanka'],
    'Europe':      ['russia','ukraine','germany','france','uk','poland','norway',
                    'finland','sweden','italy','spain','netherlands','belgium','turkey'],
    'Americas':    ['usa','united states','canada','mexico','brazil','argentina',
                    'chile','colombia','venezuela','peru','uruguay'],
    'Africa':      ['nigeria','ghana','kenya','south africa','ethiopia','congo',
                    'gabon','senegal','mauritania','equatorial guinea','mali','niger',
                    'morocco','libya','sudan'],
}

# Standing active events used for geopolitical analysis
ACTIVE_EVENTS = [
    ('conflict',  'Middle East', 'Iran-Israel tensions'),
    ('trade',     'Asia',        'US-China trade war'),
    ('conflict',  'Europe',      'Russia-Ukraine war'),
    ('sanction',  'Europe',      'Russia sanctions regime'),
    ('economic',  'Americas',    'US Federal Reserve tightening'),
    ('election',  'Africa',      'African mining sector elections'),
    ('trade',     'Asia',        'India-China border trade tensions'),
]

# Reasoning templates: key = (sector, event_type, signal)
REASONING_TEMPLATES = {
    ('energy','conflict','UP'):
        '{name} holds producing assets or supply-chain nodes in regions affected by {event}. '
        'Conflict-driven supply disruptions tighten global energy balances, lifting spot prices '
        'and boosting revenues for producers with capacity outside the conflict zone.',
    ('energy','sanction','UP'):
        'Sanctions targeting {region} energy exporters remove competing supply from global markets. '
        '{name} is positioned to capture the resulting price uplift and potential market share gains '
        'from buyers who can no longer source from sanctioned counterparties.',
    ('energy','economic','DOWN'):
        'Economic contraction in {region} directly reduces energy consumption. '
        '{name}\'s revenues correlate tightly with demand levels, and a sustained GDP slowdown '
        'in key consuming economies compresses both volumes and pricing power.',
    ('defence','conflict','UP'):
        'Conflict escalation in {region} is a direct demand catalyst for {name}. '
        'Governments respond to rising threat perception by accelerating procurement cycles, '
        'expanding existing platform orders, and fast-tracking upgrade programmes — all of which '
        'feed directly into {name}\'s order book.',
    ('shipping','conflict','UP'):
        'Conflict in {region} forces vessel rerouting away from affected straits and ports. '
        'Longer voyage distances tighten effective fleet capacity, pushing freight rates higher '
        'across the routes {name} operates. Rate spikes of this kind translate directly into '
        'near-term revenue outperformance.',
    ('shipping','trade','DOWN'):
        'The {event} reduces cargo volumes on key trade lanes. {name}\'s revenue depends on '
        'throughput; when trade flows between {region} and its major partners slow, vessel '
        'utilisation rates fall and spot rates soften — a direct hit to top-line performance.',
    ('shipping','sanction','DOWN'):
        'Sanctions in {region} disrupt established cargo flows that {name} depends on. '
        'Port access restrictions and compliance costs add friction, while reduced trade '
        'volumes lower utilisation across the fleet.',
    ('semiconductors','sanction','DOWN'):
        '{name} has supply-chain dependencies running through {region}. Sanctions '
        'targeting the region simultaneously restrict access to critical inputs and cut off '
        'customer markets — squeezing {name} on both the cost and revenue side.',
    ('semiconductors','trade','DOWN'):
        'Trade friction between {region} and major economies threatens the integrated supply '
        'chains {name} relies on. Export-control expansion and component tariffs that route '
        'through {region} add cost, create procurement uncertainty, and risk eroding margins.',
    ('agriculture','conflict','UP'):
        'Conflict in {region} disrupts the global grain and fertiliser supply chains that '
        'set commodity price floors. {name} benefits as competing supply contracts, driving '
        'prices toward levels where its own production economics improve materially.',
    ('mining and metals','conflict','UP'):
        '{name}\'s exposure to minerals sourced from or transiting {region} means it is '
        'directly sensitive to conflict-driven supply disruption. Reduced competing supply '
        'tightens the market, pushing spot prices for {name}\'s key output metals higher.',
    ('mining and metals','sanction','UP'):
        'Sanctions on {region} remove significant commodity tonnage from global markets — '
        'particularly in metals where {region} holds a dominant export position. '
        '{name} stands to benefit from the resulting price appreciation.',
    ('mining and metals','trade','DOWN'):
        'Trade barriers in {region} reduce industrial output and metal consumption. '
        '{name}\'s volumes and realised prices are correlated with manufacturing activity, '
        'which contracts when bilateral trade flows between {region} and its partners shrink.',
    ('mining and metals','economic','DOWN'):
        'Economic slowdown in {region} reduces industrial output and metal demand. '
        '{name} faces direct pressure on volumes, utilisation, and realised prices as '
        'key consumers in {region} cut production runs.',
    ('consumer goods','conflict','DOWN'):
        '{name} sells into markets disrupted by {event} in {region}. Consumer spending '
        'contracts during conflict periods, and supply-chain disruption adds cost pressure '
        'simultaneously. Both forces compress {name}\'s margins.',
    ('consumer goods','sanction','DOWN'):
        'Sanctions in {region} restrict either {name}\'s export markets or its input '
        'supply chains. Whether the channel is demand or cost, the net effect is '
        'revenue and margin compression for {name}.',
    ('consumer goods','trade','DOWN'):
        'Trade restrictions in {region} create direct tariff exposure for {name}\'s '
        'cross-border sales. Consumer goods typically face the highest tariff rates '
        'in bilateral trade disputes, making {name} disproportionately vulnerable.',
    ('fertilizers and chemicals','conflict','UP'):
        '{name}\'s products sit upstream of the food supply chain. Conflict in {region} '
        'disrupts competing fertiliser exports, tightening global supply and pushing '
        'prices toward levels that benefit {name}\'s margins significantly.',
    ('fertilizers and chemicals','sanction','UP'):
        'Sanctions on {region} remove major fertiliser exporters from global supply — '
        'particularly potash and nitrogen products. {name} is positioned to capture '
        'both the price uplift and the market share that sanctioned exporters leave behind.',
}

POSITIVE_WORDS = ['beat','strong','growth','profit','record','surge','rally',
                  'wins','award','contract','order','expands','rises','soars',
                  'outperforms','upgrade','buys','acquires','launches','secured']
NEGATIVE_WORDS = ['miss','loss','decline','fall','crash','drop','sell','downgrade',
                  'warning','risk','deficit','slump','cut','layoff','probe',
                  'investigation','default','crisis','sanction','ban','recall','fraud']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_watchlist():
    try:
        with open(WATCHLIST_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def search_company_in_database(query):
    q = query.strip()
    q_upper = q.upper()
    q_lower = q.lower()

    # Exact ticker
    if q_upper in COMPANY_BY_TICKER:
        return COMPANY_BY_TICKER[q_upper]

    # Partial ticker — e.g. "GRSE" matches "GRSE.NS"
    for ticker, company in COMPANY_BY_TICKER.items():
        base = ticker.split('.')[0]
        if base == q_upper:
            return company

    # Exact name
    if q_lower in COMPANY_BY_NAME:
        return COMPANY_BY_NAME[q_lower]

    # All words present in name
    words = [w for w in q_lower.split() if len(w) >= 3]
    if words:
        for name, company in COMPANY_BY_NAME.items():
            if all(w in name for w in words):
                return company

    # Substring (at least 5 chars)
    if len(q_lower) >= 5:
        for name, company in COMPANY_BY_NAME.items():
            if q_lower in name:
                return company

    return None


def fetch_company_news_newsapi(company_name, ticker):
    if not NEWSAPI_KEY:
        return []
    results = []
    for q in [company_name, ticker]:
        if not q:
            continue
        try:
            quoted = f'"{q}"' if ' ' in q else q
            url = (
                'https://newsapi.org/v2/everything'
                f'?q={requests.utils.quote(quoted)}'
                '&language=en&sortBy=publishedAt&pageSize=5'
                f'&apiKey={NEWSAPI_KEY}'
            )
            r = requests.get(url, timeout=8)
            if r.status_code == 429:
                break
            for a in r.json().get('articles', [])[:5]:
                results.append({
                    'title':       (a.get('title')       or '').strip(),
                    'source':      (a.get('source') or {}).get('name', ''),
                    'date':        (a.get('publishedAt') or '')[:10],
                    'url':         a.get('url', ''),
                    'description': (a.get('description') or '').strip(),
                })
            if results:
                break
        except Exception:
            continue
    return results


def fetch_company_news_google(company_name, ticker):
    if not FEEDPARSER_OK:
        return []
    results = []
    for q in [f'{company_name} stock', ticker]:
        if not q:
            continue
        try:
            url  = f'https://news.google.com/rss/search?q={requests.utils.quote(q)}&hl=en&gl=US&ceid=US:en'
            feed = _feedparser.parse(url)
            for entry in (feed.entries or [])[:5]:
                title  = (entry.get('title') or '').strip()
                source = ''
                if ' - ' in title:
                    parts  = title.rsplit(' - ', 1)
                    title  = parts[0].strip()
                    source = parts[1].strip()
                # Date from published_parsed (time struct) or published string
                date_str = ''
                if entry.get('published_parsed'):
                    try:
                        date_str = datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d')
                    except Exception:
                        pass
                elif entry.get('published'):
                    date_str = str(entry.published)[:10]
                results.append({
                    'title':       title,
                    'source':      source or 'Google News',
                    'date':        date_str,
                    'url':         entry.get('link', ''),
                    'description': (entry.get('summary') or '').strip(),
                })
            if results:
                break
        except Exception:
            continue
    return results


def fetch_stock_price(ticker):
    if not YFINANCE_OK:
        return None
    try:
        stock = _yf.Ticker(ticker)
        info  = stock.info or {}
        price = (info.get('regularMarketPrice')
                 or info.get('currentPrice')
                 or info.get('ask'))
        if not price:
            fi    = stock.fast_info
            price = getattr(fi, 'last_price', None)
            if not price:
                return None
            prev  = getattr(fi, 'previous_close', None) or price
            chg   = round((price - prev) / prev * 100, 2) if prev else 0.0
            return {
                'current_price':  round(price, 2),
                'previous_close': round(prev, 2),
                'change_percent': chg,
                'day_high':       getattr(fi, 'day_high', None),
                'day_low':        getattr(fi, 'day_low', None),
                'week_52_high':   getattr(fi, 'year_high', None),
                'week_52_low':    getattr(fi, 'year_low', None),
                'volume':         getattr(fi, 'three_month_average_volume', None),
                'market_cap':     getattr(fi, 'market_cap', None),
                'pe_ratio':       None,
                'currency':       getattr(fi, 'currency', '') or '',
            }

        prev = (info.get('regularMarketPreviousClose')
                or info.get('previousClose')
                or price)
        chg  = round((price - prev) / prev * 100, 2) if prev else 0.0
        return {
            'current_price':  round(price, 2),
            'previous_close': round(prev, 2),
            'change_percent': chg,
            'day_high':       info.get('dayHigh')     or info.get('regularMarketDayHigh'),
            'day_low':        info.get('dayLow')      or info.get('regularMarketDayLow'),
            'week_52_high':   info.get('fiftyTwoWeekHigh'),
            'week_52_low':    info.get('fiftyTwoWeekLow'),
            'volume':         info.get('regularMarketVolume') or info.get('volume'),
            'market_cap':     info.get('marketCap'),
            'pe_ratio':       info.get('trailingPE')  or info.get('forwardPE'),
            'currency':       info.get('currency', '') or '',
        }
    except Exception:
        return None


def fetch_recent_earnings(ticker):
    if not YFINANCE_OK:
        return []
    try:
        stock = _yf.Ticker(ticker)
        try:
            hist = stock.earnings_history
            if hist is not None and not hist.empty:
                rows = []
                for idx, row in hist.head(4).iterrows():
                    rows.append({
                        'date':          str(idx)[:10],
                        'actual_eps':    round(float(row.get('epsActual',    0) or 0), 3),
                        'estimated_eps': round(float(row.get('epsEstimate',  0) or 0), 3),
                        'surprise_pct':  round(float(row.get('surprisePercent', 0) or 0), 2),
                    })
                return rows
        except Exception:
            pass
        return []
    except Exception:
        return []


def _countries_to_regions(country_list):
    found = set()
    joined = ' '.join(c.lower() for c in country_list)
    for region, terms in REGION_COUNTRY_MAP.items():
        if any(t in joined for t in terms):
            found.add(region)
    return list(found) if found else ['Global']


def analyze_company_geopolitical_impact(company):
    sector   = (company.get('sector') or '').lower()
    exposure = company.get('revenue_exposure', [])
    supply   = company.get('supply_chain_dependencies', [])
    relevant = _countries_to_regions(exposure + supply)

    best_score  = -1
    best_event  = None
    best_region = 'Global'

    for ev_type, ev_region, ev_label in ACTIVE_EVENTS:
        if ev_region not in relevant and ev_region != 'Global':
            continue
        for c in get_affected_companies(ev_type, ev_region):
            if c['ticker'].upper() == company['ticker'].upper():
                if c['relevance_score'] > best_score:
                    best_score  = c['relevance_score']
                    best_event  = (ev_type, ev_region, ev_label)
                    best_region = ev_region
                break

    if not best_event:
        return {
            'signal':        'NEUTRAL',
            'confidence':    'low',
            'driver':        'no active event match',
            'primary_event': None,
            'region':        ', '.join(relevant),
            'reasoning':     (
                f'{company["name"]} has no significant exposure under current tracked events. '
                f'Monitor conditions in {", ".join(relevant)} for emerging catalysts.'
            ),
            'active_events': [],
        }

    ev_type, ev_region, ev_label = best_event
    signal     = SECTOR_SIGNAL_MAP.get(sector, {}).get(ev_type, 'NEUTRAL')
    confidence = 'high' if best_score >= 7 else 'medium' if best_score >= 4 else 'low'

    tmpl = REASONING_TEMPLATES.get((sector, ev_type, signal))
    if tmpl:
        reasoning = tmpl.format(
            name=company['name'], event=ev_label,
            region=ev_region, sector=sector,
        )
    else:
        direction = 'positively' if signal == 'UP' else 'negatively' if signal == 'DOWN' else 'marginally'
        reasoning = (
            f'{company["name"]} operates in the {sector} sector with revenue exposure across '
            f'{", ".join(exposure[:3])}. The ongoing {ev_label} ({ev_region}) is expected '
            f'to affect this sector {direction} based on the current event dynamics.'
        )

    # All matching active events
    active_list = []
    for et, er, el in ACTIVE_EVENTS:
        if er in relevant or er == 'Global':
            for c in get_affected_companies(et, er):
                if c['ticker'].upper() == company['ticker'].upper():
                    active_list.append(el)
                    break
    active_list = list(dict.fromkeys(active_list))[:4]  # unique, max 4

    return {
        'signal':        signal,
        'confidence':    confidence,
        'driver':        ev_type,
        'primary_event': ev_label,
        'region':        ev_region,
        'reasoning':     reasoning,
        'active_events': active_list,
    }


def analyze_news_sentiment(articles):
    if not articles:
        return {'panic':0,'boycott':0,'trust_collapse':0,'overall_sentiment':'neutral',
                'positive_hits':0,'negative_hits':0}
    combined = ' '.join(
        (a.get('title','') + ' ' + a.get('description',''))
        for a in articles
    )
    sigs = detect_signals(combined)
    cl   = combined.lower()
    pos  = sum(1 for w in POSITIVE_WORDS if w in cl)
    neg  = sum(1 for w in NEGATIVE_WORDS if w in cl)
    if pos > neg + 1:
        mood = 'positive'
    elif neg > pos + 1:
        mood = 'negative'
    else:
        mood = 'neutral'
    return {
        'panic':             sigs['panic'],
        'boycott':           sigs['boycott'],
        'trust_collapse':    sigs['trust_collapse'],
        'overall_sentiment': mood,
        'positive_hits':     pos,
        'negative_hits':     neg,
    }


def build_company_brief(query):
    company = search_company_in_database(query)
    name    = company['name']    if company else query.strip().title()
    ticker  = company['ticker']  if company else query.strip().upper()

    with ThreadPoolExecutor(max_workers=4) as ex:
        f_newsapi  = ex.submit(fetch_company_news_newsapi, name, ticker)
        f_google   = ex.submit(fetch_company_news_google,  name, ticker)
        f_price    = ex.submit(fetch_stock_price,          ticker)
        f_earnings = ex.submit(fetch_recent_earnings,      ticker)
        news_api   = f_newsapi.result()
        news_goog  = f_google.result()
        price      = f_price.result()
        earnings   = f_earnings.result()

    # Merge + deduplicate news
    all_news, seen = [], set()
    for art in news_api + news_goog:
        key = (art.get('title') or '')[:60].lower()
        if key and key not in seen:
            seen.add(key)
            all_news.append(art)
        if len(all_news) >= 8:
            break

    geo_impact = analyze_company_geopolitical_impact(company) if company else None
    sentiment  = analyze_news_sentiment(all_news)
    watchlist  = load_watchlist()
    in_wl      = any(c['ticker'].upper() == ticker.upper() for c in watchlist)

    return {
        'query':        query,
        'company':      company,
        'name':         name,
        'ticker':       ticker,
        'in_database':  company is not None,
        'in_watchlist': in_wl,
        'price':        price,
        'earnings':     earnings,
        'news':         all_news,
        'geo_impact':   geo_impact,
        'sentiment':    sentiment,
    }


# ---------------------------------------------------------------------------
# JSON sanitizer  (yfinance returns numpy types / NaN / Inf — all fatal to jsonify)
# ---------------------------------------------------------------------------

def _sanitize(val):
    """Recursively convert a value to a JSON-safe native Python type."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        return {k: _sanitize(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_sanitize(v) for v in val]
    # numpy types (present whenever yfinance is used)
    try:
        import numpy as np
        if isinstance(val, np.integer):
            return int(val)
        if isinstance(val, np.floating):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        if isinstance(val, np.bool_):
            return bool(val)
        if isinstance(val, np.ndarray):
            return [_sanitize(v) for v in val.tolist()]
    except ImportError:
        pass
    # Last-resort numeric coercion
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        pass
    return str(val)


# ---------------------------------------------------------------------------
# Intent helpers
# ---------------------------------------------------------------------------

def _is_greeting(msg):
    ml = msg.lower().strip()
    words = ['hi','hey','hello','good morning','good afternoon',
             'good evening','howdy','yo','sup','greetings']
    return ml in words or any(ml.startswith(w + ' ') for w in words)


def _strip_action(msg, *prefixes):
    """Remove leading action word and trailing watchlist phrase."""
    result = re.sub(
        r'^(' + '|'.join(re.escape(p) for p in prefixes) + r')\s+',
        '', msg, flags=re.IGNORECASE
    ).strip()
    result = re.sub(r'\s+(to\s+|from\s+)?(my\s+)?watchlist\b', '', result, flags=re.IGNORECASE).strip()
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('chatbot.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        body = request.get_json(force=True) or {}
        msg  = (body.get('message') or '').strip()
        print(f'\n[CHAT] ── incoming: "{msg}"')

        if not msg:
            print('[CHAT] → empty message → help')
            return jsonify({'type':'help','message':'Please ask me something.','data':{}})

        ml = msg.lower()

        if _is_greeting(msg):
            print('[CHAT] → intent: greeting')
            return jsonify({'type':'welcome','message':'','data':{}})

        if any(w in ml for w in ['compare',' vs ',' versus ']):
            print('[CHAT] → intent: compare (not implemented)')
            return jsonify({
                'type':'help',
                'message':'Company comparison is coming soon. Look them up individually for now.',
                'data':{},
            })

        if any(w in ml for w in ['watchlist','my stocks','my companies','show watchlist',
                                  'what am i watching','show my']):
            print('[CHAT] → intent: watchlist view')
            wl = load_watchlist()
            return jsonify({
                'type':'watchlist_card',
                'message':f'Your watchlist — {len(wl)} {"company" if len(wl)==1 else "companies"}.',
                'data':{'watchlist':wl},
            })

        if re.match(r'^(remove|delete|unwatch)\b', ml):
            q = _strip_action(msg, 'remove','delete','unwatch')
            print(f'[CHAT] → intent: watchlist remove, query="{q}"')
            c = search_company_in_database(q)
            if c:
                wl = load_watchlist()
                before = len(wl)
                wl = [x for x in wl if x['ticker'].upper() != c['ticker'].upper()]
                if len(wl) < before:
                    save_watchlist(wl)
                    return jsonify({'type':'confirmation','message':f'Removed {c["name"]} from your watchlist.',
                                    'data':{'action':'removed','company':c}})
                return jsonify({'type':'confirmation','message':f'{c["name"]} was not in your watchlist.',
                                'data':{'action':'not_found','company':c}})
            return jsonify({'type':'help','message':f'Could not find "{q}" in the database.','data':{}})

        if re.match(r'^(add|watch|track|follow|save)\b', ml) and re.search(r'watchlist', ml):
            q = _strip_action(msg, 'add','watch','track','follow','save')
            print(f'[CHAT] → intent: watchlist add, query="{q}"')
            c = search_company_in_database(q)
            if c:
                wl = load_watchlist()
                if any(x['ticker'].upper() == c['ticker'].upper() for x in wl):
                    return jsonify({'type':'confirmation','message':f'{c["name"]} is already in your watchlist.',
                                    'data':{'action':'already_exists','company':c}})
                wl.append({'name':c['name'],'ticker':c['ticker'],'sector':c['sector'],
                            'buy_price':None,'notes':'',
                            'added_date':datetime.utcnow().strftime('%Y-%m-%d')})
                save_watchlist(wl)
                return jsonify({'type':'confirmation','message':f'Added {c["name"]} ({c["ticker"]}) to your watchlist.',
                                'data':{'action':'added','company':c}})
            return jsonify({'type':'help','message':'Could not find that company. Try the ticker symbol.','data':{}})

        # Default — company lookup / brief
        print(f'[CHAT] → intent: company brief, building for "{msg}"')
        brief      = build_company_brief(msg)
        brief_safe = _sanitize(brief)
        print(f'[CHAT] → brief complete: in_database={brief_safe["in_database"]} '
              f'price={brief_safe["price"] is not None} news={len(brief_safe["news"])}')

        if brief_safe['in_database'] or brief_safe['price'] or brief_safe['news']:
            print(f'[CHAT] → returning company_brief for "{brief_safe["name"]}"')
            return jsonify({'type':'company_brief',
                            'message':f'Intelligence brief for {brief_safe["name"]}.',
                            'data':brief_safe})

        print('[CHAT] → no data found → help')
        return jsonify({'type':'help',
                        'message':'No data found. Try a company name or ticker like "GRSE.NS" or "Mazagon Dock".',
                        'data':{}})

    except Exception as e:
        traceback.print_exc()
        print(f'[CHAT] !! EXCEPTION: {e}')
        return jsonify({'type':'error','message':f'Backend error: {str(e)}','data':{}})


@app.route('/watchlist', methods=['GET'])
def get_watchlist():
    return jsonify(load_watchlist())


@app.route('/watchlist/add', methods=['POST'])
def watchlist_add():
    body   = request.get_json(force=True)
    ticker = (body.get('ticker') or '').strip().upper()
    c = COMPANY_BY_TICKER.get(ticker)
    if not c:
        return jsonify({'error':'Company not found'}), 404
    wl = load_watchlist()
    if any(x['ticker'].upper() == ticker for x in wl):
        return jsonify({'status':'already_exists'})
    wl.append({'name':c['name'],'ticker':c['ticker'],'sector':c['sector'],
               'buy_price':None,'notes':'',
               'added_date':datetime.utcnow().strftime('%Y-%m-%d')})
    save_watchlist(wl)
    return jsonify({'status':'added','company':c})


@app.route('/watchlist/remove', methods=['POST'])
def watchlist_remove():
    body   = request.get_json(force=True)
    ticker = (body.get('ticker') or '').strip().upper()
    wl = [c for c in load_watchlist() if c['ticker'].upper() != ticker]
    save_watchlist(wl)
    return jsonify({'status':'removed'})


if __name__ == '__main__':
    app.run(debug=True, port=5002)
