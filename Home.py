import streamlit as st
import sys
import traceback
import login
import app

# Set page config here so it applies to the whole app layout
st.set_page_config(page_title="Options Pro", page_icon="📈", layout="wide")

st.write("🔍 App Starting...")

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.write("✓ Session state initialized")

st.write("📦 Attempting to import login module...")
try:
    import login
    st.write("✓ Login module imported successfully")
except Exception as e:
    st.error(f"❌ Failed to import login: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

st.write("📦 Attempting to import app module...")
try:
    import app
    st.write("✓ App module imported successfully")
except Exception as e:
    st.error(f"❌ Failed to import app: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()

st.write("🔐 Checking authentication status...")
st.write(f"Authenticated: {st.session_state.authenticated}")

try:
    # The Gatekeeper: Route the user based on their session state
    if not st.session_state.authenticated:
        st.write("➡️ Rendering login page...")
        login.render_auth_page()
    else:
        st.write("➡️ Rendering app terminal...")
        app.render_pro_terminal()
except Exception as e:
    st.error(f"❌ Runtime Error: {str(e)}")
    st.code(traceback.format_exc())
    st.stop()
