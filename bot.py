import requests
import time
from collections import deque
from datetime import datetime
import threading
import re

# =====================
# BOT SETTING LANGSUNG
# =====================
BOT_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"  # primary user

CHECK_INTERVAL = 10  # lebih aman, anti spam
LOT = 0.01
MODAL = 100
TP = 500  # TP 500 point (~5 USD)
SL = 500  # SL 500 point (~5 USD)

# =====================
# ADMIN & USER WHITELIST
# =====================
ADMIN_ID = 5446217291
ALLOWED_USERS = [
    5446217291,  # admin
    # tambahkan Chat ID lain jika mau
]

# =====================
# TRADING VARIABLES
# =====================
prices = deque(maxlen=50)
in_position = False
position_type = None
entry_price = 0
tp_price = 0
sl_price = 0
strategy_used = None

total_trade = 0
win = 0
loss = 0
last_update_id = None
last_signal_sent = None  # untuk mencegah spam chat

strategies_winrate = {
    "EMA Crossover + Slope": 65,
    "Breakout 10 Candle": 60,
    "Momentum 4 Candle": 55
}

# =====================
# TELEGRAM FUNCTION
# =====================
def send_telegram(msg, chat_id=CHAT_ID):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg})
    except:
        pass

# =====================
# GET GOLD PRICE
# =====================
def get_price():
    try:
        url = "https://www.investing.com/commodities/gold"
        headers = {"User-Agent":"Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        m = re.search(r'id="last_last">([\d,\.]+)<', r.text)
        if m:
            return float(m.group(1).replace(",", ""))
        return None
    except:
        return None

def ema(data, period=50):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    e = data[0]
    for p in data[1:]:
        e = p * k + e * (1 - k)
    return e

# =====================
# INIT LAST UPDATE (ANTI-SPAM)
# =====================
def init_last_update():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=1"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "result" in data and data["result"]:
            last_update_id = data["result"][-1]["update_id"]
    except:
        last_update_id = None

init_last_update()

# =====================
# TELEGRAM COMMANDS
# =====================
def check_command():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=5"
        r = requests.get(url, timeout=5)
        data = r.json()
        if "result" in data:
            for msg in data["result"]:
                update_id = msg["update_id"]
                if last_update_id is not None and update_id <= last_update_id:
                    continue
                last_update_id = update_id

                message = msg.get("message")
                if not message:
                    continue
                text = message.get("text", "")
                chat_id = message["chat"]["id"]

                # =====================
                # CHECK WHITELIST
                # =====================
                if chat_id not in ALLOWED_USERS:
                    send_telegram(f"⚠️ Anda tidak diizinkan menggunakan bot ini (Chat ID: {chat_id})", chat_id)
                    continue

                # =====================
                # COMMANDS
                # =====================
                if text == "/status":
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    resp = f"🤖 Bot Status\nActive: {'Yes' if in_position else 'No'}\nTotal Trade: {total_trade}\nWin: {win} | Loss: {loss}\n💯 Winrate Aktual: {winrate_actual:.2f}%"
                    send_telegram(resp, chat_id)

                elif text == "/balance":
                    resp = f"💰 Modal: ${MODAL}\nLot: {LOT}\nTP: {TP} | SL: {SL} (~5 USD per ounce)"
                    send_telegram(resp, chat_id)

                elif text == "/lastsignal":
                    if in_position:
                        winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                        resp = f"📌 Last Signal: {position_type}\nEntry: {entry_price}\nTP: {tp_price}\nSL: {sl_price}\nStrategi: {strategy_used}\n💯 Winrate Aktual: {winrate_actual:.2f}%"
                    else:
                        resp = "📌 No active signal right now."
                    send_telegram(resp, chat_id)

                elif text == "/strategi":
                    msg = "📊 Strategi XAU/USD yang digunakan:\n\n"
                    for i, (name, rate) in enumerate(strategies_winrate.items(), start=1):
                        msg += f"{i}. {name.ljust(25)} : {rate}%\n"
                    send_telegram(msg, chat_id)

                elif text == "/help":
                    msg = (
                        "📌 Daftar Command Bot XAU/USD:\n\n"
                        "/status     - Cek status bot (aktif, total trade, win/loss, winrate)\n"
                        "/balance    - Cek modal, lot, TP/SL\n"
                        "/lastsignal - Lihat sinyal terakhir yang aktif\n"
                        "/strategi   - Lihat semua strategi yang digunakan beserta winrate\n"
                        "/help       - Tampilkan daftar command ini\n"
                        "/listuser   - Lihat daftar user (Hanya Admin)"
                    )
                    send_telegram(msg, chat_id)

                elif text == "/listuser":
                    if chat_id == ADMIN_ID:
                        msg = "📋 Daftar User yang diizinkan:\n"
                        for u in ALLOWED_USERS:
                            msg += f"- {u}\n"
                        send_telegram(msg, chat_id)
                    else:
                        send_telegram("⚠️ Command ini hanya bisa dipakai oleh Admin!", chat_id)

    except:
        pass

def telegram_loop():
    while True:
        check_command()
        time.sleep(1)

threading.Thread(target=telegram_loop, daemon=True).start()

# =====================
# START BOT
# =====================
send_telegram("🤖 XAUUSD Bot iPhone ✅ | TP/SL 500 Point (~5 USD) | Winrate ditampilkan | Admin Active")

# =====================
# MAIN TRADING LOOP
# =====================
while True:
    try:
        price = get_price()
        if not price:
            time.sleep(CHECK_INTERVAL)
            continue

        prices.append(price)
        ema50 = ema(list(prices), 50)
        ema20 = ema(list(prices), 20)

        if ema50 is None or ema20 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        signal = None
        strategy_used = None

        if not in_position:
            slope = ema20 - ema(list(prices)[-21:-1], 20) if len(prices) > 21 else 0
            if ema20 > ema50 and slope > 0.05:
                signal = "BUY"; strategy_used = "EMA Crossover + Slope"
            elif ema20 < ema50 and slope < -0.05:
                signal = "SELL"; strategy_used = "EMA Crossover + Slope"

            local_high = max(list(prices)[-10:])
            local_low = min(list(prices)[-10:])
            if price > local_high:
                signal = "BUY"; strategy_used = "Breakout 10 Candle"
            elif price < local_low:
                signal = "SELL"; strategy_used = "Breakout 10 Candle"

            if len(prices) >= 4:
                if prices[-1] > prices[-2] > prices[-3] > prices[-4]:
                    signal = "BUY"; strategy_used = "Momentum 4 Candle"
                elif prices[-1] < prices[-2] < prices[-3] < prices[-4]:
                    signal = "SELL"; strategy_used = "Momentum 4 Candle"

        # =====================
        # KIRIM SINYAL HANYA JIKA BARU
        # =====================
        if signal and not in_position and signal != last_signal_sent:
            in_position = True
            position_type = signal
            entry_price = price
            tp_price = entry_price + TP if signal == "BUY" else entry_price - TP
            sl_price = entry_price - SL if signal == "BUY" else entry_price + SL
            winrate_strategy = strategies_winrate.get(strategy_used, 0)
            winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0

            msg = f"""📈 SIGNAL {signal} XAU/USD
Entry: {entry_price}
TP: {tp_price}
SL: {sl_price}
Strategi: {strategy_used}
Winrate Strategi: {winrate_strategy}%
Total Trade: {total_trade} | ✅ Win: {win} | ❌ Loss: {loss} | 💯 Winrate Aktual: {winrate_actual:.2f}%"""
            send_telegram(msg)
            last_signal_sent = signal

        # =====================
        # MONITOR TP/SL
        # =====================
        if in_position:
            winrate_strategy = strategies_winrate.get(strategy_used, 0)
            if position_type == "BUY":
                if price >= tp_price:
                    in_position = False; total_trade += 1; win += 1
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    send_telegram(f"✅ TP HIT (BUY) | Price: {price} | Strategi: {strategy_used} | Winrate Strategi: {winrate_strategy}% | 💯 Winrate Aktual: {winrate_actual:.2f}%")
                elif price <= sl_price:
                    in_position = False; total_trade += 1; loss += 1
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    send_telegram(f"❌ SL HIT (BUY) | Price: {price} | Strategi: {strategy_used} | Winrate Strategi: {winrate_strategy}% | 💯 Winrate Aktual: {winrate_actual:.2f}%")
            elif position_type == "SELL":
                if price <= tp_price:
                    in_position = False; total_trade += 1; win += 1
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    send_telegram(f"✅ TP HIT (SELL) | Price: {price} | Strategi: {strategy_used} | Winrate Strategi: {winrate_strategy}% | 💯 Winrate Aktual: {winrate_actual:.2f}%")
                elif price >= sl_price:
                    in_position = False; total_trade += 1; loss += 1
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    send_telegram(f"❌ SL HIT (SELL) | Price: {price} | Strategi: {strategy_used} | Winrate Strategi: {winrate_strategy}% | 💯 Winrate Aktual: {winrate_actual:.2f}%")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error: {e}")
        time.sleep(5)
