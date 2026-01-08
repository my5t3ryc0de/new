import requests
import time

# ======================
# CONFIG
# ======================
TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

SYMBOL = "BTCUSDT"
INTERVAL = 30
TP_USD = 30
SL_USD = 30

prices = []
trade = None
stats = {"win": 0, "loss": 0}

# ======================
# TELEGRAM
# ======================
def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass

# ======================
# MARKET
# ======================
def get_price():
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}",
            timeout=5
        ).json()
        return float(r["price"])
    except:
        return None

def sma(data, n):
    if len(data) < n:
        return None
    return sum(data[-n:]) / n

# ======================
# STRATEGY
# ======================
def check_signal():
    ma5 = sma(prices, 5)
    ma20 = sma(prices, 20)

    if ma5 and ma20:
        if ma5 > ma20:
            return "BUY"
        elif ma5 < ma20:
            return "SELL"
    return None

# ======================
# MAIN LOOP
# ======================
send("✅ BTCUSDT BOT ULTRA STABLE AKTIF")

while True:
    try:
        price = get_price()
        if not price:
            time.sleep(10)
            continue

        prices.append(price)
        if len(prices) > 50:
            prices.pop(0)

        print("Price:", price)

        # Manage trade
        if trade:
            if trade["side"] == "BUY":
                if price >= trade["tp"]:
                    stats["win"] += 1
                    send("🎯 TP HIT ✅")
                    trade = None
                elif price <= trade["sl"]:
                    stats["loss"] += 1
                    send("🛑 SL HIT ❌")
                    trade = None

            if trade and trade["side"] == "SELL":
                if price <= trade["tp"]:
                    stats["win"] += 1
                    send("🎯 TP HIT ✅")
                    trade = None
                elif price >= trade["sl"]:
                    stats["loss"] += 1
                    send("🛑 SL HIT ❌")
                    trade = None

        # Entry
        if not trade and len(prices) >= 20:
            signal = check_signal()
            if signal:
                tp = price + TP_USD if signal == "BUY" else price - TP_USD
                sl = price - SL_USD if signal == "BUY" else price + SL_USD

                trade = {
                    "side": signal,
                    "tp": tp,
                    "sl": sl
                }

                send(
                    f"🚀 SIGNAL {signal}\n"
                    f"Entry: {price:.2f}\n"
                    f"TP: {tp:.2f}\n"
                    f"SL: {sl:.2f}"
                )

        time.sleep(INTERVAL)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(10)
