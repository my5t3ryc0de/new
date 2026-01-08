import requests
import time

# =========================
# TELEGRAM CONFIG
# =========================
TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"

# =========================
# STRATEGY CONFIG
# =========================
SYMBOL = "XAUUSD"
TIMEFRAME = "3m"

EQUAL_TOLERANCE = 0.3      # toleransi equal high/low
TP_POINT = 300
SL_POINT = 300
POINT_VALUE = 0.01        # 1 point = 0.01 harga

TP_PRICE = TP_POINT * POINT_VALUE
SL_PRICE = SL_POINT * POINT_VALUE

SCAN_INTERVAL = 30        # detik

# =========================
# GLOBAL STATE
# =========================
candles = []
active_setup = None
last_alert_id = None

# =========================
# TELEGRAM
# =========================
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text
        }, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# =========================
# PRICE DATA (FREE API)
# =========================
def get_price():
    try:
        r = requests.get("https://api.metals.live/v1/spot", timeout=10).json()
        for item in r:
            if item[0] == "gold":
                return float(item[1])
    except:
        pass
    return None

def build_candle(price):
    now = int(time.time())
    candles.append({
        "time": now,
        "open": price,
        "high": price,
        "low": price,
        "close": price
    })

    if len(candles) > 100:
        candles.pop(0)

# =========================
# LOGIC DETECTION
# =========================
def detect_equal():
    if len(candles) < 5:
        return None

    c1 = candles[-3]
    c2 = candles[-5]

    # Equal High
    if abs(c1["high"] - c2["high"]) <= EQUAL_TOLERANCE:
        return ("equal_high", max(c1["high"], c2["high"]))

    # Equal Low
    if abs(c1["low"] - c2["low"]) <= EQUAL_TOLERANCE:
        return ("equal_low", min(c1["low"], c2["low"]))

    return None

def detect_fvg():
    if len(candles) < 3:
        return None

    c0 = candles[-1]
    c2 = candles[-3]

    # Bullish FVG
    if c0["low"] > c2["high"]:
        return ("bullish", c2["high"], c0["low"])

    # Bearish FVG
    if c0["high"] < c2["low"]:
        return ("bearish", c0["high"], c2["low"])

    return None

# =========================
# MAIN LOOP
# =========================
def trading_loop():
    global active_setup, last_alert_id

    send_telegram("✅ BOT SIGNAL XAUUSD AKTIF (FREE VERSION)")

    last_price = None

    while True:
        try:
            price = get_price()
            if price is None:
                time.sleep(5)
                continue

            print("Harga:", price)

            if last_price != price:
                build_candle(price)
                last_price = price

            equal = detect_equal()
            fvg = detect_fvg()

            # ALERT 1 — SETUP
            if equal and fvg and active_setup is None:
                setup_id = f"{equal[0]}_{fvg[0]}"

                active_setup = {
                    "type": fvg[0],
                    "zone_low": min(fvg[1], fvg[2]),
                    "zone_high": max(fvg[1], fvg[2]),
                }

                send_telegram(
                    f"🟡 SETUP TERDETEKSI (M3)\n\n"
                    f"Pair: {SYMBOL}\n"
                    f"Setup: {equal[0]} + {fvg[0]} FVG\n"
                    f"Zona FVG: {active_setup['zone_low']:.2f} - {active_setup['zone_high']:.2f}\n\n"
                    f"Status: Menunggu retrace"
                )

            # ALERT 2 — ENTRY
            if active_setup:
                if active_setup["zone_low"] <= price <= active_setup["zone_high"]:
                    direction = "BUY" if active_setup["type"] == "bullish" else "SELL"

                    if direction == "BUY":
                        tp = price + TP_PRICE
                        sl = price - SL_PRICE
                    else:
                        tp = price - TP_PRICE
                        sl = price + SL_PRICE

                    send_telegram(
                        f"🟢 ENTRY SIGNAL (M3)\n\n"
                        f"Pair: {SYMBOL}\n"
                        f"Action: {direction}\n"
                        f"Entry: {price:.2f}\n"
                        f"TP: {tp:.2f}\n"
                        f"SL: {sl:.2f}\n"
                        f"Strategy: FVG + Equal"
                    )

                    active_setup = None

            time.sleep(SCAN_INTERVAL)

        except Exception as e:
            print("Loop error:", e)
            time.sleep(5)

# =========================
# START BOT
# =========================
trading_loop()
