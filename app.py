import streamlit as st
import pandas as pd
from jugaad_data.nse import NSELive

# ==========================================
# PAGE CONFIGURATION & STATE INITIALIZATION
# ==========================================
st.set_page_config(page_title="Nifty Option Trading", page_icon="📈", layout="wide")

# CSS to keep things compact
st.markdown("""
    <style>
        .block-container {
            padding-top: 3rem; 
            padding-bottom: 0rem;
        }
        h3, h4 {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
    </style>
""", unsafe_allow_html=True)

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = []

st.header("📈 Nifty Option Trading")


# ==========================================
# DATA FETCHING FUNCTIONS
# ==========================================
@st.cache_data(ttl=30, show_spinner=False)
def fetch_nse_option_chain(symbol="NIFTY"):
    try:
        n = NSELive()
        data = n.index_option_chain(symbol)
        return data['records']
    except Exception as e:
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


# ==========================================
# MAIN LAYOUT: Side-by-Side Columns
# ==========================================
col_order, col_portfolio = st.columns([1, 2.2])

# ==========================================
# LEFT COLUMN: EXECUTE TRADE
# ==========================================
with col_order:
    st.markdown("#### 📝 Execute Trade")
    with st.container(border=True):
        strike_prices = list(range(22000, 26801, 50))
        default_index = strike_prices.index(24000) if 24000 in strike_prices else 0
        selected_strike = st.selectbox("Strike Price", strike_prices, index=default_index)

        c1, c2 = st.columns(2)
        with c1:
            option_type = st.radio("Option Type", ["CE", "PE"])
        with c2:
            trade_action = st.radio("Action", ["Buy", "Sell"])

        c3, c4 = st.columns(2)
        with c3:
            order_type = st.radio("Order Type", ["Market", "Limit"])
        with c4:
            lots = st.number_input("Lots (Size: 65)", min_value=1, value=1, step=1)
            quantity = lots * 65
            st.caption(f"Qty: **{quantity}**")

        if order_type == "Limit":
            entry_price = st.number_input("Limit Price (₹)", min_value=0.0, value=100.0, step=1.0)
        else:
            entry_price = 0.0
            st.caption("Market Order: Will execute at live price.")

        if st.button("⚡ Execute", use_container_width=True, type="primary"):
            final_entry_price = entry_price

            if order_type == "Market":
                with st.spinner("Fetching live market price..."):
                    st.cache_data.clear()
                    records = fetch_nse_option_chain("NIFTY")
                    live_price = get_ltp_from_chain(records['data'] if records else None, selected_strike, option_type)

                    if live_price is not None:
                        final_entry_price = live_price
                    else:
                        st.error(f"Could not fetch Market Price for {selected_strike} {option_type}.")
                        st.stop()

            st.session_state.portfolio.append({
                "Action": trade_action,
                "Type": f"{selected_strike} {option_type}",
                "Order": order_type,
                "Entry Price": final_entry_price,
                "Lots": lots,
                "Quantity": quantity,
                "Live LTP": 0.0,
                "P&L": 0.0
            })
            st.success(f"Executed {trade_action} at ₹{final_entry_price}!")

# ==========================================
# RIGHT COLUMN: PROFIT & LOSS
# ==========================================
with col_portfolio:
    header_col, btn_refresh, btn_clear = st.columns([3, 1, 1])
    with header_col:
        st.markdown("#### 💼 Profit & Loss")
    with btn_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
    with btn_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.portfolio = []
            st.rerun()

    if len(st.session_state.portfolio) > 0:
        with st.spinner("Updating portfolio prices..."):
            records = fetch_nse_option_chain("NIFTY")
            total_pnl = 0.0

            if records:
                spot_price = records.get('underlyingValue', 'N/A')
                st.markdown(f"**NIFTY 50 Index Value:** `{spot_price}`")

                chain_data = records['data']

                # Calculate P&L mathematically first
                for pos in st.session_state.portfolio:
                    strike = int(pos['Type'].split(" ")[0])
                    opt_type = pos['Type'].split(" ")[1]

                    live_ltp = get_ltp_from_chain(chain_data, strike, opt_type)

                    if live_ltp is not None:
                        pos['Live LTP'] = live_ltp

                        if pos['Action'] == "Buy":
                            pos['P&L'] = (live_ltp - pos['Entry Price']) * pos['Quantity']
                        elif pos['Action'] == "Sell":
                            pos['P&L'] = (pos['Entry Price'] - live_ltp) * pos['Quantity']

                        total_pnl += pos['P&L']

            # --- NEW CRASH-PROOF TABLE FORMATTING ---
            # Format numbers safely as text before passing to Pandas
            display_list = []
            for pos in st.session_state.portfolio:
                display_list.append({
                    "Action": pos["Action"],
                    "Type": pos["Type"],
                    "Order": pos["Order"],
                    "Lots": pos["Lots"],
                    "Qty": pos["Quantity"],
                    "Buy/Sell Price": f"₹{pos['Entry Price']:.2f}",
                    "Live Price": f"₹{pos['Live LTP']:.2f}",
                    "Profit/Loss": f"₹{pos['P&L']:.2f}"
                })

            # Display the basic dataframe
            df = pd.DataFrame(display_list)
            st.dataframe(df, use_container_width=True)

            # Display overall total P&L underneath
            if total_pnl > 0:
                st.success(f"### 🟢 Total P&L: +₹{total_pnl:.2f}")
            elif total_pnl < 0:
                st.error(f"### 🔴 Total P&L: -₹{abs(total_pnl):.2f}")
            else:
                st.info(f"### ⚪ Total P&L: ₹0.00")

    else:
        st.info("Your portfolio is empty. Execute a trade to get started.")