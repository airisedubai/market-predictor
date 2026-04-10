import json
import re
import requests
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
from textblob import TextBlob
from sklearn.ensemble import RandomForestRegressor
import yfinance as yf
import feedparser
import threading
import time

app = Flask(__name__)

# ========== CONFIGURATION ==========
NEWS_SOURCES = [
    'https://feeds.bloomberg.com/markets/news.rss',
    'http://feeds.reuters.com/reuters/businessNews',
    'https://www.cnbc.com/id/100003114/device/rss/rss.html',
    'https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC',
    'https://www.ft.com/?format=rss'
]

# ========== DATA CACHE ==========
class DataCache:
    def __init__(self):
        self.news_data = []
        self.insider_trades = []
        self.predictions = {}
        self.last_update = None
    
    def needs_update(self):
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update).seconds > 300  # Update every 5 min

cache = DataCache()

# ========== NEWS SENTIMENT ANALYZER ==========
class NewsAnalyzer:
    def __init__(self):
        self.sentiment_scores = []
    
    def clean_text(self, text):
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'http\S+', '', text)
        return text[:500]
    
    def get_sentiment(self, text):
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        # Keyword amplification for market-moving terms
        bullish_terms = ['surge', 'rally', 'profit', 'beat', 'upgrade', 'bullish', 'growth']
        bearish_terms = ['crash', 'decline', 'loss', 'downgrade', 'bearish', 'inflation', 'rate hike']
        
        text_lower = text.lower()
        for term in bullish_terms:
            if term in text_lower:
                polarity += 0.15
        for term in bearish_terms:
            if term in text_lower:
                polarity -= 0.15
                
        return max(-1, min(1, polarity))
    
    def fetch_news(self):
        articles = []
        for source in NEWS_SOURCES:
            try:
                feed = feedparser.parse(source)
                for entry in feed.entries[:10]:
                    title = self.clean_text(entry.get('title', ''))
                    summary = self.clean_text(entry.get('summary', ''))
                    full_text = title + " " + summary
                    
                    if len(full_text) > 20:
                        sentiment = self.get_sentiment(full_text)
                        articles.append({
                            'title': title[:100],
                            'source': source.split('/')[2],
                            'sentiment': round(sentiment, 3),
                            'timestamp': datetime.now().isoformat(),
                            'url': entry.get('link', '#')
                        })
            except Exception as e:
                print(f"Error fetching {source}: {e}")
        
        return articles

# ========== INSTITUTIONAL TRACKER ==========
class InstitutionalTracker:
    def __init__(self):
        self.top_holdings = {}
    
    def fetch_13f_demo(self):
        """Demo institutional data (real API requires SEC EDGAR key)"""
        # Sample institutional moves - in production, use sec-api.io
        demo_trades = [
            {'firm': 'Berkshire Hathaway', 'stock': 'AAPL', 'action': 'BUY', 'shares': 5000000, 'date': '2025-01-15'},
            {'firm': 'Renaissance Tech', 'stock': 'MSFT', 'action': 'BUY', 'shares': 2500000, 'date': '2025-01-14'},
            {'firm': 'Bridgewater', 'stock': 'GOOGL', 'action': 'HOLD', 'shares': 1000000, 'date': '2025-01-13'},
            {'firm': 'Citadel', 'stock': 'NVDA', 'action': 'BUY', 'shares': 8000000, 'date': '2025-01-16'},
            {'firm': 'BlackRock', 'stock': 'TSLA', 'action': 'SELL', 'shares': 3000000, 'date': '2025-01-12'}
        ]
        return demo_trades
    
    def calculate_institutional_score(self):
        trades = self.fetch_13f_demo()
        stock_scores = {}
        for trade in trades:
            stock = trade['stock']
            action = trade['action']
            if action == 'BUY':
                stock_scores[stock] = stock_scores.get(stock, 0) + 1
            elif action == 'SELL':
                stock_scores[stock] = stock_scores.get(stock, 0) - 1
        return stock_scores

# ========== PREDICTION ENGINE ==========
class MarketPredictor:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
    
    def prepare_features(self, sentiment_score, institutional_score, volume_change):
        return np.array([[sentiment_score, institutional_score, volume_change]])
    
    def train_model(self):
        # Synthetic training data (real model needs historical data)
        X_train = np.random.randn(1000, 3)
        y_train = 0.3 * X_train[:, 0] + 0.5 * X_train[:, 1] + 0.2 * X_train[:, 2] + np.random.randn(1000) * 0.1
        self.model.fit(X_train, y_train)
        self.is_trained = True
    
    def predict(self, sentiment_score, institutional_score, volume_change):
        if not self.is_trained:
            self.train_model()
        features = self.prepare_features(sentiment_score, institutional_score, volume_change)
        prediction = self.model.predict(features)[0]
        
        # Convert to human-readable signal
        if prediction > 0.3:
            signal = "STRONG BUY"
            confidence = min(95, 70 + (prediction * 50))
        elif prediction > 0.1:
            signal = "BUY"
            confidence = 60 + (prediction * 50)
        elif prediction > -0.1:
            signal = "NEUTRAL"
            confidence = 50
        elif prediction > -0.3:
            signal = "SELL"
            confidence = 60 + (abs(prediction) * 50)
        else:
            signal = "STRONG SELL"
            confidence = min(95, 70 + (abs(prediction) * 50))
        
        return {
            'signal': signal,
            'confidence': round(confidence, 1),
            'raw_score': round(prediction, 3),
            'sentiment_contribution': round(sentiment_score, 3),
            'institutional_contribution': round(institutional_score, 3)
        }

# ========== MAIN ENGINE ==========
class MarketEngine:
    def __init__(self):
        self.news_analyzer = NewsAnalyzer()
        self.institutional_tracker = InstitutionalTracker()
        self.predictor = MarketPredictor()
    
    def run_analysis(self):
        # Fetch data
        news_articles = self.news_analyzer.fetch_news()
        inst_scores = self.institutional_tracker.calculate_institutional_score()
        
        # Calculate aggregate sentiment
        if news_articles:
            avg_sentiment = np.mean([a['sentiment'] for a in news_articles])
        else:
            avg_sentiment = 0
        
        # Aggregate institutional score
        if inst_scores:
            avg_inst_score = np.mean(list(inst_scores.values())) / 5  # Normalize
        else:
            avg_inst_score = 0
        
        # Volume change (simplified)
        volume_change = np.random.randn() * 0.2
        
        # Generate predictions for top stocks
        predictions = {}
        top_stocks = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'META']
        
        for stock in top_stocks:
            stock_inst_score = inst_scores.get(stock, 0) / 3
            pred = self.predictor.predict(avg_sentiment, stock_inst_score, volume_change)
            predictions[stock] = pred
        
        # Get current prices
        prices = {}
        for stock in top_stocks:
            try:
                ticker = yf.Ticker(stock)
                prices[stock] = ticker.history(period='1d')['Close'].iloc[-1]
            except:
                prices[stock] = 0
        
        return {
            'timestamp': datetime.now().isoformat(),
            'news_articles': news_articles[:20],
            'aggregate_sentiment': round(avg_sentiment, 3),
            'institutional_moves': inst_scores,
            'predictions': predictions,
            'prices': prices,
            'market_summary': self.generate_summary(avg_sentiment, inst_scores, predictions)
        }
    
    def generate_summary(self, sentiment, inst_scores, predictions):
        buy_signals = sum(1 for p in predictions.values() if p['signal'] in ['BUY', 'STRONG BUY'])
        sell_signals = sum(1 for p in predictions.values() if p['signal'] in ['SELL', 'STRONG SELL'])
        
        if sentiment > 0.2 and buy_signals > sell_signals:
            return "🟢 BULLISH: Positive news sentiment aligned with institutional buying suggests upward momentum."
        elif sentiment < -0.2 and sell_signals > buy_signals:
            return "🔴 BEARISH: Negative news sentiment and institutional selling suggest caution."
        else:
            return "🟡 NEUTRAL: Mixed signals. Look for confirmation before taking positions."

engine = MarketEngine()

# ========== WEB INTERFACE (Mobile Friendly) ==========
HTML_TEMPLATE = '''
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
        .timestamp { color: #666; font-size: 0.8rem; margin-bottom: 20px; }
        .card {
            background: rgba(20, 25, 50, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .signal-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #0f1428 100%);
            border-left: 4px solid;
            border-radius: 16px;
        }
        .signal-buy { border-left-color: #00c853; }
        .signal-sell { border-left-color: #ff3b30; }
        .signal-neutral { border-left-color: #ffcc00; }
        .signal-text { font-size: 2rem; font-weight: bold; margin: 10px 0; }
        .confidence { font-size: 1rem; color: #aaa; }
        .progress-bar {
            background: #2a2f4a;
            border-radius: 10px;
            height: 8px;
            margin: 10px 0;
            overflow: hidden;
        }
        .progress-fill {
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s;
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
        .metric-value { font-size: 1.4rem; font-weight: bold; color: #667eea; }
        .metric-label { font-size: 0.7rem; color: #888; margin-top: 4px; }
        .stock-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .stock-symbol { font-weight: bold; font-size: 1.1rem; }
        .stock-price { font-family: monospace; font-size: 1rem; color: #aaa; }
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
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .news-title { font-size: 0.9rem; margin-bottom: 4px; }
        .news-sentiment { font-size: 0.7rem; }
        .positive { color: #00c853; }
        .negative { color: #ff3b30; }
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
        .loading { animation: pulse 1s infinite; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Market Predictor AI</h1>
        <div class="timestamp" id="timestamp">Loading data...</div>
        
        <div id="content" class="loading">Loading market data...</div>
        
        <div class="refresh">
            <button onclick="refreshData()">🔄 Refresh Analysis</button>
        </div>
    </div>
    
    <script>
        async function refreshData() {
            document.getElementById('content').innerHTML = '<div class="card loading">Updating market data...</div>';
            await loadData();
        }
        
        async function loadData() {
            try {
                const response = await fetch('/api/analysis');
                const data = await response.json();
                
                document.getElementById('timestamp').innerHTML = '🕐 ' + new Date(data.timestamp).toLocaleString();
                
                let html = '';
                
                // Market Summary
                html += `<div class="card">`;
                html += `<strong>📈 Market Summary</strong><br>`;
                html += `${data.market_summary}<br>`;
                html += `<div class="grid-2">`;
                html += `<div class="metric"><div class="metric-value">${(data.aggregate_sentiment * 100).toFixed(0)}%</div><div class="metric-label">News Sentiment</div></div>`;
                html += `<div class="metric"><div class="metric-value">${Object.keys(data.institutional_moves).length}</div><div class="metric-label">Institutional Moves</div></div>`;
                html += `</div></div>`;
                
                // Top Predictions
                html += `<div class="card"><strong>🎯 AI Predictions</strong><br><small>Based on news + institutional tracking</small>`;
                
                const stocks = Object.keys(data.predictions).slice(0, 5);
                for (const stock of stocks) {
                    const pred = data.predictions[stock];
                    const price = data.prices[stock] ? `$${data.prices[stock].toFixed(2)}` : 'N/A';
                    let signalClass = 'badge-neutral';
                    if (pred.signal.includes('BUY')) signalClass = 'badge-buy';
                    if (pred.signal.includes('SELL')) signalClass = 'badge-sell';
                    
                    html += `<div class="stock-row">
                        <div><span class="stock-symbol">${stock}</span><br><span class="stock-price">${price}</span></div>
                        <div><span class="signal-badge ${signalClass}">${pred.signal}</span><br><small>${pred.confidence}% conf</small></div>
                    </div>`;
                }
                html += `</div>`;
                
                // Institutional Activity
                html += `<div class="card"><strong>🏛️ Institutional Activity (Last 13F)</strong><br><small>What big money is doing</small>`;
                const instStocks = Object.keys(data.institutional_moves).slice(0, 5);
                for (const stock of instStocks) {
                    const action = data.institutional_moves[stock] > 0 ? 'BUYING' : (data.institutional_moves[stock] < 0 ? 'SELLING' : 'HOLDING');
                    const color = data.institutional_moves[stock] > 0 ? '#00c853' : (data.institutional_moves[stock] < 0 ? '#ff3b30' : '#ffcc00');
                    html += `<div class="stock-row">
                        <span class="stock-symbol">${stock}</span>
                        <span style="color: ${color};">${action}</span>
                    </div>`;
                }
                html += `</div>`;
                
                // Recent News
                html += `<div class="card"><strong>📰 Recent News Sentiment</strong>`;
                for (const news of data.news_articles.slice(0, 5)) {
                    const sentimentClass = news.sentiment > 0 ? 'positive' : (news.sentiment < 0 ? 'negative' : '');
                    const sentimentIcon = news.sentiment > 0 ? '🟢' : (news.sentiment < 0 ? '🔴' : '⚪');
                    html += `<div class="news-item">
                        <div class="news-title">${news.title}</div>
                        <div class="news-sentiment ${sentimentClass}">${sentimentIcon} Sentiment: ${news.sentiment}</div>
                    </div>`;
                }
                html += `</div>`;
                
                document.getElementById('content').innerHTML = html;
            } catch(e) {
                document.getElementById('content').innerHTML = '<div class="card">Error loading data. Make sure you have internet connection.</div>';
            }
        }
        
        loadData();
        setInterval(loadData, 60000); // Refresh every minute
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analysis')
def api_analysis():
    result = engine.run_analysis()
    return jsonify(result)

@app.route('/api/predict/<symbol>')
def predict_symbol(symbol):
    """Get prediction for a specific stock"""
    analysis = engine.run_analysis()
    if symbol in analysis['predictions']:
        return jsonify({'symbol': symbol, **analysis['predictions'][symbol]})
    return jsonify({'error': 'Symbol not found'}), 404

# ========== RUN THE APP ==========
if __name__ == '__main__':
    print("=" * 50)
    print("📊 Market Predictor AI - Starting...")
    print("=" * 50)
    print("\n✅ Access the app on your:")
    print("   • Laptop: http://localhost:5000")
    print("   • Phone: http://[YOUR_LAPTOP_IP]:5000")
    print("\n   To find your laptop IP:")
    print("   • Windows: Run 'ipconfig' and look for IPv4 Address")
    print("   • Mac/Linux: Run 'ifconfig' or 'ip addr'")
    print("\n   From your phone, connect to the SAME WiFi network")
    print("   and open the IP address in your browser")
    print("\n" + "=" * 50)
    print("🚀 Server running... Press Ctrl+C to stop")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
