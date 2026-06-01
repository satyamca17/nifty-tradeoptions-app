import streamlit as st
import sys

# Set page config here so it applies to the whole app layout
st.set_page_config(page_title="Options Pro", page_icon="📈", layout="wide")

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

try:
    import login
    import app
    
    # The Gatekeeper: Route the user based on their session state
    if not st.session_state.authenticated:
        # UPDATED: Call the router function so users can access both Login and Signup forms
        login.render_auth_page()
    else:
        # Calls the terminal function from your app.py
        app.render_pro_terminal()

except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.info("Make sure all required modules are installed: bcrypt, streamlit, streamlit-autorefresh, jugaad-data, plotly, pandas")
    st.stop()
except Exception as e:
    st.error(f"❌ Error: {str(e)}")
    st.info("Check your browser console for more details")
    import traceback
    st.code(traceback.format_exc())
    st.stop()
