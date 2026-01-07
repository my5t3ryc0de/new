import requests
import time
from collections import deque
from datetime import datetime

# ======================
# KONFIGURASI UTAMA
# ======================
BOT_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = 5446217291  # ganti dengan chat_id kamu

PAIR = "XAUUSD"
TIMEFRAME = "M3"

CHECK_INTERVAL = 180      # M3 = 3 menit
RANGE_LOOKBACK = 20       # jumlah candle M3 untuk range
BREAKOUT_BUFFER = 10      # anti fake breakout (point)

# ======================
# STATE
# ======================
prices = deque(maxlen=100)

last_breakout = None
last_fvg = None

london_sent = False
newyork_sent = False
last_day = None

# ======================
# TELEGRAM
# ======================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )

# ======================
# MARKET DATA
# ======================
def get_price():
    url = "https://api.gold-api.com/price/XAU"
    response = requests.get(url, timeout=10)
    return float(response.json()["price"])

# ======================
# SESSION CHECK
# ======================
def check_session():
    global london_sent, newyork_sent, last_day

    now_utc = datetime.utcnow()
    wib_hour = (now_utc.hour + 7) % 24
    today = now_utc.date()

    if last_day != today:
        london_sent = False
        newyork_sent = False
        last_day = today

    if wib_hour == 14 and not london_sent:
        send_telegram(
            "🕒 LONDON SESSION OPEN\n\n"
            f"Pair : {PAIR}\n"
            "Waktu : 14:00 WIB"
        )
        london_sent = True

    if wib_hour == 19 and not newyork_sent:
        send_telegram(
            "🕒 NEW YORK SESSION OPEN\n\n"
            f"Pair : {PAIR}\n"
            "Waktu : 19:00 WIB"
        )
        newyork_sent = True

# ======================
# START BOT
# ======================
send_telegram(
    "🤖 BOT ALERT AKTIF\n\n"
    "Strategi:\n"
    "- Breakout (buffer)\n"
    "- Fair Value Gap (FVG)\n"
    "- Session London & New York\n\n"
    f"Pair : {PAIR}\n"
    f"TF : {TIMEFRAME}"
)

# ======================
# MAIN LOOP
# ======================
while True:
    try:
        check_session()

        price = get_price()
        prices.append(price)
        send_telegram(f"⏱ BOT CHECK M3 | Harga: {price}")

        if len(prices) < RANGE_LOOKBACK:
            time.sleep(CHECK_INTERVAL)
            continue

        # ======================
        # BREAKOUT LOGIC
        # ======================
        recent_prices = list(prices)[-RANGE_LOOKBACK:]
        range_high = max(recent_prices)
        range_low = min(recent_prices)

        if price > range_high + BREAKOUT_BUFFER and last_breakout != "BUY":
            last_breakout = "BUY"
            send_telegram(
                "🚀 BREAKOUT ALERT\n\n"
                f"Pair : {PAIR} {TIMEFRAME}\n"
                f"Harga : {price}\n"
                "Jenis : Breakout High\n"
                f"Buffer : {BREAKOUT_BUFFER} point"
            )

        elif price < range_low - BREAKOUT_BUFFER and last_breakout != "SELL":
            last_breakout = "SELL"
            send_telegram(
                "🚀 BREAKOUT ALERT\n\n"
                f"Pair : {PAIR} {TIMEFRAME}\n"
                f"Harga : {price}\n"
                "Jenis : Breakout Low\n"
                f"Buffer : {BREAKOUT_BUFFER} point"
            )

        # ======================
        # FVG LOGIC
        # ======================
        if len(prices) >= 3:
            if prices[-1] > prices[-3] and last_fvg != "BUY":
                last_fvg = "BUY"
                send_telegram(
                    "📦 FVG ALERT\n\n"
                    f"Pair : {PAIR} {TIMEFRAME}\n"
                    f"Harga : {price}\n"
                    "Jenis : FVG BUY"
                )

            elif prices[-1] < prices[-3] and last_fvg != "SELL":
                last_fvg = "SELL"
                send_telegram(
                    "📦 FVG ALERT\n\n"
                    f"Pair : {PAIR} {TIMEFRAME}\n"
                    f"Harga : {price}\n"
                    "Jenis : FVG SELL"
                )

        time.sleep(CHECK_INTERVAL)

    except Exception as error:
        send_telegram(f"⚠️ ERROR BOT:\n{error}")
        time.sleep(60)
