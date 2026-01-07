import requests
import time
from collections import deque

# ======================
# KONFIGURASI
# ======================
BOT_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

PAIR = "XAUUSD"
CHECK_INTERVAL = 60  # 1 menit

TP_POINT = 5000
SL_POINT = 5000

# ======================
# STATE (TANPA DATABASE)
# ======================
prices = deque(maxlen=60)
in_position = False
position_type = None
entry_price = 0
tp_price = 0
sl_price = 0

total_trade = 0
win = 0
loss = 0

# ======================
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
    ema_val = data[0]
    for p in data[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return ema_val

# ======================
send_telegram("🤖 Bot trading XAUUSD AKTIF (cek tiap 1 menit)")

while True:
    try:
        price = get_price()
        prices.append(price)

        ema50 = ema(list(prices), 50)
        if ema50 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        prev_high = max(prices)
        prev_low = min(prices)

        # ======================
        # ENTRY
        # ======================
        if not in_position:
            # BUY
            if price < prev_low and price > ema50:
                in_position = True
                position_type = "BUY"
                entry_price = price
                tp_price = price + TP_POINT
                sl_price = price - SL_POINT

                send_telegram(
                    f"🔔 SIGNAL BUY XAUUSD (M5)\n\n"
                    f"Entry : {entry_price}\n"
                    f"Alasan : Sweep low + EMA50\n"
                    f"TP : {tp_price}\n"
                    f"SL : {sl_price}"
                )

            # SELL
            elif price > prev_high and price < ema50:
                in_position = True
                position_type = "SELL"
                entry_price = price
                tp_price = price - TP_POINT
                sl_price = price + SL_POINT

                send_telegram(
                    f"🔔 SIGNAL SELL XAUUSD (M5)\n\n"
                    f"Entry : {entry_price}\n"
                    f"Alasan : Sweep high + EMA50\n"
                    f"TP : {tp_price}\n"
                    f"SL : {sl_price}"
                )

        # ======================
        # MONITOR TP / SL
        # ======================
        else:
            if position_type == "BUY":
                if price >= tp_price:
                    total_trade += 1
                    win += 1
                    in_position = False

                elif price <= sl_price:
                    total_trade += 1
                    loss += 1
                    in_position = False

            elif position_type == "SELL":
                if price <= tp_price:
                    total_trade += 1
                    win += 1
                    in_position = False

                elif price >= sl_price:
                    total_trade += 1
                    loss += 1
                    in_position = False

            if not in_position:
                winrate = (win / total_trade) * 100 if total_trade > 0 else 0
                send_telegram(
                    f"📊 HASIL TRADE\n\n"
                    f"Total : {total_trade}\n"
                    f"Win : {win} | Loss : {loss}\n"
                    f"Winrate : {winrate:.2f}%"
                )

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error bot: {e}")
        time.sleep(60)
