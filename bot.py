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
INTERVAL = 20
TP_USD = 40
SL_USD = 40
MAX_TRADES = 10

# =========================
# DATA STORAGE
# =========================
prices = deque(maxlen=120)
open_trades = []
stats = {}
last_signal_time = {}

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except:
        pass

# =========================
# PRICE FETCH
# =========================
def get_price():
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        r = requests.get(url, timeout=5).json()
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
# STRATEGIES (SIMPLIFIED 5)
# =========================
def run_strategies():
    signals = []
    p = prices
    last = p[-1]

    ma10 = sma(p, 10)
    ma30 = sma(p, 30)
    r = rsi(list(p))

    if ma10 and ma30:
        if ma10 > ma30:
            signals.append(("MA Trend", "BUY"))
        elif ma10 < ma30:
            signals.append(("MA Trend", "SELL"))

    if r:
        if r < 30:
            signals.append(("RSI Oversold", "BUY"))
        elif r > 70:
            signals.append(("RSI Overbought", "SELL"))

    if len(p) > 20 and last >= max(list(p)[-20:]):
        signals.append(("Breakout High", "BUY"))

    if len(p) > 20 and last <= min(list(p)[-20:]):
        signals.append(("Breakout Low", "SELL"))

    if ma30 and abs(last - ma30) / ma30 < 0.0008:
        signals.append(("Pullback", "BUY"))

    return signals

# =========================
# TRADE MANAGEMENT
# =========================
def open_trade(strategy, direction, price):
    if len(open_trades) >= MAX_TRADES:
        return

    now = time.time()
    if strategy in last_signal_time:
        if now - last_signal_time[strategy] < 120:
            return

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
    last_signal_time[strategy] = now

    if strategy not in stats:
        stats[strategy] = {"win": 0, "loss": 0}

    send_telegram(
        f"🚀 SIGNAL\n{strategy}\n{direction}\nEntry: {price:.2f}\nTP: {tp:.2f}\nSL: {sl:.2f}"
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
            f"📊 CLOSED\n{t['strategy']} | {result}\nWinrate: {winrate:.1f}%"
        )

# =========================
# MAIN LOOP
# =========================
def main():
    send_telegram("✅ BTCUSDT BOT STABLE MODE AKTIF")

    while True:
        try:
            price = get_price()
            if price is None:
                time.sleep(5)
                continue

            prices.append(price)
            print("Price:", price)

            update_trades(price)

            if len(prices) > 30:
                signals = run_strategies()
                for strategy, direction in signals:
                    if not any(t["strategy"] == strategy for t in open_trades):
                        open_trade(strategy, direction, price)

            time.sleep(INTERVAL)

        except Exception as e:
            print("Runtime error:", e)
            time.sleep(5)

main()
