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
MAX_TRADES = 8

# =========================
# DATA STORAGE
# =========================
prices = deque(maxlen=120)
open_trades = []
stats = {}
last_signal_time = {}
last_update_id = 0

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except:
        pass

def get_updates():
    global last_update_id
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    try:
        r = requests.get(url, params={"offset": last_update_id + 1}, timeout=5).json()
        if "result" in r:
            for update in r["result"]:
                last_update_id = update["update_id"]
                if "message" in update:
                    yield update["message"]
    except:
        pass

# =========================
# COMMAND HANDLER
# =========================
def handle_command(text):
    if text == "/help":
        send_telegram(
            "📖 COMMAND LIST\n\n"
            "/help - Daftar command\n"
            "/status - Status bot\n"
            "/stats - Winrate strategi\n"
            "/setting - Setting TP/SL\n"
            "/reset - Reset statistik"
        )

    elif text == "/status":
        send_telegram(
            f"🤖 BOT STATUS\n\n"
            f"Pair: {SYMBOL}\n"
            f"Open Trade: {len(open_trades)}\n"
            f"Price Cache: {len(prices)}"
        )

    elif text == "/setting":
        send_telegram(
            f"⚙️ BOT SETTING\n\n"
            f"TP: ${TP_USD}\n"
            f"SL: ${SL_USD}\n"
            f"Interval: {INTERVAL}s\n"
            f"Max Trade: {MAX_TRADES}"
        )

    elif text == "/stats":
        if not stats:
            send_telegram("📊 Belum ada trade.")
            return

        msg = "📊 WINRATE\n\n"
        for k, v in stats.items():
            total = v["win"] + v["loss"]
            wr = (v["win"] / total) * 100 if total else 0
            msg += f"{k}\nWin: {v['win']} | Loss: {v['loss']} | WR: {wr:.1f}%\n\n"

        send_telegram(msg)

    elif text == "/reset":
        stats.clear()
        send_telegram("♻️ Statistik berhasil direset.")

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
# STRATEGIES (5 SAFE)
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
        f"🚀 SIGNAL\n\n"
        f"{strategy}\n"
        f"{direction}\n"
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
            f"📊 CLOSED\n\n"
            f"{t['strategy']}\n"
            f"Result: {result}\n"
            f"Winrate: {winrate:.1f}%"
        )

# =========================
# MAIN LOOP
# =========================
def main():
    send_telegram("✅ BTCUSDT BOT + COMMAND + WINRATE AKTIF")

    while True:
        try:
            # --- Read Commands
            for msg in get_updates():
                text = msg.get("text", "")
                if text.startswith("/"):
                    handle_command(text)

            # --- Price Update
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
