import streamlit as st
import pandas as pd
import requests

# Page settings
st.set_page_config(page_title="Cloud Algo Terminal", layout="wide", page_icon="⚡")

# --- SECRETS OR SIDEBAR INPUT ---
st.sidebar.header("🔑 Credentials")
dhan_client_id = st.secrets.get("DHAN_CLIENT_ID", "") or st.sidebar.text_input("Dhan Client ID", type="password")
dhan_access_token = st.secrets.get("DHAN_ACCESS_TOKEN", "") or st.sidebar.text_input("Dhan Access Token", type="password")
bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "") or st.sidebar.text_input("Telegram Bot Token", type="password")
chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "") or st.sidebar.text_input("Telegram Chat ID")

# --- FUNCTION: DISPATCH TELEGRAM ALERT WITH BUTTONS ---
def send_telegram_alert(symbol, sec_id, action, entry, sl, tgt, qty):
    if not bot_token or not chat_id:
        st.error("Please provide your Telegram Bot Token and Chat ID!")
        return
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = (
        f"🚨 <b>AUTONOMOUS SIGNAL DETECTED</b> 🚨\n\n"
        f"<b>Asset:</b> {symbol}\n"
        f"<b>Action:</b> {action}\n"
        f"<b>Entry:</b> ₹{entry}\n"
        f"<b>Stop Loss:</b> ₹{sl}\n"
        f"<b>Target:</b> ₹{tgt}\n"
        f"<b>Qty:</b> {qty}\n\n"
        f"<i>Tap below to take action on Dhan:</i>"
    )
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🎯 CATCH (Execute Trade)", "callback_data": f"CATCH_{sec_id}_{action}_{qty}"},
                    {"text": "❌ IGNORE", "callback_data": "IGNORE"}
                ]
            ]
        }
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            st.success(f"Signal sent to Telegram for {symbol}!")
        else:
            st.error(f"Telegram error: {r.text}")
    except Exception as e:
        st.error(f"Error: {e}")

# --- FUNCTION: DHAN ORDER EXECUTION ---
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

# --- CHECK FOR CATCH CLICKS FROM TELEGRAM ---
def check_for_catch():
    if not bot_token:
        return
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        res = requests.get(url).json()
        for update in res.get("result", []):
            if "callback_query" in update:
                query = update["callback_query"]
                data = query.get("data", "")
                query_id = query.get("id")
                
                if data.startswith("CATCH"):
                    _, s_id, side, q = data.split("_")
                    order_res = place_order(s_id, side, q)
                    
                    # Notify on Telegram that trade is executed
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": query_id, "text": "Trade placed on Dhan!"})
                    requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json={"chat_id": chat_id, "text": f"⚡ <b>Order Executed!</b>\nResponse: {order_res}", "parse_mode": "HTML"})
                elif data == "IGNORE":
                    requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": query_id, "text": "Signal Ignored."})
    except Exception:
        pass

# --- UI DASHBOARD ---
st.title("⚡ Autonomous F&O Algo Terminal")
st.caption("Powered by Dhan API & Telegram")

tab1, tab2 = st.tabs(["🔍 Screener & Alert Radar", "⚡ Manual Trigger"])

with tab1:
    st.subheader("Live Market Signals")
    
    # Sample signals detected by rules
    signals = [
        {"Symbol": "NIFTY 24500 CE", "Security_ID": "49081", "Action": "BUY", "Entry": 145, "SL": 125, "TGT": 185, "Qty": 25},
        {"Symbol": "BANKNIFTY 52200 PE", "Security_ID": "49082", "Action": "BUY", "Entry": 210, "SL": 180, "TGT": 270, "Qty": 15}
    ]
    st.dataframe(pd.DataFrame(signals), use_container_width=True)

    if st.button("🚀 Run Scan & Send Signals to Telegram"):
        for s in signals:
            send_telegram_alert(s["Symbol"], s["Security_ID"], s["Action"], s["Entry"], s["SL"], s["TGT"], s["Qty"])

with tab2:
    st.subheader("Direct Dhan Fire")
    col1, col2 = st.columns(2)
    with col1:
        s_id = st.text_input("Security ID", value="49081")
        trade_side = st.selectbox("Side", ["BUY", "SELL"])
    with col2:
        trade_qty = st.number_input("Quantity", value=25, step=25)
    
    if st.button("Place Test Market Order"):
        res = place_order(s_id, trade_side, trade_qty)
        st.write(res)

# Process any pending button clicks from Telegram
check_for_catch()
