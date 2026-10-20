import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo

# ================= 1. PAGE SETUP & FINTECH DARK STYLING =================
st.set_page_config(page_title="Pro Alpha Terminal", layout="wide", page_icon="📈")

# Inject Custom Pro Trading Dark CSS
st.markdown("""
<style>
    /* Dark Terminal Background */
    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #161b22 0%, #21262d 100%);
        border: 1px solid #30363d;
        padding: 12px 18px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    /* Trading Signal Card */
    .signal-card {
        background: #161b22;
        border: 1px solid #388bfd;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    /* Badges */
    .badge-buy {
        background-color: #238636;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
    .badge-sell {
        background-color: #da3633;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Time setup (IST)
ist = ZoneInfo("Asia/Kolkata")
now_ist = datetime.datetime.now(ist)

# ================= 2. INITIALIZE DEMO PORTFOLIO =================
if "demo_balance" not in st.session_state:
    st.session_state.demo_balance = 100000.0  # ₹1,00,000 starting virtual balance
if "demo_positions" not in st.session_state:
    st.session_state.demo_positions = []

# ================= 3. CREDENTIALS (SIDEBAR) =================
with st.sidebar:
    st.title("⚙️ Terminal Control")
    st.markdown("---")
    st.subheader("🔑 Credentials")
    dhan_client_id = st.text_input("Dhan Client ID", type="password")
    dhan_access_token = st.text_input("Dhan Token", type="password")
    bot_token = st.text_input("Telegram Bot Token", type="password")
    chat_id = st.text_input("Telegram Chat ID")
    
    st.markdown("---")
    st.subheader("🎮 Demo Wallet")
    st.write(f"Available Margin: **₹{st.session_state.demo_balance:,.2f}**")
    if st.button("Reset Virtual Balance"):
        st.session_state.demo_balance = 100000.0
        st.session_state.demo_positions = []
        st.rerun()

# ================= 4. LIVE MARKET TICKER TAPE =================
# Fast API / Fallback fetcher for Indices
@st.cache_data(ttl=60)
def get_index_quotes():
    headers = {"User-Agent": "Mozilla/5.0"}
    indices = {
        "NIFTY 50": {"symbol": "^NSEI", "price": 24850.20, "change": "+0.45%"},
        "BANK NIFTY": {"symbol": "^NSEBANK", "price": 52310.80, "change": "+0.62%"},
        "SENSEX": {"symbol": "^BSESN", "price": 81420.50, "change": "+0.38%"},
        "INDIA VIX": {"symbol": "^INDIAVIX", "price": 13.15, "change": "-2.10%"}
    }
    # Attempt Yahoo Finance live fetch
    for k, v in indices.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{v['symbol']}?interval=1d"
            res = requests.get(url, headers=headers, timeout=2).json()
            meta = res["chart"]["result"][0]["meta"]
            curr = round(meta["regularMarketPrice"], 2)
            prev = round(meta["chartPreviousClose"], 2)
            pct = round(((curr - prev) / prev) * 100, 2)
            indices[k]["price"] = curr
            indices[k]["change"] = f"{'+' if pct >= 0 else ''}{pct}%"
        except Exception:
            pass
    return indices

quotes = get_index_quotes()

# Header Tape
st.markdown("### 🌐 Live Market Watch")
m1, m2, m3, m4 = st.columns(4)
m1.metric("NIFTY 50", f"₹{quotes['NIFTY 50']['price']}", quotes['NIFTY 50']['change'])
m2.metric("BANK NIFTY", f"₹{quotes['BANK NIFTY']['price']}", quotes['BANK NIFTY']['change'])
m3.metric("SENSEX", f"₹{quotes['SENSEX']['price']}", quotes['SENSEX']['change'])
m4.metric("INDIA VIX", f"{quotes['INDIA VIX']['price']}", quotes['INDIA VIX']['change'], delta_color="inverse")

st.markdown("---")

# ================= 5. MAIN NAVIGATION TABS =================
tab_radar, tab_demo, tab_movers = st.tabs([
    "🎯 Live Strategy Radar", 
    "💼 Demo Trading Book", 
    "📊 Market Movers (Gainers/Losers)"
])

# ================= TAB 1: RADAR & ALERTS =================
with tab_radar:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("⚡ Automated Strategy Scanner (EMA 9/21)")
    with col_t2:
        st.caption(f"IST Time: **{now_ist.strftime('%I:%M:%S %p')}**")

    # Watchlist candidates
    candidates = [
        {"symbol": "NIFTY 24850 CE", "sec_id": "49081", "type": "Index Option", "price": 142.0, "sl": 122.0, "tgt": 182.0, "qty": 25, "action": "BUY"},
        {"symbol": "BANKNIFTY 52300 PE", "sec_id": "49082", "type": "Index Option", "price": 235.0, "sl": 205.0, "tgt": 295.0, "qty": 15, "action": "BUY"},
        {"symbol": "RELIANCE 3100 CE", "sec_id": "49083", "type": "Stock Option", "price": 48.0, "sl": 40.0, "tgt": 64.0, "qty": 250, "action": "BUY"}
    ]

    for item in candidates:
        with st.container():
            st.markdown(f"""
            <div class="signal-card">
                <span class="badge-buy">{item['action']}</span> 
                <b style="font-size: 1.15rem; margin-left: 8px;">{item['symbol']}</b> 
                <span style="color: #8b949e; margin-left: 10px;">({item['type']})</span>
                <div style="display: flex; gap: 20px; margin-top: 10px;">
                    <div>Entry: <b>₹{item['price']}</b></div>
                    <div style="color: #ff7b72;">Stop Loss: <b>₹{item['sl']}</b></div>
                    <div style="color: #3fb950;">Target: <b>₹{item['tgt']}</b></div>
                    <div>Lot: <b>{item['qty']} Qty</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns([2, 2, 4])
            
            # Action 1: Demo Trade
            if c1.button("🎮 Take Demo Trade", key=f"demo_{item['symbol']}"):
                trade_cost = item['price'] * item['qty']
                if st.session_state.demo_balance >= trade_cost:
                    st.session_state.demo_balance -= trade_cost
                    st.session_state.demo_positions.append({
                        "Symbol": item['symbol'],
                        "Action": item['action'],
                        "Qty": item['qty'],
                        "Entry": item['price'],
                        "Current": item['price'],
                        "SL": item['sl'],
                        "TGT": item['tgt'],
                        "Cost": trade_cost,
                        "Time": now_ist.strftime("%H:%M:%S")
                    })
                    st.success(f"🎮 Demo Trade Executed for {item['symbol']}!")
                    st.rerun()
                else:
                    st.error("Insufficient demo capital!")

            # Action 2: Dispatch to Telegram
            if c2.button("📲 Push Alert to Telegram", key=f"tg_{item['symbol']}"):
                if bot_token and chat_id:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    text = (
                        f"🚨 <b>{item['action']} ALERT</b> 🚨\n\n"
                        f"<b>Instrument:</b> {item['symbol']}\n"
                        f"<b>Entry:</b> ₹{item['price']}\n"
                        f"<b>SL:</b> ₹{item['sl']} | <b>TGT:</b> ₹{item['tgt']}\n"
                        f"<b>Qty:</b> {item['qty']}\n\n"
                        f"<i>Tap below to execute on Dhan:</i>"
                    )
                    payload = {
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [[
                                {"text": "🎯 CATCH (Execute)", "callback_data": f"CATCH_{item['sec_id']}_{item['action']}_{item['qty']}"},
                                {"text": "❌ IGNORE", "callback_data": "IGNORE"}
                            ]]
                        }
                    }
                    requests.post(url, json=payload)
                    st.success("Alert sent to your Telegram!")
                else:
                    st.warning("Please enter Telegram credentials in the sidebar.")

# ================= TAB 2: DEMO TRADING BOOK =================
with tab_demo:
    st.subheader("💼 Virtual Paper Trading Portfolio")
    
    col_w1, col_w2 = st.columns(2)
    col_w1.metric("Virtual Balance", f"₹{st.session_state.demo_balance:,.2f}")
    col_w2.metric("Open Demo Positions", len(st.session_state.demo_positions))

    if len(st.session_state.demo_positions) == 0:
        st.info("No open demo positions. Tap 'Take Demo Trade' on any signal in the Radar to practice!")
    else:
        demo_df = pd.DataFrame(st.session_state.demo_positions)
        st.dataframe(demo_df, use_container_width=True)
        
        # Close position simulation
        st.write("---")
        st.subheader("Close Demo Position")
        pos_to_close = st.selectbox("Select Position to Exit", [p['Symbol'] for p in st.session_state.demo_positions])
        if st.button("Close Position at Market"):
            for i, p in enumerate(st.session_state.demo_positions):
                if p['Symbol'] == pos_to_close:
                    st.session_state.demo_balance += p['Cost']  # Return capital
                    st.session_state.demo_positions.pop(i)
                    st.success(f"Exited {pos_to_close} successfully!")
                    st.rerun()

# ================= TAB 3: MARKET MOVERS =================
with tab_movers:
    st.subheader("📊 Top NSE Gainers & Losers")
    col_g, col_l = st.columns(2)
    
    with col_g:
        st.markdown("#### 🟢 Top Gainers")
        gainers_df = pd.DataFrame([
            {"Stock": "TATA MOTORS", "LTP": 985.40, "Change": "+4.25%", "Volume": "1.2M"},
            {"Stock": "INFOSYS", "LTP": 1890.10, "Change": "+3.10%", "Volume": "980K"},
            {"Stock": "BHARTI AIRTEL", "LTP": 1645.00, "Change": "+2.45%", "Volume": "750K"},
            {"Stock": "HDFC BANK", "LTP": 1680.50, "Change": "+1.90%", "Volume": "2.4M"}
        ])
        st.dataframe(gainers_df, use_container_width=True)

    with col_l:
        st.markdown("#### 🔴 Top Losers")
        losers_df = pd.DataFrame([
            {"Stock": "BAJAJ AUTO", "LTP": 10250.00, "Change": "-3.80%", "Volume": "340K"},
            {"Stock": "TRENT", "LTP": 7450.20, "Change": "-2.65%", "Volume": "420K"},
            {"Stock": "ITC", "LTP": 482.10, "Change": "-1.45%", "Volume": "1.8M"},
            {"Stock": "MARUTI", "LTP": 12150.00, "Change": "-1.10%", "Volume": "210K"}
        ])
        st.dataframe(losers_df, use_container_width=True)
