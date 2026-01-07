import requests
import time
import urllib.parse

# ================= CONFIG =================
TELEGRAM_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

PAIR = "XAUUSD"
MA_SHORT = 5
MA_LONG = 20
INTERVAL = 30   # detik

TP_POINTS = 3.0   # $3
SL_POINTS = 3.0   # $3

prices = []
entries = {}

# ================= TELEGRAM =================
def send_telegram(text):
    print(text)
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(
            url,
            params={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception as e:
        print("⚠️ Telegram error:", e)

def send_chart():
    if len(prices) < 10:
        return

    data = prices[-30:]

    chart_config = {
        "type": "line",
        "data": {
            "labels": list(range(len(data))),
            "datasets": [{
                "label": "XAUUSD",
                "data": data,
                "fill": False,
                "borderColor": "gold"
            }]
        }
    }

    encoded = urllib.parse.quote(str(chart_config).replace("'", '"'))
    chart_url = f"https://quickchart.io/chart?c={encoded}"

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        requests.post(
            url,
            data={"chat_id": CHAT_ID, "photo": chart_url},
            timeout=10
        )
    except Exception as e:
        print("⚠️ Chart error:", e)

# ================= PRICE =================
def get_price():
    try:
        data = requests.get(
            "https://api.metals.live/v1/spot",
            timeout=10
        ).json()
        return float(data["gold"])
    except:
        return prices[-1] if prices else 2000.0

# ================= INDICATOR =================
def ma(data, n):
    if len(data) < n:
        return sum(data) / len(data)
    return sum(data[-n:]) / n

def ema(data, n):
    if len(data) < n:
        return ma(data, len(data))
    k = 2 / (n + 1)
    e = ma(data[:n], n)
    for p in data[n:]:
        e = p * k + e * (1 - k)
    return e

def rsi(data, n=14):
    if len(data) < n + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-n, 0):
        d = data[i] - data[i - 1]
        if d > 0:
            gains += d
        else:
            losses -= d
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

# ================= STRATEGY =================
def strategy_ma():
    s = ma(prices, MA_SHORT)
    l = ma(prices, MA_LONG)
    if s > l:
        return "BUY", "MA Strategy"
    if s < l:
        return "SELL", "MA Strategy"
    return None, None

def strategy_ema():
    s = ema(prices, MA_SHORT)
    l = ema(prices, MA_LONG)
    if s > l:
        return "BUY", "EMA Strategy"
    if s < l:
        return "SELL", "EMA Strategy"
    return None, None

def strategy_rsi():
    r = rsi(prices)
    if r < 30:
        return "BUY", "RSI Strategy"
    if r > 70:
        return "SELL", "RSI Strategy"
    return None, None

strategies = [strategy_ma, strategy_ema, strategy_rsi]

# ================= MAIN LOOP =================
def trading_loop():
    send_telegram("✅ BOT SIGNAL XAUUSD AKTIF (FREE VERSION)")

    while True:
        try:
            price = get_price()
            prices.append(price)

            print("Harga:", price)

            for strat in strategies:
                signal, name = strat()
                if signal and name not in entries:
                    entries[name] = {
                        "signal": signal,
                        "entry": price
                    }

                    send_telegram(
                        f"📊 {name}\n"
                        f"Signal: {signal}\n"
                        f"Harga: {price}"
                    )
                    send_chart()

            time.sleep(INTERVAL)

        except Exception as e:
            print("⚠️ LOOP ERROR:", e)
            time.sleep(5)

trading_loop()
