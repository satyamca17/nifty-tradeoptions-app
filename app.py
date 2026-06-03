import streamlit as st
import login
import terminal  # We are importing your newly renamed terminal.py here


def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# Set page config here so it applies to the whole app layout
st.set_page_config(page_title="Options Pro", page_icon="📈", layout="wide")
load_css() # <--- Loads your gorgeous new CSS!
# Force the database to initialize and create any missing tables!
login.init_db()

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# The Gatekeeper: Route the user based on their session state
if not st.session_state.authenticated:
    login.render_auth_page()
else:
    # THIS LINE FIXED: It must say 'terminal.' instead of 'app.'
    terminal.render_pro_terminal()