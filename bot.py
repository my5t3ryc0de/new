import os
import requests
import time
from threading import Thread

# ===== CONFIG dari Environment Variables Railway =====
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")  # HARUS di-set di Railway
CHAT_ID = os.environ.get("CHAT_ID")                # HARUS di-set di Railway
PAIR = os.environ.get("PAIR", "BTCUSDT")
MA_SHORT = int(os.environ.get("MA_SHORT", 5))
MA_LONG = int(os.environ.get("MA_LONG", 20))
INTERVAL = int(os.environ.get("INTERVAL", 60))
TP_POINTS = int(os.environ.get("TP_POINTS", 30000))
SL_POINTS = int(os.environ.get("SL_POINTS", 30000))

# ===== VARIABEL =====
prices = []
last_signal = None
entry_price = None
entry_signal = None
trades = []

# ===== FUNGSI =====
def get_price():
    try:
        url = f'https://api.binance.com/api/v3/ticker/price?symbol={PAIR}'
        response = requests.get(url, timeout=10).json()
        return float(response['price'])
    except:
        return prices[-1] if prices else 40000000

def print_telegram_preview(message):
    print("===== Pesan Telegram =====")
    print(message)
    if trades:
        wins = sum(1 for t in trades if t['result'] == 'WIN')
        total = len(trades)
        winrate = wins / total * 100
        print(f"📈 Winrate: {winrate:.2f}% ({wins}/{total} trade)")
    print("==========================\n")

def send_telegram(message):
    print_telegram_preview(message)
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.get(url, params={'chat_id': CHAT_ID, 'text': message}, timeout=10)
    except:
        print("⚠️ Gagal mengirim Telegram")

def moving_average(data, period):
    if len(data) < period:
        return sum(data)/len(data)
    return sum(data[-period:])/period

def exponential_moving_average(data, period):
    if len(data) < period:
        return moving_average(data, len(data))
    k = 2 / (period + 1)
    ema_prev = moving_average(data[:period], period)
    for price in data[period:]:
        ema_prev = price * k + ema_prev * (1 - k)
    return ema_prev

def rsi(data, period=14):
    if len(data) < period + 1:
        return 50
    gains, losses = 0, 0
    for i in range(-period, 0):
        change = data[i] - data[i-1]
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def calculate_winrate():
    if len(trades) == 0:
        return 0
    wins = sum(1 for t in trades if t['result'] == 'WIN')
    return wins / len(trades) * 100

# ===== TELEGRAM LISTENER =====
def telegram_listener():
    global TP_POINTS, SL_POINTS, INTERVAL, MA_SHORT, MA_LONG, trades
    offset = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?timeout=100"
            if offset:
                url += f"&offset={offset}"
            updates = requests.get(url, timeout=10).json()
            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {}).get("text", "").lower()

                # ===== COMMANDS =====
                if msg.startswith("/tp"):
                    try:
                        TP_POINTS = int(msg.split()[1])
                        send_telegram(f"✅ TP diubah menjadi {TP_POINTS} points")
                    except:
                        send_telegram("Format salah. Gunakan: /tp 30000")

                elif msg.startswith("/sl"):
                    try:
                        SL_POINTS = int(msg.split()[1])
                        send_telegram(f"✅ SL diubah menjadi {SL_POINTS} points")
                    except:
                        send_telegram("Format salah. Gunakan: /sl 30000")

                elif msg.startswith("/interval"):
                    try:
                        INTERVAL = int(msg.split()[1])
                        send_telegram(f"✅ Interval diubah menjadi {INTERVAL} detik")
                    except:
                        send_telegram("Format salah. Gunakan: /interval 60")

                elif msg.startswith("/setma"):
                    try:
                        parts = msg.split()
                        if len(parts) != 3:
                            raise ValueError
                        MA_SHORT = int(parts[1])
                        MA_LONG = int(parts[2])
                        send_telegram(f"✅ MA berhasil diubah: MA_SHORT={MA_SHORT}, MA_LONG={MA_LONG}")
                    except:
                        send_telegram("Format salah. Gunakan: /setma 5 20")

                elif msg.startswith("/resetwin"):
                    trades = []
                    send_telegram("♻️ Semua trade di-reset. Winrate kembali ke 0.")

                elif msg.startswith("/trades"):
                    if trades:
                        msg_text = "\n".join([f"{t['signal']} Entry:{t['entry']} Exit:{t['exit']} Result:{t['result']}" for t in trades])
                        winrate = calculate_winrate()
                        msg_text += f"\n📈 Winrate: {winrate:.2f}%"
                        send_telegram(msg_text)
                    else:
                        send_telegram("Belum ada trade yang dicatat.")

                elif msg.startswith("/help"):
                    help_text = (
                        "📌 Daftar perintah bot:\n"
                        "/tp [points]         → Ubah Take Profit\n"
                        "/sl [points]         → Ubah Stop Loss\n"
                        "/interval [detik]    → Ubah interval cek harga\n"
                        "/setma [short] [long]→ Ubah MA_SHORT & MA_LONG\n"
                        "/resetwin            → Reset semua trade & winrate\n"
                        "/trades              → Lihat riwayat trade + winrate\n"
                        "/help                → Lihat daftar perintah"
                    )
                    send_telegram(help_text)

# ===== TRADING LOOP =====
def trading_loop():
    global last_signal, entry_price, entry_signal

    # ===== ALERT BOT AKTIF =====
    send_telegram(f"✅ Bot Telegram Trading untuk {PAIR} sudah aktif!\n"
                  f"MA_SHORT={MA_SHORT}, MA_LONG={MA_LONG}, TP={TP_POINTS}, SL={SL_POINTS}, Interval={INTERVAL}s")

    while True:
        try:
            price = get_price()
            prices.append(price)

            ma_short = moving_average(prices, MA_SHORT)
            ma_long = moving_average(prices, MA_LONG)
            ema_short = exponential_moving_average(prices, MA_SHORT)
            ema_long = exponential_moving_average(prices, MA_LONG)
            rsi_value = rsi(prices)

            signal = None
            if ma_short > ma_long and ema_short > ema_long and rsi_value < 70:
                signal = 'BUY'
            elif ma_short < ma_long and ema_short < ema_long and rsi_value > 30:
                signal = 'SELL'

            if signal != last_signal and signal is not None:
                last_signal = signal
                entry_price = price
                entry_signal = signal
                tp = entry_price + TP_POINTS if signal == 'BUY' else entry_price - TP_POINTS
                sl = entry_price - SL_POINTS if signal == 'BUY' else entry_price + SL_POINTS
                send_telegram(
                    f"📊 Sinyal {signal} {PAIR}\nHarga Masuk: {entry_price}\nMA{MA_SHORT}: {ma_short:.2f}, MA{MA_LONG}: {ma_long:.2f}\n"
                    f"EMA{MA_SHORT}: {ema_short:.2f}, EMA{MA_LONG}: {ema_long:.2f}\nRSI: {rsi_value:.2f}\nTP: {tp:.2f}, SL: {sl:.2f}"
                )

            # Notifikasi harga tiap interval
            if entry_price:
                send_telegram(f"📌 Harga sekarang: {price} | Posisi: {entry_signal}")

                if entry_signal == 'BUY':
                    if price >= entry_price + TP_POINTS:
                        trades.append({'signal':'BUY','entry':entry_price,'exit':price,'result':'WIN'})
                        send_telegram(f"✅ TAKE PROFIT BUY {PAIR} tercapai! Harga: {price}")
                        entry_price = None
                        entry_signal = None
                    elif price <= entry_price - SL_POINTS:
                        trades.append({'signal':'BUY','entry':entry_price,'exit':price,'result':'LOSS'})
                        send_telegram(f"❌ STOP LOSS BUY {PAIR} tercapai! Harga: {price}")
                        entry_price = None
                        entry_signal = None

                elif entry_signal == 'SELL':
                    if price <= entry_price - TP_POINTS:
                        trades.append({'signal':'SELL','entry':entry_price,'exit':price,'result':'WIN'})
                        send_telegram(f"✅ TAKE PROFIT SELL {PAIR} tercapai! Harga: {price}")
                        entry_price = None
                        entry_signal = None
                    elif price >= entry_price + SL_POINTS:
                        trades.append({'signal':'SELL','entry':entry_price,'exit':price,'result':'LOSS'})
                        send_telegram(f"❌ STOP LOSS SELL {PAIR} tercapai! Harga: {price}")
                        entry_price = None
                        entry_signal = None

            time.sleep(INTERVAL)

        except Exception as e:
            print("⚠️ Error trading loop:", e)
            time.sleep(10)

# ===== JALANKAN THREAD =====
Thread(target=telegram_listener, daemon=True).start()
trading_loop()
