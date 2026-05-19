import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from main import get_analysis_data
from gold_module.gold_signal import generate_gold_signal

app = Flask(__name__)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vaibhav_watchlist.json')
COMPANIES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'company_database', 'companies.json'
)

PRESET_SCANS = [
    ("Iran war",                "conflict",  "Middle East"),
    ("China trade tariffs",     "trade",     "Asia"),
    ("Russia Ukraine",          "conflict",  "Europe"),
    ("US economy recession",    "economic",  "Americas"),
    ("Africa mining elections", "election",  "Africa"),
]

with open(COMPANIES_FILE) as _f:
    ALL_COMPANIES = json.load(_f)

COMPANY_BY_TICKER = {c['ticker'].upper(): c for c in ALL_COMPANIES}
COMPANY_BY_NAME   = {c['name'].lower(): c for c in ALL_COMPANIES}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_watchlist():
    try:
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def find_company_in_message(msg):
    msg_upper = msg.upper()
    for ticker, company in COMPANY_BY_TICKER.items():
        if ticker in msg_upper:
            return company
    msg_lower = msg.lower()
    for name, company in COMPANY_BY_NAME.items():
        words = [w for w in name.split() if len(w) >= 5]
        if any(w in msg_lower for w in words):
            return company
    return None


def detect_event_type(msg):
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ['war', 'conflict', 'attack', 'military', 'troops',
                                     'iran', 'ukraine', 'russia', 'missile', 'bomb', 'invasion']):
        return 'conflict'
    if any(w in msg_lower for w in ['trade', 'tariff', 'sanction', 'embargo',
                                     'china', 'export', 'import', 'wto']):
        return 'trade'
    if any(w in msg_lower for w in ['election', 'vote', 'poll', 'coup', 'political']):
        return 'election'
    if any(w in msg_lower for w in ['recession', 'inflation', 'gdp', 'interest rate',
                                     'federal reserve', 'economy']):
        return 'economic'
    if any(w in msg_lower for w in ['disaster', 'earthquake', 'flood', 'hurricane',
                                     'tsunami', 'climate']):
        return 'disaster'
    return 'conflict'


def detect_region(msg):
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ['iran', 'israel', 'saudi', 'middle east',
                                     'iraq', 'syria', 'yemen', 'gulf', 'persian']):
        return 'Middle East'
    if any(w in msg_lower for w in ['china', 'japan', 'korea', 'asia', 'taiwan',
                                     'india', 'pakistan', 'southeast asia']):
        return 'Asia'
    if any(w in msg_lower for w in ['russia', 'ukraine', 'europe', 'eu', 'nato',
                                     'germany', 'france', 'poland']):
        return 'Europe'
    if any(w in msg_lower for w in ['us ', 'usa', 'america', 'trump', 'washington',
                                     'federal', 'canada', 'mexico']):
        return 'Americas'
    if any(w in msg_lower for w in ['africa', 'nigeria', 'ghana', 'congo',
                                     'kenya', 'ethiopia', 'south africa']):
        return 'Africa'
    return 'Global'


def extract_keyword(msg):
    stopwords = {
        'what', 'how', 'will', 'affect', 'impact', 'the', 'a', 'an',
        'analyze', 'signal', 'about', 'for', 'on', 'with', 'from', 'to',
        'i', 'me', 'my', 'can', 'could', 'should', 'would', 'is', 'are',
        'was', 'be', 'and', 'or', 'of', 'in', 'at', 'do', 'tell', 'show',
        'give', 'get', 'please', 'this', 'that', 'these', 'those',
    }
    words = msg.lower().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 3]
    return ' '.join(keywords[:3]) if keywords else msg[:50]


def run_all_scans():
    scan_results = []
    for keyword, event_type, region in PRESET_SCANS:
        data = get_analysis_data(keyword, event_type, region)
        scan_results.append(data)

    company_map = {}
    for scan in scan_results:
        for company in scan['company_signals']:
            ticker = company['ticker']
            if (ticker not in company_map
                    or abs(company['final_score']) > abs(company_map[ticker]['final_score'])):
                company_map[ticker] = company

    aggregated = sorted(company_map.values(),
                        key=lambda x: abs(x['final_score']), reverse=True)
    best_scan  = max(scan_results, key=lambda s: abs(s['gold_signal']['final_score']))

    region_activity = []
    for scan, (keyword, event_type, region) in zip(scan_results, PRESET_SCANS):
        region_activity.append({
            'region':   region,
            'keyword':  keyword,
            'up':       scan['summary']['up_count'],
            'down':     scan['summary']['down_count'],
            'neutral':  scan['summary']['neutral_count'],
            'gold':     scan['gold_signal']['signal'],
            'articles': scan['articles_found'],
        })

    return {
        'aggregated_signals': aggregated,
        'best_gold':          best_scan['gold_signal'],
        'best_scan_keyword':  best_scan['keyword'],
        'region_activity':    region_activity,
        'summary': {
            'total':         len(aggregated),
            'up_count':      sum(1 for c in aggregated if c['signal'] == 'UP'),
            'down_count':    sum(1 for c in aggregated if c['signal'] == 'DOWN'),
            'neutral_count': sum(1 for c in aggregated if c['signal'] == 'NEUTRAL'),
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('chatbot.html')


@app.route('/chat', methods=['POST'])
def chat():
    body = request.get_json(force=True)
    msg  = body.get('message', '').strip()
    if not msg:
        return jsonify({'type': 'help', 'message': 'Please ask me something.', 'data': {}})

    msg_lower = msg.lower()

    # GREETING
    greetings = ['hi', 'hey', 'hello', 'good morning', 'good afternoon',
                 'good evening', 'howdy', 'yo', 'sup']
    if msg_lower in greetings or any(msg_lower.startswith(g + ' ') for g in greetings):
        return jsonify({'type': 'welcome', 'message': '', 'data': {}})

    # GLOBAL SCAN
    if any(w in msg_lower for w in ['global scan', "what's happening", 'market today',
                                     'market briefing', 'global market', 'briefing',
                                     'daily scan', 'morning scan']):
        data = run_all_scans()
        return jsonify({
            'type': 'scan_results',
            'message': (f'Global scan complete. Analysed {data["summary"]["total"]} '
                        f'companies across 5 regions.'),
            'data': data,
        })

    # WATCHLIST VIEW
    if any(w in msg_lower for w in ['watchlist', 'my stocks', 'my companies',
                                     'what am i watching', 'show watchlist', 'my watchlist']):
        watchlist = load_watchlist()
        return jsonify({
            'type': 'watchlist_card',
            'message': f'Your watchlist has {len(watchlist)} '
                       f'{"company" if len(watchlist) == 1 else "companies"}.',
            'data': {'watchlist': watchlist},
        })

    # WATCHLIST REMOVE
    if any(w in msg_lower for w in ['remove', 'delete', 'unwatch', 'stop watching']):
        company = find_company_in_message(msg)
        if company:
            watchlist = load_watchlist()
            before    = len(watchlist)
            watchlist = [c for c in watchlist
                         if c['ticker'].upper() != company['ticker'].upper()]
            if len(watchlist) < before:
                save_watchlist(watchlist)
                return jsonify({
                    'type': 'confirmation',
                    'message': f'Removed {company["name"]} from your watchlist.',
                    'data': {'action': 'removed', 'company': company},
                })
            return jsonify({
                'type': 'confirmation',
                'message': f'{company["name"]} was not in your watchlist.',
                'data': {'action': 'not_found', 'company': company},
            })
        return jsonify({
            'type': 'help',
            'message': 'Which company do you want to remove? Try: "remove GRSE.NS"',
            'data': {},
        })

    # WATCHLIST ADD
    if any(w in msg_lower for w in ['add to watchlist', 'watch ', 'track ', 'save ',
                                     'follow ', 'add ']):
        company = find_company_in_message(msg)
        if company:
            watchlist = load_watchlist()
            if any(c['ticker'].upper() == company['ticker'].upper() for c in watchlist):
                return jsonify({
                    'type': 'confirmation',
                    'message': f'{company["name"]} is already in your watchlist.',
                    'data': {'action': 'already_exists', 'company': company},
                })
            entry = {
                'name':       company['name'],
                'ticker':     company['ticker'],
                'sector':     company['sector'],
                'buy_price':  None,
                'notes':      '',
                'added_date': datetime.utcnow().strftime('%Y-%m-%d'),
            }
            watchlist.append(entry)
            save_watchlist(watchlist)
            return jsonify({
                'type': 'confirmation',
                'message': f'Added {company["name"]} ({company["ticker"]}) to your watchlist.',
                'data': {'action': 'added', 'company': company},
            })
        return jsonify({
            'type': 'help',
            'message': 'Which company should I add? Try: "add HAL.NS to my watchlist"',
            'data': {},
        })

    # GOLD SIGNAL
    if any(w in msg_lower for w in ['gold price', 'should i buy gold',
                                     'gold signal', 'gold today']):
        event_type = detect_event_type(msg)
        region     = detect_region(msg)
        keyword    = extract_keyword(msg)
        data       = get_analysis_data(keyword, event_type, region)
        return jsonify({
            'type': 'gold_card',
            'message': f'Gold signal — {region} {event_type}: {data["gold_signal"]["signal"]}',
            'data': data['gold_signal'],
        })

    # Detect company early for signal analysis and lookup
    company = find_company_in_message(msg)

    # SIGNAL ANALYSIS
    analysis_triggers = ['analyze', 'signal', 'what will happen', 'affect', 'impact',
                         'conflict', 'war', 'trade war', 'tariff', 'sanction',
                         'recession', 'election', 'coup', 'crisis', 'tension']
    if any(w in msg_lower for w in analysis_triggers):
        event_type  = detect_event_type(msg)
        region      = detect_region(msg)
        keyword     = extract_keyword(msg)
        data        = get_analysis_data(keyword, event_type, region)
        top_signals = sorted(data['company_signals'],
                             key=lambda x: abs(x['final_score']), reverse=True)[:10]
        data_out    = dict(data)
        data_out['company_signals']  = top_signals
        data_out['highlight_ticker'] = company['ticker'] if company else None
        return jsonify({
            'type': 'signal_table',
            'message': f'{keyword} · {region} · {event_type}',
            'data': data_out,
        })

    # COMPANY LOOKUP
    if company:
        watchlist    = load_watchlist()
        in_watchlist = any(c['ticker'].upper() == company['ticker'].upper()
                           for c in watchlist)
        return jsonify({
            'type': 'company_card',
            'message': f'Here\'s what I know about {company["name"]}.',
            'data': {**company, 'in_watchlist': in_watchlist},
        })

    # GOLD (bare word fallback)
    if 'gold' in msg_lower:
        event_type = detect_event_type(msg)
        region     = detect_region(msg)
        keyword    = extract_keyword(msg)
        data       = get_analysis_data(keyword, event_type, region)
        return jsonify({
            'type': 'gold_card',
            'message': f'Gold signal — {region}: {data["gold_signal"]["signal"]}',
            'data': data['gold_signal'],
        })

    # UNKNOWN
    return jsonify({
        'type': 'help',
        'message': "I didn't quite catch that. Here are some things you can ask:",
        'data': {},
    })


@app.route('/watchlist', methods=['GET'])
def get_watchlist():
    return jsonify(load_watchlist())


@app.route('/watchlist/add', methods=['POST'])
def watchlist_add():
    body    = request.get_json(force=True)
    ticker  = body.get('ticker', '').strip().upper()
    company = COMPANY_BY_TICKER.get(ticker)
    if not company:
        return jsonify({'error': 'Company not found'}), 404
    watchlist = load_watchlist()
    if any(c['ticker'].upper() == ticker for c in watchlist):
        return jsonify({'status': 'already_exists'})
    entry = {
        'name':       company['name'],
        'ticker':     company['ticker'],
        'sector':     company['sector'],
        'buy_price':  None,
        'notes':      '',
        'added_date': datetime.utcnow().strftime('%Y-%m-%d'),
    }
    watchlist.append(entry)
    save_watchlist(watchlist)
    return jsonify({'status': 'added', 'company': company})


@app.route('/watchlist/remove', methods=['POST'])
def watchlist_remove():
    body      = request.get_json(force=True)
    ticker    = body.get('ticker', '').strip().upper()
    watchlist = load_watchlist()
    watchlist = [c for c in watchlist if c['ticker'].upper() != ticker]
    save_watchlist(watchlist)
    return jsonify({'status': 'removed'})


if __name__ == '__main__':
    app.run(debug=True, port=5002)
