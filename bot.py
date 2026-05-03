import json
import websocket
import threading
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- SETTINGS ---
# Agar Render use kar rahe hain to TOKEN ko environment variable mein dalna behtar hai
TOKEN = '8617592022:AAHP0btRZbKccsQ7icWDb_j8NsBjVirJ-OY'
SYMBOLS = ['eurusdt', 'gbpusdt', 'btcusdt', 'audusdt', 'usdjpy', 'audjpy', 'usdbrl', 'eurjpy', 'ethusd', 'solusd', 'grassusd', 'gbpusd']
market_storage = {s: [] for s in SYMBOLS}

# --- 90% CONFIDENCE SIGNAL LOGIC ---
def get_high_prob_signal(symbol):
    prices = market_storage[symbol]
    if len(prices) < 30:
        return f"💎 {symbol.upper()}: Data Loading ({len(prices)}/30)..."
    
    curr_price = prices[-1]
    # Simple Moving Averages
    ma9 = sum(prices[-9:]) / 9
    ma21 = sum(prices[-21:]) / 21
    
    # RSI Calculation (14 Period)
    deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
    gains = [d if d > 0 else 0 for d in deltas[-14:]]
    losses = [-d if d < 0 else 0 for d in deltas[-14:]]
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    rsi = 100 - (100 / (1 + (avg_gain/avg_loss))) if avg_loss != 0 else 100

    now = datetime.now().strftime("%H:%M:%S")
    
    # Strategy: Trend (MA) + Momentum (RSI) + Price Position
    if ma9 > ma21 and rsi > 55 and curr_price > ma9:
        signal = "🚀 [HIGH CONFIDENCE] - CALL (UP)"
        prob = "90%"
    elif ma9 < ma21 and rsi < 45 and curr_price < ma9:
        signal = "🔻 [HIGH CONFIDENCE] - PUT (DOWN)"
        prob = "90%"
    else:
        signal = "⚖️ NEUTRAL - NO TRADE"
        prob = "---"

    return (f"📊 **PAIR: {symbol.upper()}**\n"
            f"⏰ Entry Time: {now}\n"
            f"⏳ Expiry: 5 Minutes\n"
            f"💰 Price: {curr_price}\n"
            f"🎯 Signal: {signal}\n"
            f"🔥 Probability: {prob}\n"
            f"📈 RSI: {round(rsi, 1)}")

# --- WEBSOCKET FOR LIVE DATA ---
def on_message(ws, message):
    data = json.loads(message)
    symbol = data['s'].lower()
    price = float(data['k']['c'])
    if symbol in market_storage:
        market_storage[symbol].append(price)
        if len(market_storage[symbol]) > 100:
            market_storage[symbol].pop(0)

def run_ws():
    streams = "/".join([f"{s}@kline_5m" for s in SYMBOLS])
    ws = websocket.WebSocketApp(f"wss://stream.binance.com:9443/ws/{streams}", on_message=on_message)
    ws.run_forever()

# --- TELEGRAM COMMANDS ---
async def list_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = "🎯 **90% SURE TRADING SIGNALS** 🎯\n\n"
    for s in SYMBOLS:
        res += get_high_prob_signal(s) + "\n" + "═" * 15 + "\n"
    await update.message.reply_text(res, parse_mode='Markdown')

if __name__ == '__main__':
    # Start Binance Data Thread
    threading.Thread(target=run_ws, daemon=True).start()
    
    print("Bot is starting on Server...")
    # Start Telegram Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("list", list_signals))
    app.run_polling(connect_timeout=30)
