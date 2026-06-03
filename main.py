import streamlit as st
import login
import app

# Set page config here so it applies to the whole app layout
st.set_page_config(page_title="Options Pro", page_icon="📈", layout="wide")

# ADDED: Force the database to initialize and create any missing tables!
login.init_db()

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# The Gatekeeper: Route the user based on their session state
if not st.session_state.authenticated:
    login.render_auth_page()
else:
    app.render_pro_terminal()