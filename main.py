from flask import Flask, request, jsonify
import requests

BOT_TOKEN = "8009906926:AAEyuRMx4elUM6Xfbx7Kp9uH_Ix6ww86DJ4"
CHAT_ID = "@mysterycodebot"

TP_POINT = 5000
SL_POINT = 5000

total_trade = 0
win = 0
loss = 0

app = Flask(__name__)

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

@app.route("/webhook", methods=["POST"])
def webhook():
    global total_trade, win, loss

    data = request.json
    event = data.get("event")  # ENTRY / TP / SL
    signal = data.get("signal")
    price = float(data.get("price", 0))
    reason = data.get("reason", "")

    if event == "ENTRY":
        msg = (
            f"🔔 SIGNAL {signal} XAUUSD (M5)\n\n"
            f"Entry : {price}\n"
            f"Alasan : {reason}\n"
            f"TP : {price + TP_POINT if signal=='BUY' else price - TP_POINT}\n"
            f"SL : {price - SL_POINT if signal=='BUY' else price + SL_POINT}"
        )
        send_telegram(msg)

    elif event == "TP":
        total_trade += 1
        win += 1
        winrate = (win / total_trade) * 100
        send_telegram(
            f"✅ TAKE PROFIT HIT\n\n"
            f"Result : WIN\n"
            f"Total Trade : {total_trade}\n"
            f"Win : {win} | Loss : {loss}\n"
            f"Winrate : {winrate:.2f}%"
        )

    elif event == "SL":
        total_trade += 1
        loss += 1
        winrate = (win / total_trade) * 100
        send_telegram(
            f"❌ STOP LOSS HIT\n\n"
            f"Result : LOSS\n"
            f"Total Trade : {total_trade}\n"
            f"Win : {win} | Loss : {loss}\n"
            f"Winrate : {winrate:.2f}%"
        )

    return jsonify({"status": "ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
