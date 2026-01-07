import requests
import time
from collections import deque
from datetime import datetime
import os
import matplotlib.pyplot as plt
from io import BytesIO

# =====================
# ENV VARIABLE (Railway)
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =====================
# CONFIG
# =====================
CHECK_INTERVAL = 60  # M1
LOT = 0.01
MODAL = 100
TP1 = 5
TP2 = 10
SL = 5

prices = deque(maxlen=50)
in_position = False
position_type = None
entry_price = 0
tp1_price = 0
tp2_price = 0
sl_price = 0
tp1_hit = False

# Winrate tracker
total_trade = 0
win = 0
loss = 0

# =====================
# TELEGRAM FUNCTIONS
# =====================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

def send_chart(prices, entry=None, tp1=None, tp2=None, sl=None):
    plt.figure(figsize=(5,3))
    plt.plot(prices, label="Price")
    if entry: plt.axhline(entry, color='green', linestyle='--', label="Entry")
    if tp1: plt.axhline(tp1, color='blue', linestyle='--', label="TP1")
    if tp2: plt.axhline(tp2, color='cyan', linestyle='--', label="TP2")
    if sl: plt.axhline(sl, color='red', linestyle='--', label="SL")
    plt.legend()
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    files = {'photo': buf}
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, files=files, data={"chat_id": CHAT_ID})

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

# =====================
# TELEGRAM COMMANDS
# =====================
def check_command():
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "result" in data and len(data["result"]) > 0:
            for msg in data["result"]:
                message = msg["message"]
                text = message.get("text", "")
                chat_id = message["chat"]["id"]
                if chat_id != int(CHAT_ID):
                    continue

                if text == "/status":
                    resp = f"🤖 Bot Status\nActive: {'Yes' if in_position or prices else 'No'}\nTotal Trade: {total_trade}\nWin: {win} | Loss: {loss}\nWinrate: {(win/total_trade*100 if total_trade>0 else 0):.2f}%"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": resp})

                elif text == "/balance":
                    resp = f"💰 Modal: ${MODAL}\nLot: {LOT}\nTP1: ${TP1} | TP2: ${TP2} | SL: ${SL}"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": resp})

                elif text == "/lastsignal":
                    if in_position:
                        resp = f"📌 Last Signal: {position_type}\nEntry: {entry_price}\nTP1: {tp1_price} | TP2: {tp2_price}\nSL: {sl_price}"
                    else:
                        resp = "📌 No active signal right now."
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": resp})

                elif text == "/help":
                    resp = "/status - Cek status bot\n/balance - Cek modal & lot\n/lastsignal - Lihat sinyal terakhir\n/help - Daftar command"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": resp})

    except Exception as e:
        pass

# =====================
# BOT START
# =====================
send_telegram("🤖 Ultimate XAUUSD Bot M1 AKTIF")
send_telegram("✅ TEST BOT AKTIF")

# =====================
# LOOP UTAMA
# =====================
while True:
    try:
        # ✅ Cek command Telegram
        check_command()
        
        # ✅ Ambil harga & strategi
        price = get_price()
        prices.append(price)
        ema50 = ema(list(prices))
        if ema50 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        high = max(prices)
        low = min(prices)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        signal = None

        # Strategi EMA Sweep + Momentum
        if not in_position:
            if price < low and price > ema50:
                signal = "BUY"
            elif price > high and price < ema50:
                signal = "SELL"
            elif len(prices) >= 4:
                if prices[-1] > prices[-2] > prices[-3] > prices[-4]:
                    signal = "BUY"
                elif prices[-1] < prices[-2] < prices[-3] < prices[-4]:
                    signal = "SELL"

        # Execute signal
        if signal and not in_position:
            in_position = True
            position_type = signal
            entry_price = price
            tp1_price = entry_price + TP1 if signal=="BUY" else entry_price - TP1
            tp2_price = entry_price + TP2 if signal=="BUY" else entry_price - TP2
            sl_price = entry_price - SL if signal=="BUY" else entry_price + SL
            tp1_hit = False

            msg = f"""
📈 SIGNAL {signal} XAU/USD
Entry: {entry_price}
TP1: {tp1_price} | TP2: {tp2_price}
SL: {sl_price}

High50: {high} | Low50: {low} | EMA50: {ema50:.2f}
Time: {now}

📊 Total Trade: {total_trade} | ✅ Win: {win} | ❌ Loss: {loss} | 💯 Winrate: {(win/total_trade*100 if total_trade>0 else 0):.2f}%
"""
            send_telegram(msg)
            send_chart(list(prices), entry_price, tp1_price, tp2_price, sl_price)

        # Monitor TP / SL Multiple
        if in_position:
            if position_type=="BUY":
                if not tp1_hit and price >= tp1_price:
                    tp1_hit = True
                    send_telegram(f"✅ TP1 HIT (BUY) | Entry: {entry_price} | Price: {price} | Time: {now}")
                elif tp1_hit and price >= tp2_price:
                    in_position = False
                    total_trade += 1
                    win += 1
                    send_telegram(f"✅ TP2 HIT (BUY) | Entry: {entry_price} | Price: {price} | Time: {now} | Winrate: {(win/total_trade*100):.2f}%")
                elif price <= sl_price:
                    in_position = False
                    total_trade += 1
                    loss += 1
                    send_telegram(f"❌ SL HIT (BUY) | Entry: {entry_price} | Price: {price} | Time: {now} | Winrate: {(win/total_trade*100):.2f}%")
            elif position_type=="SELL":
                if not tp1_hit and price <= tp1_price:
                    tp1_hit = True
                    send_telegram(f"✅ TP1 HIT (SELL) | Entry: {entry_price} | Price: {price} | Time: {now}")
                elif tp1_hit and price <= tp2_price:
                    in_position = False
                    total_trade += 1
                    win += 1
                    send_telegram(f"✅ TP2 HIT (SELL) | Entry: {entry_price} | Price: {price} | Time: {now} | Winrate: {(win/total_trade*100):.2f}%")
                elif price >= sl_price:
                    in_position = False
                    total_trade += 1
                    loss += 1
                    send_telegram(f"❌ SL HIT (SELL) | Entry: {entry_price} | Price: {price} | Time: {now} | Winrate: {(win/total_trade*100):.2f}%")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error: {e}")
        time.sleep(60)
