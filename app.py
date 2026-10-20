import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo

# Page settings
st.set_page_config(page_title="Autonomous Algo Terminal", layout="wide", page_icon="⚡")

# --- INDIAN TIMEZONE (IST) ---
ist = ZoneInfo("Asia/Kolkata")
now_ist = datetime.datetime.now(ist)
current_time_str = now_ist.strftime("%I:%M:%S %p")
current_date_str = now_ist.strftime("%d-%b-%Y")

# --- SIDEBAR CREDENTIALS ---
st.sidebar.header("🔑 Credentials")
st.sidebar.caption("Open daily via web.dhan.co")
dhan_client_id = st.sidebar.text_input("Dhan Client ID", type="password")
dhan_access_token = st.sidebar.text_input("Dhan Access Token", type="password")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID")

# --- STRATEGY ENGINE (9 & 21 EMA CROSSOVER) ---
def evaluate_strategy(df):
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    signal = "HOLD"
    entry = float(curr['close'])
    sl = 0.0
    tgt = 0.0

    if prev['EMA_9'] <= prev['EMA_21'] and curr['EMA_9'] > curr['EMA_21']:
        signal = "BUY"
        sl = round(float(curr['low']) - 10, 2)
        tgt = round(entry + ((entry - sl) * 2), 2)
    elif prev['EMA_9'] >= prev['EMA_21'] and curr['EMA_9'] < curr['EMA_21']:
        signal = "SELL"
        sl = round(float(curr['high']) + 10, 2)
        tgt = round(entry - ((sl - entry) * 2), 2)

    return signal, entry, sl, tgt

# --- TELEGRAM DISPATCH ---
def send_telegram_alert(symbol, sec_id, action, entry, sl, tgt, qty):
    if not bot_token or not chat_id:
        st.error("⚠️ Enter Telegram Bot Token and Chat ID in the sidebar first!")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": (
            f"🚨 <b>{action} SIGNAL TRIGGERED</b> 🚨\n\n"
            f"<b>Instrument:</b> {symbol}\n"
            f"<b>Time:</b> {current_time_str} IST\n"
            f"<b>Entry Approx:</b> ₹{entry}\n"
            f"<b>Stop Loss:</b> ₹{sl}\n"
            f"<b>Target (1:2):</b> ₹{tgt}\n"
            f"<b>Lot Size:</b> {qty}\n\n"
            f"<i>Tap below to execute directly on Dhan:</i>"
        ),
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🎯 CATCH (Trade Now)", "callback_data": f"CATCH_{sec_id}_{action}_{qty}"},
                    {"text": "❌ IGNORE", "callback_data": "IGNORE"}
                ]
            ]
        }
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            st.success(f"✅ Alert sent for {symbol} to Telegram!")
        else:
            st.error(f"Telegram error: {r.text}")
    except Exception as e:
        st.error(f"Error: {e}")

# --- DHAN ORDER ROUTER ---
def place_order(sec_id, action, qty):
    try:
        from dhanhq import dhanhq
        dhan = dhanhq(dhan_client_id, dhan_access_token)
        side = dhan.BUY if action == "BUY" else dhan.SELL
        order = dhan.place_order(
            security_id=str(sec_id),
            exchange_segment=dhan.NSE_FNO,
            transaction_type=side,
            quantity=int(qty),
            order_type=dhan.MARKET,
            product_type=dhan.INTRADAY,
            price=0
        )
        return order
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --- TELEGRAM BUTTON LISTENER ---
def process_telegram_clicks():
    if not bot_token:
        return
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        res = requests.get(url).json()
        for update in res.get("result", []):
            if "callback_query" in update:
                query = update["callback_query"]
                data = query.get("data", "")
                q_id = query.get("id")
                
                if data.startswith("CATCH"):
                    _, s_id, side, q = data.split("_")
                    order_res = place_order(s_id, side, q)
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": q_id, "text": "Trade routed to Dhan!"})
                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚡ <b>Order Executed on Dhan!</b>\nResponse: {order_res}", "parse_mode": "HTML"})
                elif data == "IGNORE":
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": q_id, "text": "Trade Ignored."})
    except Exception:
        pass

# ================= UI =================
st.title("⚡ Autonomous F&O Algo Radar")
col1, col2, col3 = st.columns(3)
col1.metric("Current Date", current_date_str)
col2.metric("IST Market Clock", current_time_str)

market_open = datetime.time(9, 15)
market_close = datetime.time(15, 30)
is_open = market_open <= now_ist.time() <= market_close
col3.metric("Market Status", "OPEN 🟢" if is_open else "CLOSED 🔴")

st.write("---")

watchlist = [
    {"Symbol": "NIFTY 24500 CE", "Security_ID": "49081", "Qty": 25},
    {"Symbol": "BANKNIFTY 52000 PE", "Security_ID": "49082", "Qty": 15}
]

st.subheader("Strategy Radar (9/21 EMA Crossover)")

if st.button("🚀 Run Live Scan Cycle"):
    for item in watchlist:
        # Sample price candles simulating market movements
        sample_df = pd.DataFrame({
            'close': [140.0, 141.5, 142.0, 145.0, 148.0, 153.0],
            'low': [138.0, 139.0, 140.0, 143.0, 145.0, 150.0],
            'high': [142.0, 143.0, 144.0, 147.0, 150.0, 155.0]
        })
        
        sig, entry, sl, tgt = evaluate_strategy(sample_df)
        if sig in ["BUY", "SELL"]:
            st.info(f"Signal found on **{item['Symbol']}**: `{sig}` | Entry: ₹{entry} | SL: ₹{sl} | TGT: ₹{tgt}")
            send_telegram_alert(item['Symbol'], item['Security_ID'], sig, entry, sl, tgt, item['Qty'])

# Process Telegram button responses
process_telegram_clicks()
