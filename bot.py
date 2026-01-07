import requests
import time
from collections import deque
from datetime import datetime
import threading
from bs4 import BeautifulSoup

# =====================
# SETTING LANGSUNG
# =====================
BOT_TOKEN = "MASUKKAN_BOT_TOKEN_DISINI"
CHAT_ID = "MASUKKAN_CHAT_ID_DISINI"

CHECK_INTERVAL = 5  # delay super ringan
LOT = 0.01
MODAL = 100
TP = 500  # TP 500 point (~5 USD)
SL = 500  # SL 500 point (~5 USD)

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

strategies_winrate = {
    "EMA Crossover + Slope": 65,
    "Breakout 10 Candle": 60,
    "Momentum 4 Candle": 55
}

# =====================
# TELEGRAM FUNCTIONS
# =====================
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

# =====================
# GET GOLD PRICE VIA SCRAPING
# =====================
def get_price():
    try:
        url = "https://www.investing.com/commodities/gold"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        price_tag = soup.find("span", {"id": "last_last"})
        if price_tag:
            return float(price_tag.text.replace(",", ""))
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
                if chat_id != int(CHAT_ID):
                    continue

                if text == "/status":
                    winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                    resp = f"🤖 Bot Status\nActive: {'Yes' if in_position else 'No'}\nTotal Trade: {total_trade}\nWin: {win} | Loss: {loss}\n💯 Winrate Aktual: {winrate_actual:.2f}%"
                    send_telegram(resp)
                elif text == "/balance":
                    resp = f"💰 Modal: ${MODAL}\nLot: {LOT}\nTP: {TP} | SL: {SL} (~5 USD per ounce)"
                    send_telegram(resp)
                elif text == "/lastsignal":
                    if in_position:
                        winrate_actual = (win / total_trade * 100) if total_trade > 0 else 0
                        resp = f"📌 Last Signal: {position_type}\nEntry: {entry_price}\nTP: {tp_price}\nSL: {sl_price}\nStrategi: {strategy_used}\n💯 Winrate Aktual: {winrate_actual:.2f}%"
                    else:
                        resp = "📌 No active signal right now."
                    send_telegram(resp)
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
send_telegram("🤖 XAUUSD Bot tanpa API Key ✅ | TP/SL 500 Point (~5 USD) | Winrate ditampilkan")

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

        if signal and not in_position:
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
