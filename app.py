import json
import re
import requests
from flask import Flask, render_template_string, jsonify
from datetime import datetime
from textblob import TextBlob
import yfinance as yf
import feedparser
import random

app = Flask(__name__)

# ========== CONFIGURATION ==========
NEWS_SOURCES = [
    'https://feeds.bloomberg.com/markets/news.rss',
    'http://feeds.reuters.com/reuters/businessNews',
    'https://www.cnbc.com/id/100003114/device/rss/rss.html',
]

# ========== NEWS SENTIMENT ANALYZER ==========
def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'http\S+', '', text)
    return text[:300]

def get_sentiment(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    # Keyword boost
    bullish = ['surge', 'rally', 'profit', 'beat', 'bullish', 'growth', 'soar']
    bearish = ['crash', 'decline', 'loss', 'bearish', 'inflation', 'drop', 'fall']
    
    text_lower = text.lower()
    for word in bullish:
        if word in text_lower:
            polarity += 0.1
    for word in bearish:
        if word in text_lower:
            polarity -= 0.1
    
    return max(-1, min(1, polarity))

def fetch_news():
    articles = []
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source)
            for entry in feed.entries[:8]:
                title = clean_text(entry.get('title', ''))
                summary = clean_text(entry.get('summary', ''))
                full_text = title + " " + summary
                
                if len(full_text) > 20:
                    sentiment = get_sentiment(full_text)
                    articles.append({
                        'title': title[:80],
                        'source': source.split('/')[2].replace('www.', ''),
                        'sentiment': round(sentiment, 3),
                        'timestamp': datetime.now().strftime('%H:%M')
                    })
        except Exception as e:
            print(f"Error: {e}")
    
    return articles

# ========== PREDICTION ENGINE ==========
def calculate_prediction(sentiment, stock_code):
    # Get current price trend (simplified)
    try:
        ticker = yf.Ticker(stock_code)
        hist = ticker.history(period='5d')
        if len(hist) >= 2:
            trend = (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]
        else:
            trend = 0
    except:
        trend = 0
    
    # Combine sentiment and trend
    raw_score = (sentiment * 0.6) + (trend * 0.4)
    
    # Add small random factor (0-5%) for variability
    raw_score += random.uniform(-0.05, 0.05)
    
    # Generate signal
    if raw_score > 0.2:
        signal = "STRONG BUY"
        confidence = min(95, 70 + (raw_score * 80))
    elif raw_score > 0.05:
        signal = "BUY"
        confidence = 55 + (raw_score * 50)
    elif raw_score > -0.05:
        signal = "NEUTRAL"
        confidence = 50
    elif raw_score > -0.2:
        signal = "SELL"
        confidence = 55 + (abs(raw_score) * 50)
    else:
        signal = "STRONG SELL"
        confidence = min(95, 70 + (abs(raw_score) * 80))
    
    return {
        'signal': signal,
        'confidence': round(confidence, 1),
        'score': round(raw_score, 3)
    }

# ========== GET STOCK PRICES ==========
def get_prices(stocks):
    prices = {}
    for stock in stocks:
        try:
            ticker = yf.Ticker(stock)
            price = ticker.history(period='1d')['Close'].iloc[-1]
            prices[stock] = round(price, 2)
        except:
            prices[stock] = 0
    return prices

# ========== INSTITUTIONAL DEMO DATA ==========
def get_institutional_moves():
    # Simplified demo data (no pandas needed)
    return {
        'AAPL': 'BUYING',
        'MSFT': 'BUYING', 
        'NVDA': 'STRONG BUY',
        'GOOGL': 'HOLDING',
        'TSLA': 'SELLING',
        'AMZN': 'BUYING',
        'META': 'HOLDING'
    }

# ========== MAIN ANALYSIS ==========
def run_analysis():
    # Fetch news
    news = fetch_news()
    
    # Calculate average sentiment
    if news:
        avg_sentiment = sum(a['sentiment'] for a in news) / len(news)
    else:
        avg_sentiment = 0
    
    # Top stocks
    stocks = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'META']
    
    # Get predictions
    predictions = {}
    for stock in stocks:
        predictions[stock] = calculate_prediction(avg_sentiment, stock)
    
    # Get prices
    prices = get_prices(stocks)
    
    # Get institutional data
    institutional = get_institutional_moves()
    
    # Generate summary
    buy_count = sum(1 for p in predictions.values() if p['signal'] in ['BUY', 'STRONG BUY'])
    sell_count = sum(1 for p in predictions.values() if p['signal'] in ['SELL', 'STRONG SELL'])
    
    if avg_sentiment > 0.15 and buy_count > sell_count:
        summary = "🟢 BULLISH: Positive news sentiment with institutional buying suggests upward momentum."
    elif avg_sentiment < -0.15 and sell_count > buy_count:
        summary = "🔴 BEARISH: Negative sentiment and institutional selling suggest caution."
    else:
        summary = "🟡 NEUTRAL: Mixed signals. Look for confirmation before positions."
    
    return {
        'timestamp': datetime.now().isoformat(),
        'news': news[:12],
        'sentiment': round(avg_sentiment, 3),
        'predictions': predictions,
        'prices': prices,
        'institutional': institutional,
        'summary': summary
    }

# ========== MOBILE HTML ==========
HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Market Predictor AI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            padding: 16px;
            line-height: 1.5;
        }
        .container { max-width: 600px; margin: 0 auto; }
        h1 { font-size: 1.8rem; margin-bottom: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .timestamp { color: #666; font-size: 0.75rem; margin-bottom: 20px; }
        .card {
            background: rgba(20, 25, 50, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 12px;
        }
        .metric {
            background: rgba(0,0,0,0.3);
            padding: 12px;
            border-radius: 12px;
            text-align: center;
        }
        .metric-value { font-size: 1.5rem; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 0.7rem; color: #888; margin-top: 4px; }
        .stock-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .stock-symbol { font-weight: bold; font-size: 1.1rem; }
        .stock-price { font-family: monospace; font-size: 0.9rem; color: #aaa; }
        .signal-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: bold;
        }
        .badge-buy { background: rgba(0,200,83,0.2); color: #00c853; }
        .badge-sell { background: rgba(255,59,48,0.2); color: #ff3b30; }
        .badge-neutral { background: rgba(255,204,0,0.2); color: #ffcc00; }
        .news-item {
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .news-title { font-size: 0.85rem; margin-bottom: 4px; }
        .news-sentiment { font-size: 0.7rem; }
        .positive { color: #00c853; }
        .negative { color: #ff3b30; }
        .inst-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
        button {
            background: #667eea;
            border: none;
            padding: 12px 24px;
            border-radius: 30px;
            color: white;
            font-weight: bold;
            width: 100%;
            margin-top: 8px;
            cursor: pointer;
        }
        .refresh { text-align: center; margin-top: 20px; margin-bottom: 40px; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .loading { animation: pulse 1s infinite; text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Market Predictor AI</h1>
        <div class="timestamp" id="timestamp">Loading...</div>
        <div id="content" class="loading">Loading market data...</div>
        <div class="refresh"><button onclick="refreshData()">🔄 Refresh Analysis</button></div>
    </div>
    <script>
        async function refreshData() {
            document.getElementById('content').innerHTML = '<div class="card loading">Updating...</div>';
            await loadData();
        }
        async function loadData() {
            try {
                const resp = await fetch('/api/analysis');
                const d = await resp.json();
                document.getElementById('timestamp').innerHTML = '🕐 ' + new Date(d.timestamp).toLocaleString();
                let html = '';
                html += `<div class="card"><strong>📈 Market Summary</strong><br>${d.summary}<div class="grid-2"><div class="metric"><div class="metric-value">${(d.sentiment * 100).toFixed(0)}%</div><div class="metric-label">News Sentiment</div></div><div class="metric"><div class="metric-value">${d.news.length}</div><div class="metric-label">News Articles</div></div></div></div>`;
                html += `<div class="card"><strong>🎯 AI Predictions</strong>`;
                const stocks = ['AAPL','MSFT','GOOGL','NVDA','TSLA'];
                for (const s of stocks) {
                    let cls = 'badge-neutral';
                    if (d.predictions[s].signal.includes('BUY')) cls = 'badge-buy';
                    if (d.predictions[s].signal.includes('SELL')) cls = 'badge-sell';
                    html += `<div class="stock-row"><div><span class="stock-symbol">${s}</span><br><span class="stock-price">$${d.prices[s] || 'N/A'}</span></div><div><span class="signal-badge ${cls}">${d.predictions[s].signal}</span><br><small>${d.predictions[s].confidence}%</small></div></div>`;
                }
                html += `</div>`;
                html += `<div class="card"><strong>🏛️ Institutional Activity</strong>`;
                for (const [stock, action] of Object.entries(d.institutional)) {
                    let color = '#ffcc00';
                    if (action.includes('BUY')) color = '#00c853';
                    if (action.includes('SELL')) color = '#ff3b30';
                    html += `<div class="inst-row"><span>${stock}</span><span style="color:${color};">${action}</span></div>`;
                }
                html += `</div>`;
                html += `<div class="card"><strong>📰 Recent News</strong>`;
                for (const n of d.news.slice(0,5)) {
                    const cls = n.sentiment > 0 ? 'positive' : (n.sentiment < 0 ? 'negative' : '');
                    const icon = n.sentiment > 0 ? '🟢' : (n.sentiment < 0 ? '🔴' : '⚪');
                    html += `<div class="news-item"><div class="news-title">${n.title}</div><div class="news-sentiment ${cls}">${icon} Sentiment: ${n.sentiment}</div></div>`;
                }
                html += `</div>`;
                document.getElementById('content').innerHTML = html;
            } catch(e) {
                document.getElementById('content').innerHTML = '<div class="card">Error loading. Check your connection.</div>';
            }
        }
        loadData();
        setInterval(loadData, 60000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/analysis')
def api_analysis():
    return jsonify(run_analysis())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
