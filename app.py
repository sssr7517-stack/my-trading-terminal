import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo

# ================= 1. PAGE SETUP & DHAN-INSPIRED STYLING =================
st.set_page_config(page_title="Dhan Pro Terminal", layout="wide", page_icon="⚡")

# Custom CSS mimicking Dhan App UI
st.markdown("""
<style>
    /* Dhan Core Theme Colors */
    .stApp {
        background-color: #0b0e14;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Dhan Ticker Bar */
    div[data-testid="stMetric"] {
        background-color: #121824;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        color: #94a3b8;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.15rem;
        font-weight: 700;
    }

    /* Signal Cards (Dhan Order Card Style) */
    .dhan-card {
        background-color: #121824;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 14px;
        transition: border 0.2s ease;
    }
    .dhan-card:hover {
        border-color: #334155;
    }

    /* Badges */
    .badge-buy {
        background-color: rgba(0, 208, 156, 0.15);
        color: #00d09c;
        border: 1px solid #00d09c;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-sell {
        background-color: rgba(235, 91, 60, 0.15);
        color: #eb5b3c;
        border: 1px solid #eb5b3c;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-fno {
        background-color: #1e293b;
        color: #94a3b8;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    .badge-promo {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

ist = ZoneInfo("Asia/Kolkata")
now_ist = datetime.datetime.now(ist)

# ================= 2. STATE STORAGE (ALERTS & PORTFOLIO) =================
ADMIN_PASSWORD = "admin"  # You can change your admin password here

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "alerts_db" not in st.session_state:
    # Default Initial Active Calls
    st.session_state.alerts_db = [
        {
            "id": 1,
            "symbol": "NIFTY 24850 CE",
            "sec_id": "49081",
            "type": "OPTIDX",
            "action": "BUY",
            "entry": 142.0,
            "sl": 120.0,
            "tgt": 185.0,
            "qty": 25,
            "time": "09:30 AM"
        },
        {
            "id": 2,
            "symbol": "BANKNIFTY 52300 PE",
            "sec_id": "49082",
            "type": "OPTIDX",
            "action": "BUY",
            "entry": 235.0,
            "sl": 200.0,
            "tgt": 305.0,
            "qty": 15,
            "time": "10:15 AM"
        }
    ]

if "demo_balance" not in st.session_state:
    st.session_state.demo_balance = 100000.0
if "demo_positions" not in st.session_state:
    st.session_state.demo_positions = []

# ================= 3. SIDEBAR (DHAN KEYS + ADMIN LOGIN) =================
with st.sidebar:
    st.markdown("### ⚡ Dhan API Gateway")
    dhan_client_id = st.text_input("Dhan Client ID", type="password")
    dhan_access_token = st.text_input("Dhan Access Token", type="password")
    bot_token = st.text_input("Telegram Bot Token", type="password")
    chat_id = st.text_input("Telegram Chat ID")

    st.markdown("---")
    st.markdown("### 🔒 Trader Portal")
    if not st.session_state.admin_logged_in:
        pin = st.text_input("Enter Admin PIN", type="password")
        if st.button("Unlock Admin"):
            if pin == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("Admin mode unlocked!")
                st.rerun()
            else:
                st.error("Invalid PIN")
    else:
        st.success("🟢 Admin Mode Active")
        if st.button("Lock Admin Mode"):
            st.session_state.admin_logged_in = False
            st.rerun()

# ================= 4. DHAN HEADER & TICKER STRIP =================
c_head1, c_head2 = st.columns([3, 1])
with c_head1:
    st.markdown("<h2 style='margin:0; font-weight:800; color:#00d09c;'>⚡ DHAN PRO TERMINAL</h2>", unsafe_allow_html=True)
    st.caption("Direct Market Access | Real-time Option Execution & Radar")
with c_head2:
    st.markdown(f"<div style='text-align:right; font-size:0.9rem; color:#94a3b8;'>IST: <b>{now_ist.strftime('%I:%M:%S %p')}</b></div>", unsafe_allow_html=True)

# Tickers
@st.cache_data(ttl=60)
def fetch_indices():
    headers = {"User-Agent": "Mozilla/5.0"}
    indices = {
        "NIFTY 50": {"sym": "^NSEI", "val": 24855.30, "chg": "+0.45%"},
        "BANK NIFTY": {"sym": "^NSEBANK", "val": 52315.80, "chg": "+0.62%"},
        "SENSEX": {"sym": "^BSESN", "val": 81450.10, "chg": "+0.38%"},
        "INDIA VIX": {"sym": "^INDIAVIX", "val": 13.10, "chg": "-1.85%"}
    }
    for k, v in indices.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{v['sym']}?interval=1d"
            res = requests.get(url, headers=headers, timeout=2).json()
            meta = res["chart"]["result"][0]["meta"]
            curr = round(meta["regularMarketPrice"], 2)
            prev = round(meta["chartPreviousClose"], 2)
            pct = round(((curr - prev) / prev) * 100, 2)
            indices[k]["val"] = curr
            indices[k]["chg"] = f"{'+' if pct >= 0 else ''}{pct}%"
        except Exception:
            pass
    return indices

idx = fetch_indices()
t1, t2, t3, t4 = st.columns(4)
t1.metric("NIFTY 50", f"₹{idx['NIFTY 50']['val']}", idx['NIFTY 50']['chg'])
t2.metric("BANK NIFTY", f"₹{idx['BANK NIFTY']['val']}", idx['BANK NIFTY']['chg'])
t3.metric("SENSEX", f"₹{idx['SENSEX']['val']}", idx['SENSEX']['chg'])
t4.metric("INDIA VIX", f"{idx['INDIA VIX']['val']}", idx['INDIA VIX']['chg'], delta_color="inverse")

st.markdown("---")

# ================= 5. MAIN NAVIGATION =================
tab_calls, tab_positions, tab_movers, tab_admin = st.tabs([
    "🎯 Live Calls", 
    "📊 Live Positions", 
    "📈 Market Movers",
    "⚙️ Admin Desk" if st.session_state.admin_logged_in else "🔒 Admin Desk"
])

# ================= TAB 1: LIVE CALLS (FREE FOR LIMITED TIME) =================
with tab_calls:
    col_sub1, col_sub2 = st.columns([3, 1])
    with col_sub1:
        st.markdown("<h3 style='margin-bottom:0;'>Free for limited time</h3>", unsafe_allow_html=True)
        st.caption("High probability option and equity trade setups")
    with col_sub2:
        st.markdown("<div style='text-align:right; margin-top:8px;'><span class='badge-promo'>VIP FREE ACCESS</span></div>", unsafe_allow_html=True)

    if len(st.session_state.alerts_db) == 0:
        st.info("No active calls right now. Check back shortly.")
    else:
        for alert in st.session_state.alerts_db:
            badge_class = "badge-buy" if alert["action"] == "BUY" else "badge-sell"
            
            st.markdown(f"""
            <div class="dhan-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="{badge_class}">{alert['action']}</span>
                        <span class="badge-fno" style="margin-left:6px;">{alert['type']}</span>
                        <b style="font-size:1.1rem; margin-left:10px; color:#f8fafc;">{alert['symbol']}</b>
                    </div>
                    <div style="color:#64748b; font-size:0.8rem;">Time: {alert['time']}</div>
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); margin-top:14px; gap:10px;">
                    <div><span style="color:#64748b; font-size:0.75rem;">ENTRY</span><br><b style="font-size:1.05rem;">₹{alert['entry']}</b></div>
                    <div><span style="color:#64748b; font-size:0.75rem;">STOP LOSS</span><br><b style="color:#eb5b3c; font-size:1.05rem;">₹{alert['sl']}</b></div>
                    <div><span style="color:#64748b; font-size:0.75rem;">TARGET</span><br><b style="color:#00d09c; font-size:1.05rem;">₹{alert['tgt']}</b></div>
                    <div><span style="color:#64748b; font-size:0.75rem;">LOT SIZE</span><br><b style="font-size:1.05rem;">{alert['qty']} Qty</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            b1, b2, b3 = st.columns([2, 2, 4])
            
            # Action 1: Demo Trade
            if b1.button("🎮 Take Demo Trade", key=f"d_{alert['id']}"):
                cost = alert['entry'] * alert['qty']
                if st.session_state.demo_balance >= cost:
                    st.session_state.demo_balance -= cost
                    st.session_state.demo_positions.append({
                        "Symbol": alert['symbol'],
                        "Side": alert['action'],
                        "Qty": alert['qty'],
                        "Entry": alert['entry'],
                        "Current": alert['entry'],
                        "SL": alert['sl'],
                        "TGT": alert['tgt'],
                        "P&L": 0.0,
                        "Cost": cost
                    })
                    st.success(f"Position opened for {alert['symbol']} in Live Positions!")
                    st.rerun()
                else:
                    st.error("Insufficient demo capital!")

            # Action 2: Telegram Push (If Admin wants to re-broadcast)
            if b2.button("📲 Send to Telegram", key=f"t_{alert['id']}"):
                if bot_token and chat_id:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    txt = (
                        f"🚨 <b>{alert['action']} CALL DETECTED</b> 🚨\n\n"
                        f"<b>Instrument:</b> {alert['symbol']}\n"
                        f"<b>Entry:</b> ₹{alert['entry']}\n"
                        f"<b>SL:</b> ₹{alert['sl']} | <b>Target:</b> ₹{alert['tgt']}\n"
                        f"<b>Lot Size:</b> {alert['qty']}\n\n"
                        f"<i>Tap below to take action on Dhan:</i>"
                    )
                    payload = {
                        "chat_id": chat_id,
                        "text": txt,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [[
                                {"text": "🎯 CATCH (Execute)", "callback_data": f"CATCH_{alert['sec_id']}_{alert['action']}_{alert['qty']}"},
                                {"text": "❌ IGNORE", "callback_data": "IGNORE"}
                            ]]
                        }
                    }
                    requests.post(url, json=payload)
                    st.success("Alert broadcasted to Telegram!")
                else:
                    st.warning("Please configure Telegram credentials in the sidebar.")

# ================= TAB 2: LIVE POSITIONS BOOK =================
with tab_positions:
    st.subheader("📊 Live Position Book")
    
    col_p1, col_p2 = st.columns(2)
    col_p1.metric("Available Margin", f"₹{st.session_state.demo_balance:,.2f}")
    
    total_unrealized_pnl = sum([p.get("P&L", 0.0) for p in st.session_state.demo_positions])
    col_p2.metric("Total Unrealized P&L", f"₹{total_unrealized_pnl:+,.2f}", delta_color="normal" if total_unrealized_pnl >= 0 else "inverse")

    if len(st.session_state.demo_positions) == 0:
        st.info("No open positions. Take a trade from the 'Free for limited time' tab.")
    else:
        for idx, pos in enumerate(st.session_state.demo_positions):
            pnl_color = "#00d09c" if pos["P&L"] >= 0 else "#eb5b3c"
            
            st.markdown(f"""
            <div class="dhan-card">
                <div style="display:flex; justify-content:space-between;">
                    <b>{pos['Symbol']} ({pos['Side']})</b>
                    <span style="color:{pnl_color}; font-weight:bold; font-size:1.1rem;">₹{pos['P&L']:+,.2f}</span>
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:6px;">
                    Qty: {pos['Qty']} | Entry: ₹{pos['Entry']} | SL: ₹{pos['SL']} | TGT: ₹{pos['TGT']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Square Off {pos['Symbol']}", key=f"exit_{idx}"):
                st.session_state.demo_balance += pos["Cost"] + pos["P&L"]
                st.session_state.demo_positions.pop(idx)
                st.success(f"Square off complete for {pos['Symbol']}!")
                st.rerun()

# ================= TAB 3: MARKET MOVERS =================
with tab_movers:
    st.subheader("📈 NSE Market Movers")
    col_g, col_l = st.columns(2)
    with col_g:
        st.markdown("<b style='color:#00d09c;'>Top Gainers</b>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([
            {"Stock": "TATA MOTORS", "LTP": "₹985.40", "Change": "+4.25%"},
            {"Stock": "INFOSYS", "LTP": "₹1,890.10", "Change": "+3.10%"},
            {"Stock": "BHARTI AIRTEL", "LTP": "₹1,645.00", "Change": "+2.45%"}
        ]), use_container_width=True)

    with col_l:
        st.markdown("<b style='color:#eb5b3c;'>Top Losers</b>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame([
            {"Stock": "BAJAJ AUTO", "LTP": "₹10,250.00", "Change": "-3.80%"},
            {"Stock": "TRENT", "LTP": "₹7,450.20", "Change": "-2.65%"},
            {"Stock": "ITC", "LTP": "₹482.10", "Change": "-1.45%"}
        ]), use_container_width=True)

# ================= TAB 4: ADMIN DESK (MANUAL ALERT DISPATCH) =================
with tab_admin:
    if not st.session_state.admin_logged_in:
        st.warning("🔒 This section is restricted to the administrator. Enter PIN in the sidebar.")
    else:
        st.subheader("⚙️ Broadcast New Trade Setup")
        
        with st.form("manual_alert_form"):
            ca1, ca2 = st.columns(2)
            new_symbol = ca1.text_input("Instrument Name (e.g. NIFTY 24900 CE)", value="NIFTY 24900 CE")
            new_sec_id = ca2.text_input("Dhan Security ID", value="49085")
            
            ca3, ca4, ca5 = st.columns(3)
            new_action = ca3.selectbox("Action", ["BUY", "SELL"])
            new_type = ca4.selectbox("Type", ["OPTIDX", "OPTSTK", "EQ"])
            new_qty = ca5.number_input("Lot / Quantity", value=25, step=25)
            
            ca6, ca7, ca8 = st.columns(3)
            new_entry = ca6.number_input("Entry Price", value=150.0, step=1.0)
            new_sl = ca7.number_input("Stop Loss", value=130.0, step=1.0)
            new_tgt = ca8.number_input("Target Price", value=190.0, step=1.0)
            
            submit_alert = st.form_submit_button("Publish & Broadcast Call")

            if submit_alert:
                new_item = {
                    "id": len(st.session_state.alerts_db) + 1,
                    "symbol": new_symbol,
                    "sec_id": new_sec_id,
                    "type": new_type,
                    "action": new_action,
                    "entry": float(new_entry),
                    "sl": float(new_sl),
                    "tgt": float(new_tgt),
                    "qty": int(new_qty),
                    "time": now_ist.strftime("%I:%M %p")
                }
                # Insert at top of the active alerts list
                st.session_state.alerts_db.insert(0, new_item)
                
                # Auto-dispatch to Telegram if credentials exist
                if bot_token and chat_id:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    txt = (
                        f"🚨 <b>{new_action} CALL PUBLISHED</b> 🚨\n\n"
                        f"<b>Instrument:</b> {new_symbol}\n"
                        f"<b>Entry:</b> ₹{new_entry}\n"
                        f"<b>SL:</b> ₹{new_sl} | <b>Target:</b> ₹{new_tgt}\n"
                        f"<b>Lot Size:</b> {new_qty}\n\n"
                        f"<i>Tap below to take action on Dhan:</i>"
                    )
                    payload = {
                        "chat_id": chat_id,
                        "text": txt,
                        "parse_mode": "HTML",
                        "reply_markup": {
                            "inline_keyboard": [[
                                {"text": "🎯 CATCH (Execute)", "callback_data": f"CATCH_{new_sec_id}_{new_action}_{new_qty}"},
                                {"text": "❌ IGNORE", "callback_data": "IGNORE"}
                            ]]
                        }
                    }
                    requests.post(url, json=payload)
                
                st.success(f"Call for {new_symbol} published successfully!")
                st.rerun()

        # Delete / Manage Existing Calls
        st.write("---")
        st.subheader("Manage Active Calls")
        for i, a in enumerate(st.session_state.alerts_db):
            cd1, cd2 = st.columns([5, 1])
            cd1.write(f"• **{a['symbol']}** ({a['action']}) @ ₹{a['entry']} | SL: ₹{a['sl']} | TGT: ₹{a['tgt']}")
            if cd2.button("🗑️ Delete", key=f"del_{a['id']}"):
                st.session_state.alerts_db.pop(i)
                st.rerun()
