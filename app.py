import streamlit as st
import pandas as pd
import requests
import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Autonomous Algo Terminal", layout="wide", page_icon="⚡")

# --- CREDENTIALS ---
st.sidebar.header("🔑 Credentials")
dhan_client_id = st.sidebar.text_input("Dhan Client ID", type="password")
dhan_access_token = st.sidebar.text_input("Dhan Access Token", type="password")
bot_token = st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.sidebar.text_input("Telegram Chat ID")

# --- 1. STRATEGY ENGINE (9 EMA & 21 EMA CROSSOVER) ---
def evaluate_strategy(df):
    """
    df must have: 'close', 'low', 'high'
    Returns: Signal (BUY/SELL/HOLD), Entry, SL, TGT
    """
    # Calculate Indicators in pure Pandas
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    # Get latest two candles
    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]

    signal = "HOLD"
    entry = curr_candle['close']
    sl = 0
    tgt = 0

    # Bullish Crossover: 9 EMA crosses above 21 EMA
    if prev_candle['EMA_9'] <= prev_candle['EMA_21'] and curr_candle['EMA_9'] > curr_candle['EMA_21']:
        signal = "BUY"
        sl = round(curr_candle['low'] - 10, 2)  # SL 10 pts below candle low
        risk = entry - sl
        tgt = round(entry + (risk * 2), 2)     # 1:2 Risk to Reward

    # Bearish Crossover: 9 EMA crosses below 21 EMA
    elif prev_candle['EMA_9'] >= prev_candle['EMA_21'] and curr_candle['EMA_9'] < curr_candle['EMA_21']:
        signal = "SELL"
        sl = round(curr_candle['high'] + 10, 2) # SL 10 pts above candle high
        risk = sl - entry
        tgt = round(entry - (risk * 2), 2)     # 1:2 Risk to Reward

    return signal, entry, sl, tgt

# --- 2. SEND ALERT TO TELEGRAM ---
def send_telegram_alert(symbol, sec_id, action, entry, sl, tgt, qty):
    if not bot_token or not chat_id:
        st.error("Please provide Telegram details in the sidebar!")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = (
        f"🚨 <b>{action} SIGNAL TRIGGERED</b> 🚨\n\n"
        f"<b>Asset:</b> {symbol}\n"
        f"<b>Strategy:</b> EMA 9/21 Crossover\n"
        f"<b>Entry:</b> ₹{entry}\n"
        f"<b>Stop Loss:</b> ₹{sl}\n"
        f"<b>Target (1:2):</b> ₹{tgt}\n"
        f"<b>Quantity:</b> {qty}\n\n"
        f"<i>Tap below to execute directly in Dhan:</i>"
    )
    payload = {
        "chat_id": chat_id,
        "text": text,
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
        requests.post(url, json=payload)
        st.success(f"Alert sent for {symbol}!")
    except Exception as e:
        st.error(f"Telegram error: {e}")

# --- 3. EXECUTE DHAN ORDER ---
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

# --- 4. TELEGRAM BUTTON LISTENER ---
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
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": q_id, "text": "Fired in Dhan!"})
                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"✅ <b>Order Placed on Dhan!</b>\n{order_res}", "parse_mode": "HTML"})
                elif data == "IGNORE":
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": q_id, "text": "Trade Ignored."})
    except Exception:
        pass

# --- UI DASHBOARD ---
st.title("⚡ Strategy Screener & Telegram Radar")

# Watchlist to scan
watchlist = [
    {"Symbol": "NIFTY 24500 CE", "Security_ID": "49081", "Qty": 25},
    {"Symbol": "BANKNIFTY 52000 PE", "Security_ID": "49082", "Qty": 15}
]

# Time Window Condition
now = datetime.datetime.now().time()
market_open = datetime.time(9, 15)
market_close = datetime.time(15, 30)

st.write(f"Current Server Time: `{now.strftime('%H:%M:%S')}`")

if st.button("🔍 Scan Watchlist for Strategy Signals"):
    for item in watchlist:
        # Sample price data (In live trading, this comes from Dhan historical data)
        sample_df = pd.DataFrame({
            'close': [140, 142, 141, 145, 148, 152],
            'low': [138, 140, 139, 143, 146, 150],
            'high': [142, 144, 143, 147, 150, 154]
        })
        
        sig, entry, sl, tgt = evaluate_strategy(sample_df)
        
        if sig in ["BUY", "SELL"]:
            st.info(f"Signal found on **{item['Symbol']}**: `{sig}` at ₹{entry} | SL: ₹{sl} | TGT: ₹{tgt}")
            send_telegram_alert(item['Symbol'], item['Security_ID'], sig, entry, sl, tgt, item['Qty'])
        else:
            st.write(f"{item['Symbol']}: No crossover condition met (HOLD).")

# Check if you tapped CATCH
process_telegram_clicks()
