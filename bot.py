import requests
import time
from threading import Thread
import matplotlib.pyplot as plt

# ================= CONFIG =================
TELEGRAM_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

PAIR = "XAUUSD"
MA_SHORT = 5
MA_LONG = 20
INTERVAL = 30

TP_POINTS = 3.0
SL_POINTS = 3.0

prices = []
entries = {}
trades = []

def send_telegram(text):
    print(text)
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=10)
    except:
        print("Telegram error")

def get_price():
    try:
        data = requests.get("https://api.metals.live/v1/spot", timeout=10).json()
        return float(data["gold"])
    except:
        return prices[-1] if prices else 2000

def ma(data, n):
    if len(data) < n:
        return sum(data)/len(data)
    return sum(data[-n:]) / n

def ema(data, n):
    if len(data) < n:
        return ma(data, len(data))
    k = 2/(n+1)
    e = ma(data[:n], n)
    for p in data[n:]:
        e = p*k + e*(1-k)
    return e

def rsi(data, n=14):
    if len(data) < n+1:
        return 50
    gains, losses = 0, 0
    for i in range(-n, 0):
        d = data[i] - data[i-1]
        if d > 0: gains += d
        else: losses -= d
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100/(1+rs))

def send_chart():
    if len(prices) < 10:
        return
    import matplotlib.pyplot as plt
    plt.figure(figsize=(6,3))
    plt.plot(prices[-50:])
    plt.title("XAUUSD")
    plt.savefig("chart.png")
    plt.close()

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open("chart.png", "rb") as f:
            requests.post(url, files={"photo": f}, data={"chat_id": CHAT_ID})
    except:
        print("Chart error")

def strategy_ma():
    s = ma(prices, MA_SHORT)
    l = ma(prices, MA_LONG)
    if s > l: return "BUY", "MA Strategy"
    if s < l: return "SELL", "MA Strategy"
    return None, None

def strategy_ema():
    s = ema(prices, MA_SHORT)
    l = ema(prices, MA_LONG)
    if s > l: return "BUY", "EMA Strategy"
    if s < l: return "SELL", "EMA Strategy"
    return None, None

def strategy_rsi():
    r = rsi(prices)
    if r < 30: return "BUY", "RSI Strategy"
    if r > 70: return "SELL", "RSI Strategy"
    return None, None

strategies = [strategy_ma, strategy_ema, strategy_rsi]

def trading_loop():
    send_telegram("✅ BOT XAUUSD AKTIF")

    while True:
        try:
            price = get_price()
            prices.append(price)

            for strat in strategies:
                signal, name = strat()
                if signal and name not in entries:
                    entries[name] = {"signal": signal, "entry": price}
                    send_telegram(f"📊 {name}\nSignal: {signal}\nHarga: {price}")
                    send_chart()

            time.sleep(INTERVAL)
        except Exception as e:
            print("ERROR:", e)
            time.sleep(5)

trading_loop()
