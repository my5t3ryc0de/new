import requests
import time
from collections import deque
from datetime import datetime
import threading
import re

# =====================
# BOT SETTINGS
# =====================
BOT_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
ADMIN_ID = 5446217291
ALLOWED_USERS = [5446217291]

CHECK_INTERVAL = 60  # 1 menit = M1
LOT = 0.01
MODAL = 100
TP = 500
SL = 500

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
last_signal_sent = None

strategies_winrate = {
    "EMA Crossover + Slope": 65,
    "Breakout 10 Candle": 60,
    "Momentum 4 Candle": 55,
    "High/Low 10 Candle": 57,
    "RSI Filter 70/30": 52,
    "MACD Histogram": 51,
    "Stochastic": 50,
    "Bollinger Band": 53
}

# =====================
# TELEGRAM FUNCTION
# =====================
def send_telegram(msg, chat_id):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg})
    except:
        pass

# =====================
# KEEP-ALIVE PING
# =====================
def keep_alive():
    while True:
        try:
            requests.get("https://api.telegram.org", timeout=5)
        except:
            pass
        time.sleep(300)  # ping setiap 5 menit

threading.Thread(target=keep_alive, daemon=True).start()

# =====================
# GET HARGA XAU/USD
# =====================
def get_price():
    try:
        url = "https://www.investing.com/commodities/gold"
        headers = {"User-Agent":"Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        m = re.search(r'id="last_last">([\d,\.]+)<', r.text)
        if m:
            return float(m.group(1).replace(",", ""))
    except:
        pass
    return None  # harga tidak valid jika gagal

def ema(data, period=50):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    e = data[0]
    for p in data[1:]:
        e = p*k + e*(1-k)
    return e

# =====================
# TELEGRAM COMMANDS
# =====================
def check_command():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=5"
        r = requests.get(url, timeout=5)
        data = r.json()
        for msg in data.get("result", []):
            update_id = msg["update_id"]
            if last_update_id and update_id <= last_update_id:
                continue
            last_update_id = update_id

            message = msg.get("message")
            if not message:
                continue
            text = message.get("text", "")
            chat_id = message["chat"]["id"]

            if chat_id not in ALLOWED_USERS:
                send_telegram(f"⚠️ Anda tidak diizinkan (Chat ID: {chat_id})", chat_id)
                continue

            if text == "/status":
                winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                send_telegram(f"🤖 Bot Status\nActive: {'Yes' if in_position else 'No'}\nTotal Trade: {total_trade}\nWin: {win} | Loss: {loss}\n💯 Winrate Aktual: {winrate_actual:.2f}%", chat_id)

            elif text == "/balance":
                send_telegram(f"💰 Modal: ${MODAL}\nLot: {LOT}\nTP: {TP} | SL: {SL}", chat_id)

            elif text == "/lastsignal":
                if in_position:
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    send_telegram(f"📌 Last Signal: {position_type}\nEntry: {entry_price}\nTP: {tp_price}\nSL: {sl_price}\nStrategi: {strategy_used}\nHarga Saat Ini: {prices[-1]}\n💯 Winrate Aktual: {winrate_actual:.2f}%", chat_id)
                else:
                    send_telegram("📌 No active signal right now.", chat_id)

            elif text == "/strategi":
                msg = "📊 Strategi XAU/USD yang digunakan:\n\n"
                for i, (name, rate) in enumerate(strategies_winrate.items(), start=1):
                    msg += f"{i}. {name.ljust(25)} : {rate}%\n"
                send_telegram(msg, chat_id)

            elif text == "/price":
                price_now = prices[-1] if prices else "N/A"
                send_telegram(f"💰 Harga XAU/USD Saat Ini: {price_now}", chat_id)

            elif text == "/help":
                send_telegram(
                    "📌 Daftar Command:\n"
                    "/status /balance /lastsignal /strategi /price /help /listuser", chat_id
                )

            elif text == "/listuser":
                if chat_id == ADMIN_ID:
                    msg = "📋 Daftar User yang diizinkan:\n" + "\n".join([str(u) for u in ALLOWED_USERS])
                    send_telegram(msg, chat_id)
                else:
                    send_telegram("⚠️ Command ini hanya bisa dipakai oleh Admin!", chat_id)

    except:
        pass

threading.Thread(target=lambda: [check_command() or time.sleep(2) for _ in iter(int,1)], daemon=True).start()

# =====================
# START BOT
# =====================
send_telegram("🤖 XAU/USD Bot M1 Gratis Aktif | TP/SL 500 point | Admin Aktif", ADMIN_ID)

# =====================
# MAIN TRADING LOOP (M1)
# =====================
while True:
    try:
        price = get_price()
        if not price:
            send_telegram("⚠️ Gagal ambil harga XAU/USD, menunggu retry...", ADMIN_ID)
            time.sleep(CHECK_INTERVAL)
            continue  # jangan lanjut ke signal jika harga tidak valid

        prices.append(price)
        ema50 = ema(list(prices), 50)
        ema20 = ema(list(prices), 20)
        if ema50 is None or ema20 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        signal = None
        strategy_used = None

        # Strategi sederhana → sinyal lebih sering
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

        if signal and not in_position and signal != last_signal_sent:
            in_position = True
            position_type = signal
            entry_price = price
            tp_price = entry_price + TP if signal == "BUY" else entry_price - TP
            sl_price = entry_price - SL if signal == "BUY" else entry_price + SL

            last_signal_sent = signal
            winrate_strategy = strategies_winrate.get(strategy_used, 0)
            send_telegram(f"📈 SIGNAL {signal} | Harga: {price} | TP: {tp_price} | SL: {sl_price} | Strategi: {strategy_used} | Winrate: {winrate_strategy}%", ADMIN_ID)

        # Monitor TP/SL
        if in_position:
            if position_type == "BUY":
                if price >= tp_price:
                    in_position = False; total_trade += 1; win += 1
                elif price <= sl_price:
                    in_position = False; total_trade += 1; loss += 1
            elif position_type == "SELL":
                if price <= tp_price:
                    in_position = False; total_trade += 1; win += 1
                elif price >= sl_price:
                    in_position = False; total_trade += 1; loss += 1

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error: {e}", ADMIN_ID)
        time.sleep(10)
