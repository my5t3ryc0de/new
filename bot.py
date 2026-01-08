import requests
import time
from collections import deque

# =========================
# TELEGRAM CONFIG
# =========================
TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

# =========================
# MARKET CONFIG
# =========================
SYMBOL = "BTCUSDT"
INTERVAL = 15   # seconds
TP_USD = 50     # take profit $50
SL_USD = 50     # stop loss $50

# =========================
# DATA STORAGE
# =========================
prices = deque(maxlen=200)
open_trades = []     # active trades
stats = {}           # winrate per strategy

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# =========================
# PRICE FETCH
# =========================
def get_price():
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        r = requests.get(url, timeout=10).json()
        return float(r["price"])
    except:
        return None

# =========================
# INDICATORS
# =========================
def sma(data, n):
    if len(data) < n:
        return None
    return sum(list(data)[-n:]) / n

def ema(data, n):
    if len(data) < n:
        return None
    k = 2 / (n + 1)
    ema_val = data[0]
    for p in data:
        ema_val = p * k + ema_val * (1 - k)
    return ema_val

def rsi(data, n=14):
    if len(data) < n + 1:
        return None
    gains, losses = 0, 0
    for i in range(-n, -1):
        diff = data[i+1] - data[i]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

# =========================
# STRATEGY ENGINE (10)
# =========================
def run_strategies():
    signals = []
    p = prices

    ma5 = sma(p, 5)
    ma20 = sma(p, 20)
    ema9 = ema(list(p)[-30:], 9)
    ema21 = ema(list(p)[-30:], 21)
    r = rsi(list(p))

    last = p[-1]

    # 1. MA crossover
    if ma5 and ma20:
        if ma5 > ma20:
            signals.append(("MA Crossover", "BUY"))
        elif ma5 < ma20:
            signals.append(("MA Crossover", "SELL"))

    # 2. EMA crossover
    if ema9 and ema21:
        if ema9 > ema21:
            signals.append(("EMA Crossover", "BUY"))
        elif ema9 < ema21:
            signals.append(("EMA Crossover", "SELL"))

    # 3. RSI
    if r:
        if r < 30:
            signals.append(("RSI Oversold", "BUY"))
        elif r > 70:
            signals.append(("RSI Overbought", "SELL"))

    # 4. Momentum
    if len(p) > 10 and p[-1] > p[-10]:
        signals.append(("Momentum", "BUY"))
    elif len(p) > 10 and p[-1] < p[-10]:
        signals.append(("Momentum", "SELL"))

    # 5. Breakout High
    if len(p) > 30 and last >= max(list(p)[-30:]):
        signals.append(("High Breakout", "BUY"))

    # 6. Breakout Low
    if len(p) > 30 and last <= min(list(p)[-30:]):
        signals.append(("Low Breakout", "SELL"))

    # 7. Pullback MA
    if ma20 and abs(last - ma20) / ma20 < 0.001:
        signals.append(("Pullback MA", "BUY"))

    # 8. Volatility spike
    if len(p) > 5 and abs(p[-1] - p[-5]) > 100:
        signals.append(("Volatility Spike", "BUY" if p[-1] > p[-5] else "SELL"))

    # 9. Trend continuation
    if len(p) > 50 and p[-1] > p[-50]:
        signals.append(("Trend Continuation", "BUY"))

    # 10. Mean reversion
    if ma20:
        if last > ma20 * 1.01:
            signals.append(("Mean Reversion", "SELL"))
        elif last < ma20 * 0.99:
            signals.append(("Mean Reversion", "BUY"))

    return signals

# =========================
# TRADE MANAGEMENT
# =========================
def open_trade(strategy, direction, price):
    tp = price + TP_USD if direction == "BUY" else price - TP_USD
    sl = price - SL_USD if direction == "BUY" else price + SL_USD

    trade = {
        "strategy": strategy,
        "direction": direction,
        "entry": price,
        "tp": tp,
        "sl": sl
    }

    open_trades.append(trade)

    if strategy not in stats:
        stats[strategy] = {"win": 0, "loss": 0}

    send_telegram(
        f"🚀 SIGNAL ENTRY\n\n"
        f"Pair: {SYMBOL}\n"
        f"Strategy: {strategy}\n"
        f"Action: {direction}\n"
        f"Entry: {price:.2f}\n"
        f"TP: {tp:.2f}\n"
        f"SL: {sl:.2f}"
    )

def update_trades(price):
    closed = []
    for t in open_trades:
        if t["direction"] == "BUY":
            if price >= t["tp"]:
                stats[t["strategy"]]["win"] += 1
                closed.append((t, "WIN"))
            elif price <= t["sl"]:
                stats[t["strategy"]]["loss"] += 1
                closed.append((t, "LOSS"))
        else:
            if price <= t["tp"]:
                stats[t["strategy"]]["win"] += 1
                closed.append((t, "WIN"))
            elif price >= t["sl"]:
                stats[t["strategy"]]["loss"] += 1
                closed.append((t, "LOSS"))

    for t, result in closed:
        open_trades.remove(t)
        s = stats[t["strategy"]]
        total = s["win"] + s["loss"]
        winrate = (s["win"] / total) * 100 if total else 0

        send_telegram(
            f"📊 TRADE CLOSED\n\n"
            f"Strategy: {t['strategy']}\n"
            f"Result: {result}\n"
            f"Total Trade: {total}\n"
            f"Win: {s['win']} | Loss: {s['loss']}\n"
            f"Winrate: {winrate:.2f}%"
        )

# =========================
# MAIN LOOP
# =========================
def main():
    send_telegram("✅ BOT BTCUSDT MULTI-STRATEGY AKTIF (10 STRATEGI)")

    while True:
        try:
            price = get_price()
            if price is None:
                time.sleep(5)
                continue

            prices.append(price)
            print("Price:", price)

            # Check open trades
            update_trades(price)

            # Generate signals
            signals = run_strategies()
            for strategy, direction in signals:
                # prevent spam: only 1 trade per strategy active
                if not any(t["strategy"] == strategy for t in open_trades):
                    open_trade(strategy, direction, price)

            time.sleep(INTERVAL)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(5)

# =========================
# START
# =========================
main()
