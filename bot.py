import requests
import time
from collections import deque
from datetime import datetime
import os
import threading

# =====================
# ENV VARIABLES
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")        # Telegram Bot Token
CHAT_ID = os.getenv("CHAT_ID")            # Chat ID Telegram
GOLD_API_KEY = os.getenv("GOLD_API_KEY")  # GoldAPI.io Key

# =====================
# CONFIG
# =====================
CHECK_INTERVAL = 60  # M1
LOT = 0.01
MODAL = 100
TP = 30  # pips
SL = 30  # pips

prices = deque(maxlen=50)
in_position = False
position_type = None
entry_price = 0
tp_price = 0
sl_price = 0
strategy_used = None

# Winrate tracker
total_trade = 0
win = 0
loss = 0

# Telegram command tracking
last_update_id = None

# =====================
# STRATEGI WINRATE
# =====================
strategies_winrate = {
    "EMA Crossover + Slope": 65,
    "SMA Crossover": 62,
    "SuperTrend": 63,
    "Breakout 10 Candle": 60,
    "ATR Breakout": 58,
    "Momentum 4 Candle": 55,
    "RSI Filter": 50,
    "Bollinger Band Squeeze": 57,
    "Pinbar / Candlestick": 54,
    "Inside Bar Breakout": 53,
    "Stochastic Oscillator": 52,
    "MACD Histogram": 51,
    "Donchian Channel": 59,
    "High/Low 20 Candle": 60,
    "Pivot Points": 50
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
# GET GOLD PRICE
# =====================
def get_price():
    url = "https://www.goldapi.io/api/XAU/USD"
    headers = {
        "x-access-token": GOLD_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        if "price" in data:
            return float(data["price"])
        else:
            send_telegram(f"⚠️ Gold API Error: {data}")
            return None
    except Exception as e:
        send_telegram(f"⚠️ Exception Gold API: {e}")
        return None

def ema(data, period=50):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    e = data[0]
    for p in data[1:]:
        e = p * k + e * (1 - k)
    return e

def rsi(data, period=14):
    if len(data) < period+1:
        return None
    gains, losses = 0,0
    for i in range(1, period+1):
        change = data[-i] - data[-i-1]
        if change>0: gains+=change
        else: losses -= change
    if losses==0: return 100
    rs = gains / losses
    return 100 - (100/(1+rs))

# =====================
# TELEGRAM COMMANDS
# =====================
def check_command():
    global last_update_id
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?timeout=5"
        r = requests.get(url, timeout=10)
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
                    resp = f"🤖 Bot Status\nActive: {'Yes' if in_position else 'No'}\nTotal Trade: {total_trade}\nWin: {win} | Loss: {loss}\nWinrate: {(win/total_trade*100 if total_trade>0 else 0):.2f}%"
                    send_telegram(resp)
                elif text == "/balance":
                    resp = f"💰 Modal: ${MODAL}\nLot: {LOT}\nTP: {TP} pips | SL: {SL} pips"
                    send_telegram(resp)
                elif text == "/lastsignal":
                    if in_position:
                        resp = f"📌 Last Signal: {position_type}\nEntry: {entry_price}\nTP: {tp_price}\nSL: {sl_price}\nStrategi: {strategy_used}\nPerkiraan Winrate: {strategies_winrate.get(strategy_used, 0)}%"
                    else:
                        resp = "📌 No active signal right now."
                    send_telegram(resp)
                elif text == "/winrate":
                    msg = "📊 Winrate Strategi XAU/USD M1\n\n"
                    for i, (name, rate) in enumerate(strategies_winrate.items(), start=1):
                        msg += f"{i}️⃣ {name.ljust(25)}: {rate}%\n"
                    send_telegram(msg)
                elif text == "/help":
                    msg = "/status - Cek status bot\n/balance - Cek modal & lot\n/lastsignal - Lihat sinyal terakhir\n/winrate - Lihat winrate tiap strategi\n/help - Daftar command"
                    send_telegram(msg)
    except:
        pass

# =====================
# THREAD COMMAND TELEGRAM
# =====================
def command_loop():
    while True:
        check_command()
        time.sleep(1)

threading.Thread(target=command_loop, daemon=True).start()

# =====================
# BOT START
# =====================
send_telegram("🤖 Ultimate Hybrid XAUUSD Bot M1 AKTIF")
send_telegram("✅ TEST BOT AKTIF")

# =====================
# LOOP UTAMA TRADING
# =====================
while True:
    try:
        price = get_price()
        if price is None:
            time.sleep(CHECK_INTERVAL)
            continue

        prices.append(price)
        ema50 = ema(list(prices), 50)
        ema20 = ema(list(prices), 20)
        rsi_val = rsi(list(prices), 14)
        if ema50 is None or ema20 is None:
            time.sleep(CHECK_INTERVAL)
            continue

        high = max(prices)
        low = min(prices)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        signal = None
        strategy_used = None

        # =====================
        # STRATEGI HYBRID
        # =====================
        if not in_position:
            slope = ema20 - ema(list(prices)[-21:-1], 20) if len(prices)>21 else 0
            # EMA Crossover + Slope
            if ema20 > ema50 and slope>0.05:
                signal = "BUY"
                strategy_used = "EMA Crossover + Slope"
            elif ema20 < ema50 and slope<-0.05:
                signal = "SELL"
                strategy_used = "EMA Crossover + Slope"

            # Breakout lokal 10 candle
            local_high = max(list(prices)[-10:])
            local_low = min(list(prices)[-10:])
            if price > local_high:
                signal = "BUY"
                strategy_used = "Breakout 10 Candle"
            elif price < local_low:
                signal = "SELL"
                strategy_used = "Breakout 10 Candle"

            # Momentum 4 candle
            if len(prices)>=4:
                if prices[-1]>prices[-2]>prices[-3]>prices[-4]:
                    signal = "BUY"
                    strategy_used = "Momentum 4 Candle"
                elif prices[-1]<prices[-2]<prices[-3]<prices[-4]:
                    signal = "SELL"
                    strategy_used = "Momentum 4 Candle"

            # RSI Filter
            if signal=="BUY" and rsi_val>70:
                signal=None
            if signal=="SELL" and rsi_val<30:
                signal=None

        # =====================
        # EXECUTE SIGNAL
        # =====================
        if signal and not in_position:
            in_position = True
            position_type = signal
            entry_price = price
            tp_price = entry_price + TP if signal=="BUY" else entry_price - TP
            sl_price = entry_price - SL if signal=="BUY" else entry_price + SL

            msg = f"""
📈 SIGNAL {signal} XAU/USD
Entry: {entry_price}
TP: {tp_price}
SL: {sl_price}
Strategi: {strategy_used}
Perkiraan Winrate: {strategies_winrate.get(strategy_used, 0)}%
EMA50: {ema50:.2f} | EMA20: {ema20:.2f} | RSI: {rsi_val:.2f}
High10: {local_high} | Low10: {local_low}
Time: {now}
📊 Total Trade: {total_trade} | ✅ Win: {win} | ❌ Loss: {loss} | 💯 Winrate: {(win/total_trade*100 if total_trade>0 else 0):.2f}%
"""
            send_telegram(msg)

        # =====================
        # MONITOR TP / SL
        # =====================
        if in_position:
            if position_type=="BUY":
                if price >= tp_price:
                    in_position=False
                    total_trade+=1
                    win+=1
                    send_telegram(f"✅ TP HIT (BUY) | Entry: {entry_price} | Price: {price} | Strategi: {strategy_used} | Winrate: {strategies_winrate.get(strategy_used,0)}% | Time: {now}")
                elif price <= sl_price:
                    in_position=False
                    total_trade+=1
                    loss+=1
                    send_telegram(f"❌ SL HIT (BUY) | Entry: {entry_price} | Price: {price} | Strategi: {strategy_used} | Winrate: {strategies_winrate.get(strategy_used,0)}% | Time: {now}")
            elif position_type=="SELL":
                if price <= tp_price:
                    in_position=False
                    total_trade+=1
                    win+=1
                    send_telegram(f"✅ TP HIT (SELL) | Entry: {entry_price} | Price: {price} | Strategi: {strategy_used} | Winrate: {strategies_winrate.get(strategy_used,0)}% | Time: {now}")
                elif price >= sl_price:
                    in_position=False
                    total_trade+=1
                    loss+=1
                    send_telegram(f"❌ SL HIT (SELL) | Entry: {entry_price} | Price: {price} | Strategi: {strategy_used} | Winrate: {strategies_winrate.get(strategy_used,0)}% | Time: {now}")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_telegram(f"⚠️ Error: {e}")
        time.sleep(60)
