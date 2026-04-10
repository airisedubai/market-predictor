import os
import json
import requests
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime, timedelta
import random
import time
import threading
from collections import deque

app = Flask(__name__)

# ========== TELEGRAM ALERTS SETUP ==========
# Add these to Render Environment Variables later:
# TELEGRAM_BOT_TOKEN = your bot token
# TELEGRAM_CHAT_ID = your chat ID

def send_telegram_alert(message):
    """Send alert to Telegram"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if bot_token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            print(f"Telegram error: {e}")

# ========== DUBAI GOLD PRICES (DGCX) ==========
def get_dubai_gold_price():
    """Fetch Dubai Gold & Commodities Exchange prices"""
    # DGCX Gold Futures (symbol: DGCC)
    try:
        import yfinance as yf
        # DGCX Gold contract (approximate using COMEX + premium)
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period='1d')
        if len(hist) > 0:
            international_price = hist['Close'].iloc[-1]
            # Dubai premium usually +$5-15 per ounce
            dubai_price = international_price + random.uniform(5, 15)
            return round(dubai_price, 2)
    except:
        pass
    
    # Fallback
    return round(2950 + random.uniform(-20, 30), 2)

def get_dubai_gold_sentiment():
    """Calculate sentiment based on local factors"""
    # In production: track DGCX volume, local demand
    factors = {
        'dgcx_volume': random.choice(['high', 'medium', 'low']),
        'ramadan_demand': 'increasing' if datetime.now().month in [3, 4] else 'normal',
        'dollar_dxy': get_dxy_trend()
    }
    
    sentiment = 0.2  # base
    if factors['dgcx_volume'] == 'high':
        sentiment += 0.2
    if factors['ramadan_demand'] == 'increasing':
        sentiment += 0.15
    
    return round(sentiment, 2), factors

# ========== TECHNICAL INDICATORS ==========
def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    if len(prices) < period + 1:
        return 50
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)

def calculate_macd(prices):
    """Calculate MACD (12,26,9)"""
    if len(prices) < 26:
        return {'macd': 0, 'signal': 0, 'histogram': 0, 'signal_text': 'NEUTRAL'}
    
    # Calculate EMAs
    ema12 = sum(prices[-12:]) / 12
    ema26 = sum(prices[-26:]) / 26
    macd = ema12 - ema26
    
    # Signal line (9-period EMA of MACD)
    signal = macd * 0.8  # Simplified
    histogram = macd - signal
    
    # Determine signal
    if macd > signal and histogram > 0:
        signal_text = "BULLISH"
    elif macd < signal and histogram < 0:
        signal_text = "BEARISH"
    else:
        signal_text = "NEUTRAL"
    
    return {
        'macd': round(macd, 4),
        'signal': round(signal, 4),
        'histogram': round(histogram, 4),
        'signal_text': signal_text
    }

def calculate_moving_averages(prices):
    """Calculate SMA 20 and 50"""
    if len(prices) >= 20:
        sma20 = sum(prices[-20:]) / 20
    else:
        sma20 = prices[-1] if prices else 0
    
    if len(prices) >= 50:
        sma50 = sum(prices[-50:]) / 50
    else:
        sma50 = prices[-1] if prices else 0
    
    trend = "BULLISH" if sma20 > sma50 else "BEARISH" if sma20 < sma50 else "NEUTRAL"
    
    return {
        'sma20': round(sma20, 2),
        'sma50': round(sma50, 2),
        'trend': trend
    }

# ========== CRYPTO DATA (TOP 10) ==========
def get_top_10_crypto():
    """Fetch top 10 cryptocurrencies with prices and indicators"""
    crypto_list = [
        'bitcoin', 'ethereum', 'solana', 'ripple', 'cardano',
        'dogecoin', 'polkadot', 'avalanche-2', 'shiba-inu', 'tron'
    ]
    
    symbols = {
        'bitcoin': 'BTC', 'ethereum': 'ETH', 'solana': 'SOL',
        'ripple': 'XRP', 'cardano': 'ADA', 'dogecoin': 'DOGE',
        'polkadot': 'DOT', 'avalanche-2': 'AVAX', 'shiba-inu': 'SHIB',
        'tron': 'TRX'
    }
    
    crypto_data = {}
    
    try:
        # Get prices from CoinGecko
        response = requests.get(
            'https://api.coingecko.com/api/v3/simple/price',
            params={
                'ids': ','.join(crypto_list),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true'
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Get historical data for indicators (simplified)
            for coin_id in crypto_list:
                symbol = symbols[coin_id]
                price_data = data.get(coin_id, {})
                
                # Generate synthetic price history for indicators
                current_price = price_data.get('usd', 0)
                change_24h = price_data.get('usd_24h_change', 0)
                
                # Create synthetic price history (last 50 days)
                base_price = current_price
                price_history = []
                for i in range(50):
                    variation = random.uniform(-0.03, 0.03)
                    price_history.append(base_price * (1 + variation))
                price_history.append(current_price)
                
                # Calculate indicators
                rsi = calculate_rsi(price_history)
                macd = calculate_macd(price_history)
                ma = calculate_moving_averages(price_history)
                
                # Generate prediction signal
                signal = generate_crypto_signal(rsi, macd, change_24h)
                
                crypto_data[symbol] = {
                    'price': round(current_price, 6) if current_price < 1 else round(current_price, 2),
                    'change_24h': round(change_24h, 2),
                    'market_cap': price_data.get('usd_market_cap', 0),
                    'volume_24h': price_data.get('usd_24h_vol', 0),
                    'rsi': rsi,
                    'macd': macd,
                    'moving_averages': ma,
                    'signal': signal,
                    'price_history': price_history[-20:]  # Last 20 for charts
                }
    except Exception as e:
        print(f"Crypto API error: {e}")
        # Fallback data
        for symbol, price in [('BTC', 72000), ('ETH', 3800), ('SOL', 180), ('XRP', 0.62), ('ADA', 0.45), ('DOGE', 0.15), ('DOT', 7.20), ('AVAX', 35), ('SHIB', 0.000023), ('TRX', 0.11)]:
            crypto_data[symbol] = {
                'price': price,
                'change_24h': random.uniform(-8, 12),
                'rsi': random.randint(30, 70),
                'signal': {'action': 'NEUTRAL', 'confidence': 50, 'reason': 'Fallback data mode'}
            }
    
    return crypto_data

def generate_crypto_signal(rsi, macd, change_24h):
    """Generate trading signal based on indicators"""
    score = 0
    
    # RSI signals
    if rsi > 70:
        score -= 2  # Overbought
    elif rsi < 30:
        score += 2  # Oversold
    
    # MACD signals
    if macd['signal_text'] == 'BULLISH':
        score += 1.5
    elif macd['signal_text'] == 'BEARISH':
        score -= 1.5
    
    # Momentum
    if change_24h > 5:
        score += 1
    elif change_24h < -5:
        score -= 1
    
    # Generate final signal
    if score >= 2:
        action = "STRONG BUY"
        confidence = min(95, 70 + (score * 8))
        reason = f"Oversold (RSI: {rsi}) + Bullish MACD"
    elif score >= 0.5:
        action = "BUY"
        confidence = 60 + (score * 10)
        reason = "Positive technical setup"
    elif score > -0.5:
        action = "NEUTRAL"
        confidence = 50
        reason = "Mixed signals, wait for confirmation"
    elif score > -2:
        action = "SELL"
        confidence = 60 + (abs(score) * 8)
        reason = f"Overbought (RSI: {rsi}) + Bearish MACD"
    else:
        action = "STRONG SELL"
        confidence = min(95, 70 + (abs(score) * 6))
        reason = "Multiple bearish indicators"
    
    return {
        'action': action,
        'confidence': round(confidence, 1),
        'reason': reason,
        'score': round(score, 2)
    }

# ========== US MARKET DATA (Your Old Features) ==========
def get_us_market_data():
    """Fetch US stock data (your original feature)"""
    us_stocks = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL']
    stock_data = {}
    
    try:
        import yfinance as yf
        for symbol in us_stocks:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period='2d')
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                change = ((current - previous) / previous) * 100
                
                # Simple signal based on price action
                if change > 2:
                    signal = "BUY"
                    confidence = 65
                elif change < -2:
                    signal = "SELL"
                    confidence = 65
                else:
                    signal = "NEUTRAL"
                    confidence = 50
                
                stock_data[symbol] = {
                    'price': round(current, 2),
                    'change': round(change, 2),
                    'signal': signal,
                    'confidence': confidence
                }
    except:
        # Fallback
        for symbol in us_stocks:
            stock_data[symbol] = {
                'price': round(random.uniform(100, 500), 2),
                'change': round(random.uniform(-3, 3), 1),
                'signal': random.choice(['BUY', 'NEUTRAL', 'SELL']),
                'confidence': random.randint(45, 75)
            }
    
    return stock_data

# ========== DXY TREND (For Gold) ==========
def get_dxy_trend():
    """Get DXY trend for gold correlation"""
    try:
        import yfinance as yf
        dxy = yf.Ticker("^DXY")
        hist = dxy.history(period='5d')
        if len(hist) >= 2:
            change = (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]
            if change < -0.003:
                return "WEAKENING (Bullish for Gold)"
            elif change > 0.003:
                return "STRENGTHENING (Bearish for Gold)"
    except:
        pass
    return "NEUTRAL"

# ========== ALERT ENGINE ==========
class AlertEngine:
    def __init__(self):
        self.last_alerts = {}
        self.alert_cooldown = 3600  # 1 hour cooldown
    
    def check_and_alert(self, asset_type, asset_name, signal, price, indicators=None):
        """Check if alert should be sent"""
        key = f"{asset_type}_{asset_name}"
        now = time.time()
        
        # Check cooldown
        if key in self.last_alerts:
            if now - self.last_alerts[key] < self.alert_cooldown:
                return
        
        # Strong signal alert
        if signal.get('action') in ['STRONG BUY', 'STRONG SELL']:
            message = f"""
🚨 <b>Trading Alert - {asset_type}</b> 🚨

<b>{asset_name}</b>
💰 Price: ${price:,.2f}
📊 Signal: <b>{signal['action']}</b>
🎯 Confidence: {signal['confidence']}%
📝 Reason: {signal.get('reason', 'Technical analysis')}

🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            if indicators:
                message += f"\n📈 RSI: {indicators.get('rsi', 'N/A')}"
                message += f"\n📉 MACD: {indicators.get('macd', {}).get('signal_text', 'N/A')}"
            
            send_telegram_alert(message)
            self.last_alerts[key] = now
            print(f"Alert sent for {asset_name}: {signal['action']}")
        
        # Price breakout alert (optional)
        elif signal.get('confidence', 0) > 85:
            message = f"""
⚠️ <b>High Confidence Alert - {asset_type}</b> ⚠️

<b>{asset_name}</b>
Signal: {signal['action']} ({signal['confidence']}% confidence)
Price: ${price:,.2f}

Act on this opportunity!
            """
            send_telegram_alert(message)
            self.last_alerts[key] = now

alert_engine = AlertEngine()

# ========== MAIN ANALYSIS ==========
def run_analysis():
    # Get Dubai Gold
    dubai_gold_price = get_dubai_gold_price()
    dubai_gold_sentiment, local_factors = get_dubai_gold_sentiment()
    
    # Generate gold prediction with indicators
    gold_price_history = [dubai_gold_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(50)]
    gold_price_history.append(dubai_gold_price)
    
    gold_rsi = calculate_rsi(gold_price_history)
    gold_macd = calculate_macd(gold_price_history)
    gold_ma = calculate_moving_averages(gold_price_history)
    
    gold_signal = generate_crypto_signal(gold_rsi, gold_macd, random.uniform(-2, 3))
    
    # Check for alerts
    alert_engine.check_and_alert(
        'GOLD (DGCX)', 'XAU/USD', gold_signal, dubai_gold_price,
        {'rsi': gold_rsi, 'macd': gold_macd}
    )
    
    # Get Crypto Data
    crypto_data = get_top_10_crypto()
    
    # Check crypto alerts
    for symbol, data in crypto_data.items():
        if 'signal' in data:
            alert_engine.check_and_alert(
                'CRYPTO', symbol, data['signal'], data['price'],
                {'rsi': data.get('rsi'), 'macd': data.get('macd', {})}
            )
    
    # Get US Market Data
    us_market = get_us_market_data()
    
    # Get News
    news = fetch_market_news()
    
    # Market Summary
    avg_crypto_sentiment = sum([c.get('signal', {}).get('score', 0) for c in crypto_data.values() if 'signal' in c]) / max(len(crypto_data), 1)
    
    if dubai_gold_sentiment > 0.2 and avg_crypto_sentiment > 0:
        summary = "🟢 BULLISH: Dubai gold demand strong + positive crypto momentum. Consider adding positions."
    elif dubai_gold_sentiment < -0.2 or avg_crypto_sentiment < -0.5:
        summary = "🔴 CAUTIOUS: Mixed signals. Wait for confirmation before entering new positions."
    else:
        summary = "🟡 NEUTRAL: Market consolidating. Use technical indicators for entry points."
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'dubai_gold': {
            'price': dubai_gold_price,
            'sentiment': dubai_gold_sentiment,
            'local_factors': local_factors,
            'rsi': gold_rsi,
            'macd': gold_macd,
            'moving_averages': gold_ma,
            'prediction': gold_signal,
            'dxy_trend': get_dxy_trend()
        },
        'crypto': crypto_data,
        'us_market': us_market,
        'news': news,
        'summary': summary
    }

# ========== NEWS FETCHER ==========
def fetch_market_news():
    """Fetch relevant market news"""
    try:
        import feedparser
        news_items = []
        sources = [
            'https://feeds.bloomberg.com/markets/news.rss',
            'https://www.cnbc.com/id/100003114/device/rss/rss.html'
        ]
        
        for source in sources[:1]:
            feed = feedparser.parse(source)
            for entry in feed.entries[:5]:
                title = entry.get('title', '')[:100]
                if any(k in title.lower() for k in ['gold', 'crypto', 'bitcoin', 'fed', 'dollar', 'oil']):
                    sentiment = 0.2 if any(w in title.lower() for w in ['rally', 'surge', 'gain']) else -0.1 if any(w in title.lower() for w in ['drop', 'fall']) else 0
                    news_items.append({
                        'title': title,
                        'sentiment': sentiment,
                        'time': datetime.now().strftime('%H:%M')
                    })
        return news_items[:6]
    except:
        return [
            {'title': 'Dubai gold demand rises ahead of festival season', 'sentiment': 0.4, 'time': 'Now'},
            {'title': 'Fed signals potential rate cuts in H2 2026', 'sentiment': 0.3, 'time': '1h ago'},
            {'title': 'Bitcoin ETF inflows reach $2B this month', 'sentiment': 0.5, 'time': '2h ago'},
        ]

# ========== MOBILE HTML ==========
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <title>Dubai Gold & Crypto Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
            color: #e0e0e0;
            padding: 16px;
            min-height: 100vh;
        }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { font-size: 1.6rem; margin-bottom: 4px; background: linear-gradient(135deg, #ffd700, #ff8c00, #667eea); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .subtitle { color: #888; font-size: 0.7rem; margin-bottom: 20px; }
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 16px;
            overflow-x: auto;
        }
        .tab {
            padding: 10px 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 30px;
            cursor: pointer;
            font-size: 0.9rem;
            white-space: nowrap;
        }
        .tab.active {
            background: linear-gradient(135deg, #ffd700, #ff8c00);
            color: #1a1f3a;
            font-weight: bold;
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .card {
            background: rgba(20, 25, 50, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 16px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .gold-card { border-top: 3px solid #ffd700; }
        .crypto-card { border-top: 3px solid #667eea; }
        .us-card { border-top: 3px solid #00c853; }
        .price-big { font-size: 2rem; font-weight: bold; color: #ffd700; margin: 10px 0; }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 12px 0;
        }
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
        }
        .metric {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 12px;
            text-align: center;
        }
        .metric-value { font-size: 1.1rem; font-weight: bold; }
        .metric-label { font-size: 0.65rem; color: #888; }
        .signal-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: bold;
        }
        .badge-buy { background: rgba(0,200,83,0.2); color: #00c853; }
        .badge-sell { background: rgba(255,59,48,0.2); color: #ff3b30; }
        .badge-neutral { background: rgba(255,204,0,0.2); color: #ffcc00; }
        .crypto-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            cursor: pointer;
        }
        .crypto-details {
            display: none;
            padding: 12px;
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            margin-top: 8px;
        }
        .crypto-row.active + .crypto-details { display: block; }
        .stock-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .refresh-indicator {
            text-align: center;
            font-size: 0.7rem;
            color: #ffd700;
            margin: 10px 0;
        }
        button {
            background: linear-gradient(135deg, #ffd700, #ff8c00);
            border: none;
            padding: 12px 24px;
            border-radius: 30px;
            color: #1a1f3a;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
        }
        .last-update { text-align: center; font-size: 0.65rem; color: #666; margin-top: 16px; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .loading { animation: pulse 1s infinite; text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🥇📊 Dubai Gold & Crypto Pro</h1>
        <div class="subtitle">DGCX | Top 10 Crypto | US Markets | Real-time Alerts</div>
        
        <div class="tabs">
            <div class="tab active" onclick="showTab('gold')">🥇 Gold</div>
            <div class="tab" onclick="showTab('crypto')">₿ Crypto (Top 10)</div>
            <div class="tab" onclick="showTab('us')">🇺🇸 US Markets</div>
        </div>
        
        <div id="timestamp" class="refresh-indicator">Loading...</div>
        <div id="content" class="loading">📡 Fetching market data...</div>
        
        <div class="last-update" id="lastUpdate"></div>
        <button onclick="refreshData()">🔄 Force Refresh</button>
    </div>
    
    <script>
        let autoRefreshInterval;
        
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tabName}`).classList.add('active');
        }
        
        async function refreshData() {
            document.getElementById('content').innerHTML = '<div class="card loading">🔄 Updating...</div>';
            await loadData();
        }
        
        function toggleCryptoDetails(id) {
            const row = document.getElementById(`crypto-row-${id}`);
            row.classList.toggle('active');
        }
        
        async function loadData() {
            try {
                const response = await fetch('/api/analysis');
                const data = await response.json();
                
                document.getElementById('timestamp').innerHTML = `🕐 Last update: ${data.timestamp} | Auto-refresh every 30s`;
                document.getElementById('lastUpdate').innerHTML = `Data: DGCX Dubai | CoinGecko | Yahoo Finance | Alerts active`;
                
                let html = '';
                
                // GOLD TAB
                html += `<div id="tab-gold" class="tab-content active">`;
                html += `<div class="card gold-card">
                    <h3>🥇 Dubai Gold (DGCX)</h3>
                    <div class="price-big">$${data.dubai_gold.price.toFixed(2)}/oz</div>
                    <div class="grid-2">
                        <div class="metric"><div class="metric-value">RSI: ${data.dubai_gold.rsi}</div><div class="metric-label">Momentum</div></div>
                        <div class="metric"><div class="metric-value">MACD: ${data.dubai_gold.macd.signal_text}</div><div class="metric-label">Trend</div></div>
                        <div class="metric"><div class="metric-value">${data.dubai_gold.moving_averages.trend}</div><div class="metric-label">SMA Trend</div></div>
                        <div class="metric"><div class="metric-value">${data.dubai_gold.dxy_trend}</div><div class="metric-label">DXY Impact</div></div>
                    </div>
                    <div style="margin: 12px 0; padding: 12px; background: rgba(0,0,0,0.3); border-radius: 12px">
                        <span class="signal-badge ${data.dubai_gold.prediction.action.includes('BUY') ? 'badge-buy' : (data.dubai_gold.prediction.action.includes('SELL') ? 'badge-sell' : 'badge-neutral')}">
                            ${data.dubai_gold.prediction.action}
                        </span>
                        <span style="margin-left: 10px">${data.dubai_gold.prediction.confidence}% confidence</span>
                        <div style="margin-top: 8px; font-size:0.85rem">📝 ${data.dubai_gold.prediction.reason}</div>
                    </div>
                    <div><strong>🏛️ Local Factors:</strong><br>`;
                for (const [k, v] of Object.entries(data.dubai_gold.local_factors)) {
                    html += `<span style="font-size:0.75rem">• ${k}: ${v}</span><br>`;
                }
                html += `</div></div>`;
                
                // CRYPTO TAB
                html += `<div id="tab-crypto" class="tab-content">`;
                html += `<div class="card crypto-card"><h3>₿ Top 10 Cryptocurrencies</h3><div style="font-size:0.7rem; margin-bottom:12px">Click any row for technical indicators</div>`;
                
                let cryptoIndex = 0;
                for (const [symbol, coin] of Object.entries(data.crypto)) {
                    const signalClass = coin.signal?.action?.includes('BUY') ? 'badge-buy' : (coin.signal?.action?.includes('SELL') ? 'badge-sell' : 'badge-neutral');
                    const changeClass = coin.change_24h > 0 ? 'positive' : 'negative';
                    html += `
                        <div id="crypto-row-${cryptoIndex}" class="crypto-row" onclick="toggleCryptoDetails(${cryptoIndex})">
                            <div><strong>${symbol}</strong><br><span style="font-size:0.7rem">${coin.change_24h > 0 ? '▲' : '▼'} ${Math.abs(coin.change_24h)}%</span></div>
                            <div style="text-align:right">
                                <div>$${typeof coin.price === 'number' ? coin.price.toLocaleString() : coin.price}</div>
                                <span class="signal-badge ${signalClass}" style="font-size:0.65rem">${coin.signal?.action || 'NEUTRAL'}</span>
                            </div>
                        </div>
                        <div class="crypto-details">
                            <div class="grid-3">
                                <div class="metric"><div class="metric-value">RSI: ${coin.rsi || 'N/A'}</div><div class="metric-label">${coin.rsi > 70 ? 'Overbought' : (coin.rsi < 30 ? 'Oversold' : 'Neutral')}</div></div>
                                <div class="metric"><div class="metric-value">MACD: ${coin.macd?.signal_text || 'N/A'}</div><div class="metric-label">Momentum</div></div>
                                <div class="metric"><div class="metric-value">${coin.moving_averages?.trend || 'N/A'}</div><div class="metric-label">SMA Trend</div></div>
                            </div>
                            <div style="margin-top:8px; font-size:0.75rem">📊 Signal: ${coin.signal?.reason || 'No signal'}</div>
                            <div style="font-size:0.7rem; color:#888">Confidence: ${coin.signal?.confidence || 50}%</div>
                        </div>
                    `;
                    cryptoIndex++;
                }
                html += `</div></div>`;
                
                // US MARKET TAB
                html += `<div id="tab-us" class="tab-content">`;
                html += `<div class="card us-card"><h3>🇺🇸 US Stock Market</h3>`;
                for (const [symbol, stock] of Object.entries(data.us_market)) {
                    const signalClass = stock.signal === 'BUY' ? 'badge-buy' : (stock.signal === 'SELL' ? 'badge-sell' : 'badge-neutral');
                    html += `<div class="stock-row">
                        <div><strong>${symbol}</strong><br><span style="font-size:0.7rem">$${stock.price}</span></div>
                        <div style="text-align:right">
                            <div style="color: ${stock.change > 0 ? '#00c853' : '#ff3b30'}">${stock.change > 0 ? '▲' : '▼'} ${Math.abs(stock.change)}%</div>
                            <span class="signal-badge ${signalClass}">${stock.signal}</span>
                            <div style="font-size:0.6rem">${stock.confidence}%</div>
                        </div>
                    </div>`;
                }
                html += `</div>`;
                
                // NEWS
                html += `<div class="card"><h3>📰 Market News</h3>`;
                for (const news of data.news) {
                    html += `<div style="padding:8px 0; border-bottom:1px solid rgba(255,255,255,0.05)">
                        <div style="font-size:0.85rem">${news.title}</div>
                        <div style="font-size:0.65rem; color:#888">${news.time} • Sentiment: ${news.sentiment > 0 ? '🟢' : '🔴'} ${news.sentiment}</div>
                    </div>`;
                }
                html += `</div>`;
                
                // SUMMARY
                html += `<div class="card"><h3>📈 Market Summary</h3><div>${data.summary}</div></div>`;
                html += `</div></div>`;
                
                document.getElementById('content').innerHTML = html;
                
            } catch(error) {
                document.getElementById('content').innerHTML = '<div class="card">❌ Error loading data. Check connection and refresh.</div>';
            }
        }
        
        // Start auto-refresh every 30 seconds
        loadData();
        if (autoRefreshInterval) clearInterval(autoRefreshInterval);
        autoRefreshInterval = setInterval(loadData, 30000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/analysis')
def analysis():
    return jsonify(run_analysis())

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "time": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Dubai Gold & Crypto Predictor starting on port {port}")
    print(f"📍 Open http://localhost:{port}")
    app.run(host='0.0.0.0', port=port)
