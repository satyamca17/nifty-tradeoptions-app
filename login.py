import streamlit as st
import sqlite3
import bcrypt

def load_css():
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

DB_PATH = "users.db"


# --- Database Helpers ---
def init_db():
    """Creates the table with the correct schema if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            pancard TEXT NOT NULL,
            password_hash TEXT NOT NULL
        );
    ''')
    conn.commit()
    conn.close()


def create_user(username, email, phone, pancard, password):
    """Inserts a new user with all required fields into the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        cursor.execute(
            "INSERT INTO users (username, email, phone, pancard, password_hash) VALUES (?, ?, ?, ?, ?)",
            (username, email, phone, pancard, password_hash)
        )
        conn.commit()
        return True, "Signup successful! You can now log in."
    except sqlite3.IntegrityError as e:
        error_msg = str(e)
        if "username" in error_msg:
            return False, "Username already exists."
        elif "email" in error_msg:
            return False, "Email address is already registered."
        else:
            return False, "Username or Email already exists."
    finally:
        conn.close()


def verify_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    if row:
        stored_hash = row[0]
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
    return False


# --- UI Pages ---
def render_login_page():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📈 Options Pro</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 User Login")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")

            if st.button("Authenticate", type="primary", use_container_width=True):
                if verify_user(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")


def render_signup_page():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>📈 Options Pro</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 📝 User Signup")
            username = st.text_input("Choose a Username", key="signup_user")
            email = st.text_input("Email Address", key="signup_email")
            phone = st.text_input("Phone Number", key="signup_phone")
            pancard = st.text_input("PAN Card Number", key="signup_pan").upper()  # Force uppercase for PAN
            password: str | None = st.text_input("Choose a Password", type="password", key="signup_pass")

            if st.button("Sign Up", type="primary", use_container_width=True):
                # Basic validation to ensure no fields are empty
                if not all([username, email, phone, pancard, password]):
                    st.error("All fields are required.")
                else:
                    success, message = create_user(username, email, phone, pancard, password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)


# --- Router ---
def render_auth_page():
    # Centering the radio buttons using columns
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        option = st.radio("Select Action", ["Login", "Signup"], horizontal=True, key="auth_action_radio")

    if option == "Login":
        render_login_page()
    else:
        render_signup_page()


# --- Main ---
# Initialize the database table structure
init_db()

