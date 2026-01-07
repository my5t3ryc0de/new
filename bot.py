import requests
import time
from collections import deque
import os

# =====================
# ENV VARIABLE (Railway)
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

CHECK_INTERVAL = 60
TP_POINT = 15
SL_POINT = 10

prices = deque(maxlen=50)
in_position = False
position_type = None
entry_price = 0
tp_price = 0
sl_price = 0

# =====================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def get_price():
    url = "https://api.gold-api.com/price/XAU"
    r = requests.get(url, timeout=10)
    return float(r.json()["price"])

def ema(data, period=50):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    e = data[0]
    for p in data[1:]:
        e = p * k + e * (1 - k)
    return e

send_telegram("🤖 Bot XAUUSD Railway AKTIF")
send_telegram("✅ TEST BOT AKTIF")

while True:
    try:
        price = get_price()
        prices.append(price)

        ema50 = ema(list(prices))
        if ema50 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        high = max(prices)
        low = min(prices)

        if not in_position:
            if price < low and price > ema50:
                in_position = True
                position_type = "BUY"
                entry_price = price
                tp_price = price + TP_POINT
                sl_price = price - SL_POINT

                send_telegram(f"📈 BUY XAUUSD\nEntry: {price}\nTP: {tp_price}\nSL: {sl_price}")

            elif price > high and price < ema50:
                in_position = True
                position_type = "SELL"
                entry_price = price
                tp_price = price - TP_POINT
                sl_price = price + SL_POINT

                send_telegram(f"📉 SELL XAUUSD\nEntry: {price}\nTP: {tp_price}\nSL: {sl_price}")

        else:
            if position_type == "BUY" and price >= tp_price:
                in_position = False
                send_telegram("✅ TP HIT (BUY)")

            elif position_type == "BUY" and price <= sl_price:
                in_position = False
                send_telegram("❌ SL HIT (BUY)")

            elif position_type == "SELL" and price <= tp_price:
                in_position = False
                send_telegram("✅ TP HIT (SELL)")

            elif position_type == "SELL" and price >= sl_price:
                in_position = False
                send_telegram("❌ SL HIT (SELL)")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error: {e}")
        time.sleep(60)
