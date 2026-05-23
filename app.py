import streamlit as st
import pandas as pd
import uuid
import plotly.graph_objects as go
from datetime import datetime
from jugaad_data.nse import NSELive
from streamlit_autorefresh import st_autorefresh

# ==========================================
# PAGE CONFIGURATION & STATE INITIALIZATION
# ==========================================
st.set_page_config(page_title="Nifty Option Trading", page_icon="📈", layout="wide")

# Updated CSS for better top-spacing
st.markdown("""
<style>
/* Make select dropdown taller and options more readable */
div[data-baseweb="select"] .css-1wy0on6, .stSelectbox .css-1wy0on6 {
  max-height: 48px !important;
  line-height: 1.4 !important;
  font-size: 15px !important;
  padding: 8px 10px !important;
}

/* Expand the opened options list and increase option padding */
div[role="listbox"], div[role="option"], .rc-virtual-list-holder-inner div {
  max-height: 360px !important;        /* allow more visible options before scrolling */
  min-width: 220px !important;         /* ensure dropdown width fits values */
  padding: 6px 10px !important;
  font-size: 15px !important;
  line-height: 1.5 !important;
  overflow-y: auto !important;
  box-shadow: 0 8px 24px rgba(15,23,36,0.08) !important;
  border-radius: 8px !important;
  background: #ffffff !important;      /* matches light theme */
  color: #0f1724 !important;
}

/* Make each option taller for readability */
div[role="option"] {
  padding: 10px 12px !important;
  min-height: 40px !important;
  display: flex !important;
  align-items: center !important;
}

/* Ensure selected value is visible and not clipped */
.css-1uccc91-singleValue, .css-1wy0on6 > div {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: 100% !important;
  color: #0f1724 !important;
}

/* Slightly increase selectbox container height */
.stSelectbox, div[data-baseweb="select"] {
  min-height: 44px !important;
  padding: 4px !important;
}

/* Responsive tweak for narrow screens */
@media (max-width: 900px) {
  div[role="listbox"] { max-height: 280px !important; min-width: 180px !important; }
  div[role="option"] { min-height: 36px !important; font-size: 14px !important; }
}
</style>
""", unsafe_allow_html=True)










# Initialize Session States
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []
if 'history' not in st.session_state:
    st.session_state.history = []
if 'pending_orders' not in st.session_state:
    st.session_state.pending_orders = []
if 'exit_prompt_id' not in st.session_state:
    st.session_state.exit_prompt_id = None
if 'edit_prompt_id' not in st.session_state:
    st.session_state.edit_prompt_id = None
if 'capital' not in st.session_state:
    st.session_state.capital = 450000.0
if 'realized_pnl' not in st.session_state:
    st.session_state.realized_pnl = 0.0

# ==========================================
# TOP DASHBOARD
# ==========================================
top_col1, top_col2, top_col3 = st.columns([2.5, 1, 1])

with top_col1:
    st.markdown("## 📈 Nifty Options Pro Terminal")
    auto_refresh = st.checkbox("⏱️ Auto-Refresh (30s)", value=False)
    if auto_refresh:
        st_autorefresh(interval=30000, key="data_refresh")

with top_col2:
    st.markdown(
        f"<div style='text-align: right; margin-top: 5px;'><span style='font-size: 16px; font-weight: bold; color: gray;'>Available Capital</span><br><span style='font-size: 24px; color: #1f77b4; font-weight: bold;'>₹{st.session_state.capital + st.session_state.realized_pnl:,.2f}</span></div>",
        unsafe_allow_html=True)

with top_col3:
    pnl_color = '#00FF00' if st.session_state.realized_pnl > 0 else '#FF0000' if st.session_state.realized_pnl < 0 else 'gray'
    st.markdown(
        f"<div style='text-align: right; margin-top: 5px;'><span style='font-size: 16px; font-weight: bold; color: gray;'>Realized P&L</span><br><span style='font-size: 24px; color: {pnl_color}; font-weight: bold;'>₹{st.session_state.realized_pnl:,.2f}</span></div>",
        unsafe_allow_html=True)

st.divider()


# ==========================================
# DATA FETCHING & HELPER FUNCTIONS
# ==========================================
@st.cache_data(ttl=20, show_spinner=False)
def fetch_nse_option_chain(symbol="NIFTY"):
    try:
        n = NSELive()
        data = n.index_option_chain(symbol)
        return data['records']
    except Exception:
        return None


def get_ltp_from_chain(chain_data, strike, opt_type):
    if not chain_data:
        return None
    for record in chain_data:
        if record['strikePrice'] == strike:
            if opt_type == "CE" and "CE" in record:
                return record['CE']['lastPrice']
            elif opt_type == "PE" and "PE" in record:
                return record['PE']['lastPrice']
    return None


def add_or_average_position(action, strike, opt_type, entry_price, target, sl, quantity, live_ltp):
    existing_pos = next((p for p in st.session_state.portfolio
                         if p['Action'] == action and p['Strike'] == strike and p['OptType'] == opt_type), None)

    if existing_pos:
        old_qty = existing_pos['Quantity']
        old_price = existing_pos['Entry Price']
        new_qty = old_qty + quantity
        new_avg_price = ((old_qty * old_price) + (quantity * entry_price)) / new_qty

        existing_pos['Quantity'] = new_qty
        existing_pos['Entry Price'] = new_avg_price
        if target > 0: existing_pos['Target'] = target
        if sl > 0: existing_pos['SL'] = sl
        existing_pos['Live LTP'] = live_ltp
    else:
        st.session_state.portfolio.append({
            "ID": str(uuid.uuid4())[:8],
            "Action": action,
            "Strike": strike,
            "OptType": opt_type,
            "Entry Price": entry_price,
            "Target": target,
            "SL": sl,
            "Quantity": quantity,
            "Live LTP": live_ltp,
            "P&L": 0.0
        })


# UPGRADED: Now accepts a specific quantity for Partial Exits
def close_position(pos_id, exit_price, reason="Manual Square-off", qty_to_close=None):
    pos = next((p for p in st.session_state.portfolio if p['ID'] == pos_id), None)
    if pos:
        # If no specific qty is passed, assume closing the entire position
        close_qty = qty_to_close if qty_to_close is not None else pos['Quantity']
        if close_qty > pos['Quantity']: close_qty = pos['Quantity']  # Failsafe

        if pos['Action'] == "Buy":
            final_pnl = (exit_price - pos['Entry Price']) * close_qty
        else:
            final_pnl = (pos['Entry Price'] - exit_price) * close_qty

        st.session_state.realized_pnl += final_pnl
        st.session_state.history.append({
            "Time Closed": datetime.now().strftime("%H:%M:%S"),
            "Action": pos['Action'],
            "Type": f"{pos['Strike']} {pos['OptType']}",
            "Qty": close_qty,
            "Entry Price": round(pos['Entry Price'], 2),
            "Exit Price": round(exit_price, 2),
            "P&L": round(final_pnl, 2),
            "Reason": reason
        })

        # Determine if it's a full close or partial exit
        if close_qty == pos['Quantity']:
            st.session_state.portfolio = [p for p in st.session_state.portfolio if p['ID'] != pos_id]
            st.session_state.pending_orders = [po for po in st.session_state.pending_orders if
                                               po.get('Pos_ID') != pos_id]
        else:
            pos['Quantity'] -= close_qty  # Deduct exited lots from open position


# ==========================================
# MAIN LAYOUT: Side-by-Side Columns
# ==========================================
col_order, col_portfolio = st.columns([1.4, 2.2])

# ==========================================
# LEFT COLUMN: EXECUTE TRADE
# ==========================================
with col_order:
    st.markdown("#### 📝 Execute Trade")
    with st.container(border=True):

        c1, c2 = st.columns([1.5, 1])
        with c1:
            strike_prices = list(range(22000, 26801, 50))
            default_index = strike_prices.index(24000) if 24000 in strike_prices else 0
            selected_strike = st.selectbox("Strike Price", strike_prices, index=default_index)
        with c2:
            option_type = st.radio("Type", ["CE", "PE"], horizontal=True)

        c3, c4 = st.columns(2)
        with c3:
            trade_action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
        with c4:
            order_type = st.radio("Order", ["Market", "Limit"], horizontal=True)

        c5, c6 = st.columns(2)
        with c5:
            lots = st.number_input("Lots (65x)", min_value=1, value=1, step=1)
            quantity = lots * 65
        with c6:
            if order_type == "Limit":
                entry_price = st.number_input("Limit (₹)", min_value=0.0, value=100.0, step=1.0)
            else:
                entry_price = 0.0
                st.markdown("<div style='margin-top: 35px; color: gray; font-size: 14px;'>Market Order (Live)</div>",
                            unsafe_allow_html=True)

        c7, c8 = st.columns(2)
        with c7:
            target_price = st.number_input("Target (0=None)", min_value=0.0, value=0.0, step=1.0)
        with c8:
            sl_price = st.number_input("SL (0=None)", min_value=0.0, value=0.0, step=1.0)

        st.markdown(f"**Total Qty: {quantity}**")

        if st.button("⚡ Execute Trade", use_container_width=True, type="primary"):
            if order_type == "Market":
                st.cache_data.clear()
                records = fetch_nse_option_chain("NIFTY")
                live_price = get_ltp_from_chain(records['data'] if records else None, selected_strike, option_type)

                if live_price is not None:
                    add_or_average_position(trade_action, selected_strike, option_type, live_price, target_price,
                                            sl_price, quantity, live_price)
                    st.success(f"Executed {trade_action} at ₹{live_price}! (Averaged if position existed)")
                else:
                    st.error(f"Failed to fetch Market Price.")
                    st.stop()
            else:
                st.session_state.pending_orders.append({
                    "ID": str(uuid.uuid4())[:8],
                    "Pos_ID": None,
                    "Type": "Entry",
                    "Action": trade_action,
                    "Strike": selected_strike,
                    "OptType": option_type,
                    "Quantity": quantity,
                    "Limit Price": entry_price,
                    "Target": target_price,
                    "SL": sl_price
                })
                st.success(f"Pending Entry Limit placed at ₹{entry_price}!")

# ==========================================
# RIGHT COLUMN: PROCESS PENDING & TABS
# ==========================================
with col_portfolio:
    records = fetch_nse_option_chain("NIFTY")
    chain_data = records['data'] if records else None
    spot_price = records.get('underlyingValue', 0.0) if records else 0.0

    # --- PROCESS PENDING ORDERS IN BACKGROUND ---
    if chain_data and len(st.session_state.pending_orders) > 0:
        for po in st.session_state.pending_orders[:]:
            live_ltp = get_ltp_from_chain(chain_data, po['Strike'], po['OptType'])
            if live_ltp is not None:
                triggered = False

                if po['Type'] == "Entry":
                    if po['Action'] == "Buy" and live_ltp <= po['Limit Price']:
                        triggered = True
                    elif po['Action'] == "Sell" and live_ltp >= po['Limit Price']:
                        triggered = True

                    if triggered:
                        add_or_average_position(po['Action'], po['Strike'], po['OptType'], po['Limit Price'],
                                                po['Target'], po['SL'], po['Quantity'], live_ltp)
                        st.session_state.pending_orders.remove(po)
                        st.toast(f"✅ Limit {po['Action']} Executed at ₹{po['Limit Price']}")

                elif po['Type'] == "Exit":
                    if po['Trigger'] == ">=" and live_ltp >= po['Limit Price']:
                        triggered = True
                    elif po['Trigger'] == "<=" and live_ltp <= po['Limit Price']:
                        triggered = True

                    if triggered:
                        pos_exists = any(p['ID'] == po['Pos_ID'] for p in st.session_state.portfolio)
                        if pos_exists:
                            close_position(po['Pos_ID'], po['Limit Price'], "Limit Exit Executed",
                                           qty_to_close=po['Quantity'])
                            st.toast(f"✅ Limit Exit Executed at ₹{po['Limit Price']}")
                        if po in st.session_state.pending_orders:
                            st.session_state.pending_orders.remove(po)

    # --- RENDER TABS ---
    tab1, tab2, tab3, tab4 = st.tabs(
        ["💼 Open Positions", "⏳ Pending Orders", "📜 Trade History", "📊 Expiry Payoff Chart"])

    # ------------------------------------------
    # TAB 1: OPEN POSITIONS
    # ------------------------------------------
    with tab1:
        rc1, rc2 = st.columns([3, 1])
        with rc1:
            st.markdown(f"#### **Live NIFTY 50 Spot:** `{spot_price}`")
        with rc2:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        if len(st.session_state.portfolio) > 0 and chain_data:
            total_unrealized_pnl = 0.0
            trades_to_close = []

            for pos in st.session_state.portfolio:
                live_ltp = get_ltp_from_chain(chain_data, pos['Strike'], pos['OptType'])
                if live_ltp is not None:
                    pos['Live LTP'] = live_ltp
                    if pos['Action'] == "Buy":
                        pos['P&L'] = (live_ltp - pos['Entry Price']) * pos['Quantity']
                        if pos['Target'] > 0 and live_ltp >= pos['Target']:
                            trades_to_close.append((pos['ID'], live_ltp, "Target Hit"))
                        elif pos['SL'] > 0 and live_ltp <= pos['SL']:
                            trades_to_close.append((pos['ID'], live_ltp, "SL Hit"))
                    elif pos['Action'] == "Sell":
                        pos['P&L'] = (pos['Entry Price'] - live_ltp) * pos['Quantity']
                        if pos['Target'] > 0 and live_ltp <= pos['Target']:
                            trades_to_close.append((pos['ID'], live_ltp, "Target Hit"))
                        elif pos['SL'] > 0 and live_ltp >= pos['SL']:
                            trades_to_close.append((pos['ID'], live_ltp, "SL Hit"))
                    total_unrealized_pnl += pos['P&L']

            for t_id, t_price, t_reason in trades_to_close:
                close_position(t_id, t_price, t_reason)
                st.warning(f"Auto-squared off trade ({t_reason}) at ₹{t_price}")
                st.rerun()

            if len(st.session_state.portfolio) > 0:
                st.markdown("---")
                h1, h2, h3, h4, h5, h6 = st.columns([1, 1.5, 1, 1, 1, 1])
                h1.markdown("Action")
                h2.markdown("Contract")
                h3.markdown("Avg Price")
                h4.markdown("Live")
                h5.markdown("P&L")
                h6.markdown("Exit")
                st.markdown("---")

                for pos in st.session_state.portfolio:
                    c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 1, 1, 1, 1])
                    pnl_color = "#00FF00" if pos['P&L'] > 0 else "#FF0000" if pos['P&L'] < 0 else "gray"

                    c1.write(f"{pos['Action']}")
                    c2.write(f"{pos['Quantity']}x {pos['Strike']} {pos['OptType']}")
                    c3.write(f"₹{pos['Entry Price']:.2f}")
                    c4.write(f"₹{pos['Live LTP']:.2f}")
                    c5.markdown(f"<span style='color: {pnl_color}; font-size: 16px;'>₹{pos['P&L']:.2f}</span>",
                                unsafe_allow_html=True)

                    if c6.button("🚪 Exit", key=f"btn_{pos['ID']}", use_container_width=True):
                        st.session_state.exit_prompt_id = pos['ID']
                        st.rerun()

                # --- UPGRADED EXIT PROMPT WITH LOTS SELECTION ---
                if st.session_state.exit_prompt_id:
                    pos_to_exit = next(
                        (p for p in st.session_state.portfolio if p['ID'] == st.session_state.exit_prompt_id), None)
                    if pos_to_exit:
                        st.markdown("---")
                        st.markdown(
                            f"#### ⚙️ Close Position: {pos_to_exit['Action']} {pos_to_exit['Quantity']}x {pos_to_exit['Strike']} {pos_to_exit['OptType']}")

                        e_c1, e_c2, e_c3, e_c4 = st.columns(4)
                        current_lots = int(pos_to_exit['Quantity'] / 65)

                        with e_c1:
                            exit_mode = st.radio("Order Type", ["Market", "Limit"], key="exit_mode")
                        with e_c2:
                            exit_lots = st.number_input("Lots to Exit", min_value=1, max_value=current_lots,
                                                        value=current_lots, step=1)
                        with e_c3:
                            if exit_mode == "Limit":
                                exit_limit = st.number_input("Limit Price (₹)", min_value=0.0,
                                                             value=float(pos_to_exit['Live LTP']), step=1.0)
                            else:
                                st.caption("Will execute immediately at Market.")
                        with e_c4:
                            st.write("")
                            st.write("")
                            if st.button("✅ Confirm Exit", type="primary", use_container_width=True):
                                qty_to_exit = exit_lots * 65

                                if exit_mode == "Market":
                                    close_position(pos_to_exit['ID'], pos_to_exit['Live LTP'], "Manual Market Exit",
                                                   qty_to_close=qty_to_exit)
                                else:
                                    trigger_dir = ">=" if exit_limit >= pos_to_exit['Live LTP'] else "<="
                                    st.session_state.pending_orders.append({
                                        "ID": str(uuid.uuid4())[:8],
                                        "Pos_ID": pos_to_exit['ID'],
                                        "Type": "Exit",
                                        "Action": "Close",
                                        "Strike": pos_to_exit['Strike'],
                                        "OptType": pos_to_exit['OptType'],
                                        "Quantity": qty_to_exit,
                                        "Limit Price": exit_limit,
                                        "Trigger": trigger_dir
                                    })
                                    st.toast(f"Pending Exit placed for {qty_to_exit} qty at ₹{exit_limit}")
                                st.session_state.exit_prompt_id = None
                                st.rerun()

                            if st.button("❌ Cancel", key="cancel_exit_prompt", use_container_width=True):
                                st.session_state.exit_prompt_id = None
                                st.rerun()
                st.markdown("---")

                if total_unrealized_pnl > 0:
                    st.success(f"**🟢 Open P&L: +₹{total_unrealized_pnl:.2f}**")
                elif total_unrealized_pnl < 0:
                    st.error(f"**🔴 Open P&L: -₹{abs(total_unrealized_pnl):.2f}**")
                else:
                    st.info(f"**⚪ Open P&L: ₹0.00**")
        else:
            st.info("No active positions. Execute a trade to begin.")

    # ------------------------------------------
    # TAB 2: PENDING ORDERS
    # ------------------------------------------
    with tab2:
        if len(st.session_state.pending_orders) > 0:
            h1, h2, h3, h4, h5, h6 = st.columns([1, 1.5, 1, 1.2, 0.8, 0.8])
            h1.markdown("Type")
            h2.markdown("Contract")
            h3.markdown("Limit Price")
            h4.markdown("Target / SL")
            h5.markdown("Edit")
            h6.markdown("Cancel")
            st.markdown("---")

            for po in st.session_state.pending_orders:
                c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 1, 1.2, 0.8, 0.8])
                c1.write(f"{po['Type']} Limit")
                c2.write(f"{po['Quantity']}x {po['Strike']} {po['OptType']}")
                c3.write(f"₹{po['Limit Price']:.2f}")

                if po['Type'] == "Entry":
                    c4.write(f"T: {po['Target']} / SL: {po['SL']}")
                else:
                    c4.write("-")

                if c5.button("✏️ Edit", key=f"edit_po_{po['ID']}", use_container_width=True):
                    st.session_state.edit_prompt_id = po['ID']
                    st.rerun()
                if c6.button("❌ Cancel", key=f"cancel_po_{po['ID']}", use_container_width=True):
                    st.session_state.pending_orders.remove(po)
                    if st.session_state.edit_prompt_id == po['ID']:
                        st.session_state.edit_prompt_id = None
                    st.rerun()

            st.markdown("---")

            if st.session_state.edit_prompt_id:
                po_to_edit = next(
                    (po for po in st.session_state.pending_orders if po['ID'] == st.session_state.edit_prompt_id), None)
                if po_to_edit:
                    st.markdown(
                        f"#### ✏️ Modify Order: {po_to_edit['Type']} {po_to_edit['Quantity']}x {po_to_edit['Strike']} {po_to_edit['OptType']}")
                    e_c1, e_c2, e_c3 = st.columns(3)

                    with e_c1:
                        edit_mode = st.radio("Order Type", ["Limit", "Market"], key="edit_po_mode")
                    with e_c2:
                        if edit_mode == "Limit":
                            new_limit = st.number_input("New Limit Price (₹)", min_value=0.0,
                                                        value=float(po_to_edit['Limit Price']), step=1.0)
                        else:
                            st.caption("Will execute immediately at live Market price.")
                    with e_c3:
                        st.write("")
                        st.write("")
                        if st.button("✅ Confirm Update", type="primary", use_container_width=True):
                            if edit_mode == "Limit":
                                po_to_edit['Limit Price'] = new_limit
                                st.toast(f"Pending Order updated to Limit ₹{new_limit}")
                            else:
                                live_price = get_ltp_from_chain(chain_data, po_to_edit['Strike'],
                                                                po_to_edit['OptType']) if chain_data else None
                                if live_price is not None:
                                    if po_to_edit['Type'] == "Entry":
                                        add_or_average_position(po_to_edit['Action'], po_to_edit['Strike'],
                                                                po_to_edit['OptType'], live_price, po_to_edit['Target'],
                                                                po_to_edit['SL'], po_to_edit['Quantity'], live_price)
                                        st.toast(f"✅ Entry executed at Market ₹{live_price}")
                                    elif po_to_edit['Type'] == "Exit":
                                        close_position(po_to_edit['Pos_ID'], live_price, "Market Edit Exit",
                                                       qty_to_close=po_to_edit['Quantity'])
                                        st.toast(f"✅ Exit executed at Market ₹{live_price}")
                                    st.session_state.pending_orders.remove(po_to_edit)
                                else:
                                    st.error("Could not fetch Live Price for Market execution.")

                            st.session_state.edit_prompt_id = None
                            st.rerun()

                        if st.button("❌ Close Editor", use_container_width=True):
                            st.session_state.edit_prompt_id = None
                            st.rerun()
                else:
                    st.session_state.edit_prompt_id = None
        else:
            st.info("No pending orders.")
            st.session_state.edit_prompt_id = None

    # ------------------------------------------
    # TAB 3: TRADE HISTORY
    # ------------------------------------------
    with tab3:
        if len(st.session_state.history) > 0:
            hist_df = pd.DataFrame(st.session_state.history)

            csv = hist_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", data=csv, file_name=f"Trade_History.csv", mime="text/csv")

            formatted_hist = hist_df.style.format({
                "Entry Price": "₹{:.2f}",
                "Exit Price": "₹{:.2f}",
                "P&L": "₹{:.2f}"
            }).map(lambda
                       val: 'color: #00FF00; font-weight:bold;' if val > 0 else 'color: #FF0000; font-weight:bold;' if val < 0 else '',
                   subset=['P&L'])

            st.dataframe(formatted_hist, use_container_width=True, hide_index=True)

            if st.button("🗑️ Clear History"):
                st.session_state.history = []
                st.rerun()
        else:
            st.info("No closed trades yet.")

    # ------------------------------------------
    # TAB 4: PAYOFF CHART
    # ------------------------------------------
    with tab4:
        if len(st.session_state.portfolio) > 0 and spot_price > 0:
            spot_range = list(range(int(spot_price) - 1000, int(spot_price) + 1000, 50))
            payoffs = []

            for s in spot_range:
                pnl_at_expiry = 0
                for pos in st.session_state.portfolio:
                    strike = pos['Strike']
                    entry = pos['Entry Price']
                    qty = pos['Quantity']

                    if pos['OptType'] == 'CE':
                        val = max(0, s - strike)
                    else:
                        val = max(0, strike - s)

                    if pos['Action'] == 'Buy':
                        pnl_at_expiry += (val - entry) * qty
                    else:
                        pnl_at_expiry += (entry - val) * qty

                payoffs.append(pnl_at_expiry)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=spot_range,
                y=payoffs,
                mode='lines',
                line=dict(color='red', width=3),
                fill='tozeroy',
                fillcolor='rgba(255, 0, 0, 0.1)'
            ))

            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Nifty Spot Price",
                yaxis_title="Profit / Loss (₹)",
                margin=dict(l=20, r=20, t=30, b=20),
                font=dict(color='white'),
                xaxis=dict(tickformat="d", gridcolor="rgba(255,255,255,0.2)"),
                yaxis=dict(tickformat="d", gridcolor="rgba(255,255,255,0.2)")
            )

            fig.update_traces(
                line=dict(color='cyan', width=3),
                fill='tozeroy',
                fillcolor='rgba(0,255,255,0.2)',
                hovertemplate="<b>Nifty Spot: %{x}</b><br>Profit/Loss: ₹%{y:,.2f}<extra></extra>"
            )

            fig.add_hline(y=0, line_dash="dash", line_color="black")

            st.plotly_chart(fig, use_container_width=True)

            max_profit = max(payoffs)
            max_loss = min(payoffs)

            if max_profit == payoffs[0] and payoffs[0] > payoffs[1]:
                prof_text = "Unlimited"
            elif max_profit == payoffs[-1] and payoffs[-1] > payoffs[-2]:
                prof_text = "Unlimited"
            else:
                prof_text = f"₹{max_profit:,.2f}"

            if max_loss == payoffs[0] and payoffs[0] < payoffs[1]:
                loss_text = "Unlimited"
            elif max_loss == payoffs[-1] and payoffs[-1] < payoffs[-2]:
                loss_text = "Unlimited"
            else:
                loss_text = f"₹{max_loss:,.2f}"

            st.markdown("---")
            m1, m2 = st.columns(2)
            m1.success(f"**🟢 Max Profit:** {prof_text}")
            m2.error(f"**🔴 Max Loss:** {loss_text}")

            st.caption(
                "Chart assumes positions are held to expiry day. Max Profit/Loss are estimated based on a ±1000 point range.")
        else:
            st.info("Execute trades and fetch live data to view your payoff chart.")