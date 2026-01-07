import requests
import time
import os
from dotenv import load_dotenv

# ===== Load environment variables =====
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PAIR = os.getenv("PAIR", "BTCUSDT")
MA_SHORT = int(os.getenv("MA_SHORT", 5))
MA_LONG = int(os.getenv("MA_LONG", 20))
INTERVAL = int(os.getenv("INTERVAL", 60))

prices = []
last_signal = None

# ===== Functions =====
def get_price():
    url = f'https://api.binance.com/api/v3/ticker/price?symbol={PAIR}'
    response = requests.get(url).json()
    return float(response['price'])

def send_telegram(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    requests.get(url, params={'chat_id': CHAT_ID, 'text': message})

def moving_average(data, period):
    if len(data) < period:
        return sum(data)/len(data)
    return sum(data[-period:])/period

# ===== Main Loop =====
while True:
    try:
        price = get_price()
        prices.append(price)
        
        ma_short = moving_average(prices, MA_SHORT)
        ma_long = moving_average(prices, MA_LONG)
        
        signal = None
        if ma_short > ma_long:
            signal = 'BUY'
        elif ma_short < ma_long:
            signal = 'SELL'
        
        if signal != last_signal and signal is not None:
            last_signal = signal
            send_telegram(f"📊 Sinyal {signal} BTC/USDT\nHarga: {price}\nMA{MA_SHORT}: {ma_short:.2f}, MA{MA_LONG}: {ma_long:.2f}")
        
        time.sleep(INTERVAL)
    
    except Exception as e:
        print("Error:", e)
        time.sleep(10)
