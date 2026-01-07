import os
import requests
import time
from threading import Thread

# ===== CONFIG =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PAIR = os.environ.get("PAIR", "BTCUSDT")
MA_SHORT = int(os.environ.get("MA_SHORT", 5))
MA_LONG = int(os.environ.get("MA_LONG", 20))
INTERVAL = int(os.environ.get("INTERVAL", 60))
TP_POINTS = int(os.environ.get("TP_POINTS", 30000))
SL_POINTS = int(os.environ.get("SL_POINTS", 30000))

# ===== VARIABEL =====
prices = []
trades = []
entries = {}  # untuk masing2 strategi: {"MA": {...}, "EMA": {...}, "RSI": {...}}

# ===== FUNGSI =====
def get_price():
    try:
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={PAIR}'
        return float(requests.get(url, timeout=10).json()['price'])
    except:
        return prices[-1] if prices else 40000000

def send_telegram(message):
    print("===== Telegram =====")
    print(message)
    print("===================")
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={'chat_id': CHAT_ID, 'text': message}, timeout=10)
    except:
        print("⚠️ Gagal kirim Telegram")

def moving_average(data, period):
    if len(data) < period:
        return sum(data)/len(data)
    return sum(data[-period:])/period

def exponential_moving_average(data, period):
    if len(data) < period:
        return moving_average(data, len(data))
    k = 2/(period+1)
    ema_prev = moving_average(data[:period], period)
    for price in data[period:]:
        ema_prev = price*k + ema_prev*(1-k)
    return ema_prev

def rsi(data, period=14):
    if len(data) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        change = data[i]-data[i-1]
        if change > 0: gains += change
        else: losses -= change
    if losses==0: return 100
    rs = gains/losses
    return 100 - (100/(1+rs))

def calculate_winrate():
    if len(trades)==0: return 0
    wins = sum(1 for t in trades if t['result']=='WIN')
    return wins/len(trades)*100

# ===== STRATEGIES =====
def check_ma_strategy():
    ma_short = moving_average(prices, MA_SHORT)
    ma_long = moving_average(prices, MA_LONG)
    signal = None
    if ma_short > ma_long: signal = 'BUY'
    elif ma_short < ma_long: signal = 'SELL'
    return signal, f"MA Strategy (MA{MA_SHORT}/{MA_LONG})"

def check_ema_strategy():
    ema_short = exponential_moving_average(prices, MA_SHORT)
    ema_long = exponential_moving_average(prices, MA_LONG)
    signal = None
    if ema_short > ema_long: signal = 'BUY'
    elif ema_short < ema_long: signal = 'SELL'
    return signal, f"EMA Strategy (EMA{MA_SHORT}/{MA_LONG})"

def check_rsi_strategy():
    rsi_value = rsi(prices)
    signal = None
    if rsi_value < 30: signal = 'BUY'
    elif rsi_value > 70: signal = 'SELL'
    return signal, f"RSI Strategy (RSI14)"

strategies = [check_ma_strategy, check_ema_strategy, check_rsi_strategy]

# ===== TELEGRAM LISTENER ANTI TIMEOUT =====
def telegram_listener():
    global TP_POINTS, SL_POINTS, INTERVAL, MA_SHORT, MA_LONG, trades
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=60"
            if offset: url += f"&offset={offset}"
            updates = requests.get(url, timeout=65).json()
            for update in updates.get("result", []):
                offset = update["update_id"]+1
                msg = update.get("message", {}).get("text", "").lower()
                # ===== COMMANDS =====
                if msg.startswith("/tp"):
                    try: TP_POINTS = int(msg.split()[1]); send_telegram(f"✅ TP diubah menjadi {TP_POINTS} points")
                    except: send_telegram("Format salah. Gunakan: /tp 30000")
                elif msg.startswith("/sl"):
                    try: SL_POINTS = int(msg.split()[1]); send_telegram(f"✅ SL diubah menjadi {SL_POINTS} points")
                    except: send_telegram("Format salah. Gunakan: /sl 30000")
                elif msg.startswith("/interval"):
                    try: INTERVAL = int(msg.split()[1]); send_telegram(f"✅ Interval diubah menjadi {INTERVAL} detik")
                    except: send_telegram("Format salah. Gunakan: /interval 60")
                elif msg.startswith("/setma"):
                    try: parts = msg.split(); MA_SHORT=int(parts[1]); MA_LONG=int(parts[2]); send_telegram(f"✅ MA_SHORT={MA_SHORT}, MA_LONG={MA_LONG}")
                    except: send_telegram("Format salah. Gunakan: /setma 5 20")
                elif msg.startswith("/resetwin"):
                    trades=[]; send_telegram("♻️ Semua trade di-reset. Winrate kembali ke 0.")
                elif msg.startswith("/trades"):
                    if trades:
                        msg_text="\n".join([f"{t['strategy']} {t['signal']} Entry:{t['entry']} Exit:{t['exit']} Result:{t['result']}" for t in trades])
                        msg_text += f"\n📈 Winrate: {calculate_winrate():.2f}%"
                        send_telegram(msg_text)
                    else: send_telegram("Belum ada trade dicatat.")
                elif msg.startswith("/help"):
                    help_text=(
                        "📌 Perintah bot:\n"
                        "/tp [points]         → Ubah Take Profit\n"
                        "/sl [points]         → Ubah Stop Loss\n"
                        "/interval [detik]    → Ubah interval cek harga\n"
                        "/setma [short] [long]→ Ubah MA_SHORT & MA_LONG\n"
                        "/resetwin            → Reset semua trade & winrate\n"
                        "/trades              → Lihat riwayat trade + winrate\n"
                        "/help                → Lihat daftar perintah"
                    )
                    send_telegram(help_text)
        except requests.exceptions.ReadTimeout:
            print("⚠️ ReadTimeout Telegram API, mencoba lagi...")
            time.sleep(1)
        except Exception as e:
            print("⚠️ Error listener:", e)
            time.sleep(5)

# ===== TRADING LOOP =====
def trading_loop():
    send_telegram(f"✅ Bot Telegram Trading {PAIR} sudah aktif!\nMA_SHORT={MA_SHORT}, MA_LONG={MA_LONG}, TP={TP_POINTS}, SL={SL_POINTS}, Interval={INTERVAL}s")
    while True:
        try:
            price = get_price()
            prices.append(price)

            # cek setiap strategi
            for strat_func in strategies:
                signal, name = strat_func()
                if signal is not None:
                    # Jika belum ada entry untuk strategi ini, buat entry
                    if name not in entries:
                        entries[name] = {'signal':signal, 'entry_price':price}
                        send_telegram(f"📊 Signal {signal} dari {name}\nHarga: {price}")

            # cek TP/SL untuk semua strategi
            remove_strat = []
            for strat_name, info in entries.items():
                signal = info['signal']
                entry_price = info['entry_price']
                tp = entry_price + TP_POINTS if signal=='BUY' else entry_price - TP_POINTS
                sl = entry_price - SL_POINTS if signal=='BUY' else entry_price + SL_POINTS

                if signal=='BUY' and price>=tp:
                    trades.append({'strategy':strat_name,'signal':'BUY','entry':entry_price,'exit':price,'result':'WIN'})
                    send_telegram(f"✅ TAKE PROFIT BUY {strat_name} tercapai! Harga: {price}")
                    remove_strat.append(strat_name)
                elif signal=='BUY' and price<=sl:
                    trades.append({'strategy':strat_name,'signal':'BUY','entry':entry_price,'exit':price,'result':'LOSS'})
                    send_telegram(f"❌ STOP LOSS BUY {strat_name} tercapai! Harga: {price}")
                    remove_strat.append(strat_name)
                elif signal=='SELL' and price<=tp:
                    trades.append({'strategy':strat_name,'signal':'SELL','entry':entry_price,'exit':price,'result':'WIN'})
                    send_telegram(f"✅ TAKE PROFIT SELL {strat_name} tercapai! Harga: {price}")
                    remove_strat.append(strat_name)
                elif signal=='SELL' and price>=sl:
                    trades.append({'strategy':strat_name,'signal':'SELL','entry':entry_price,'exit':price,'result':'LOSS'})
                    send_telegram(f"❌ STOP LOSS SELL {strat_name} tercapai! Harga: {price}")
                    remove_strat.append(strat_name)

            for strat_name in remove_strat:
                entries.pop(strat_name)

            time.sleep(INTERVAL)

        except Exception as e:
            print("⚠️ Error trading loop:", e)
            time.sleep(10)

# ===== START THREAD LISTENER =====
Thread(target=telegram_listener, daemon=True).start()
trading_loop()
