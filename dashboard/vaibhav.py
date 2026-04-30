import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for
from main import get_analysis_data

app = Flask(__name__)

WATCHLIST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vaibhav_watchlist.json')

PRESET_SCANS = [
    ("Iran war",                "conflict",  "Middle East"),
    ("China trade tariffs",     "trade",     "Asia"),
    ("Russia Ukraine",          "conflict",  "Europe"),
    ("US economy recession",    "economic",  "Americas"),
    ("Africa mining elections", "election",  "Africa"),
]

SECTORS = [
    "Energy",
    "Semiconductors",
    "Shipping",
    "Agriculture",
    "Defence",
    "Consumer Goods",
    "Mining and Metals",
    "Fertilizers and Chemicals",
]


def load_watchlist():
    try:
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def run_all_scans():
    scan_results = []
    for keyword, event_type, region in PRESET_SCANS:
        data = get_analysis_data(keyword, event_type, region)
        scan_results.append(data)

    # Per ticker keep highest absolute score
    company_map = {}
    for scan in scan_results:
        for company in scan['company_signals']:
            ticker = company['ticker']
            if ticker not in company_map or abs(company['final_score']) > abs(company_map[ticker]['final_score']):
                company_map[ticker] = company

    aggregated = sorted(company_map.values(), key=lambda x: abs(x['final_score']), reverse=True)

    best_scan = max(scan_results, key=lambda s: abs(s['gold_signal']['final_score']))

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
        'aggregated_signals':  aggregated,
        'best_gold':           best_scan['gold_signal'],
        'best_scan_keyword':   best_scan['keyword'],
        'region_activity':     region_activity,
        'summary': {
            'total':         len(aggregated),
            'up_count':      sum(1 for c in aggregated if c['signal'] == 'UP'),
            'down_count':    sum(1 for c in aggregated if c['signal'] == 'DOWN'),
            'neutral_count': sum(1 for c in aggregated if c['signal'] == 'NEUTRAL'),
        },
    }


@app.route('/vaibhav')
def home():
    watchlist = load_watchlist()
    return render_template('vaibhav_home.html', watchlist=watchlist, scan_data=None)


@app.route('/vaibhav/scan', methods=['POST'])
def scan():
    watchlist = load_watchlist()
    scan_data = run_all_scans()
    return render_template('vaibhav_home.html', watchlist=watchlist, scan_data=scan_data)


@app.route('/vaibhav/watchlist')
def watchlist_page():
    watchlist = load_watchlist()

    watchlist_signals = []
    if watchlist:
        watchlist_tickers = {c['ticker'] for c in watchlist}
        scan_data = run_all_scans()
        for signal in scan_data['aggregated_signals']:
            if signal['ticker'] in watchlist_tickers:
                watchlist_signals.append(signal)

    return render_template('vaibhav_watchlist.html',
                           watchlist=watchlist,
                           watchlist_signals=watchlist_signals,
                           sectors=SECTORS)


@app.route('/vaibhav/add', methods=['POST'])
def add_company():
    watchlist = load_watchlist()

    ticker = request.form.get('ticker', '').strip().upper()
    if not ticker:
        return redirect(url_for('watchlist_page'))

    if any(c['ticker'] == ticker for c in watchlist):
        return redirect(url_for('watchlist_page'))

    company = {
        'name':       request.form.get('name', '').strip(),
        'ticker':     ticker,
        'sector':     request.form.get('sector', ''),
        'buy_price':  request.form.get('buy_price', '').strip() or None,
        'notes':      request.form.get('notes', '').strip(),
        'added_date': datetime.utcnow().strftime('%Y-%m-%d'),
    }

    watchlist.append(company)
    save_watchlist(watchlist)
    return redirect(url_for('watchlist_page'))


@app.route('/vaibhav/remove/<ticker>')
def remove_company(ticker):
    watchlist = load_watchlist()
    watchlist = [c for c in watchlist if c['ticker'] != ticker.upper()]
    save_watchlist(watchlist)
    next_page = request.args.get('next', 'watchlist')
    if next_page == 'home':
        return redirect(url_for('home'))
    return redirect(url_for('watchlist_page'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)
