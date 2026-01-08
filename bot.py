import requests
import time

TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "5446217291"
SYMBOL = "BTCUSDT"

INTERVAL = 60     # 1 menit (lebih aman)
TP_USD = 20
SL_USD = 20

last_price = None
trade = None
win = 0
loss = 0


def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except:
        pass


def get_price():
    try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}",
            timeout=5
        ).json()
        return float(r["price"])
    except:
        return None


send("✅ BTCUSDT BOT SUPER LIGHT AKTIF")

while True:
    try:
        price = get_price()
        if not price:
            time.sleep(INTERVAL)
            continue

        print("PRICE:", price)

        # ===== TRADE MANAGEMENT =====
        if trade:
            if trade["side"] == "BUY":
                if price >= trade["tp"]:
                    win += 1
                    send(f"🎯 TP HIT | WIN={win} LOSS={loss}")
                    trade = None
                elif price <= trade["sl"]:
                    loss += 1
                    send(f"🛑 SL HIT | WIN={win} LOSS={loss}")
                    trade = None

            elif trade["side"] == "SELL":
                if price <= trade["tp"]:
                    win += 1
                    send(f"🎯 TP HIT | WIN={win} LOSS={loss}")
                    trade = None
                elif price >= trade["sl"]:
                    loss += 1
                    send(f"🛑 SL HIT | WIN={win} LOSS={loss}")
                    trade = None

        # ===== ENTRY LOGIC =====
        if not trade and last_price:
            if price > last_price:
                side = "BUY"
            elif price < last_price:
                side = "SELL"
            else:
                side = None

            if side:
                tp = price + TP_USD if side == "BUY" else price - TP_USD
                sl = price - SL_USD if side == "BUY" else price + SL_USD

                trade = {
                    "side": side,
                    "tp": tp,
                    "sl": sl
                }

                send(
                    f"🚀 SIGNAL {side}\n"
                    f"Entry: {price:.2f}\n"
                    f"TP: {tp:.2f}\n"
                    f"SL: {sl:.2f}"
                )

        last_price = price
        time.sleep(INTERVAL)

    except Exception as e:
        print("ERROR:", e)
        time.sleep(INTERVAL)
