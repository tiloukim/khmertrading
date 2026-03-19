import streamlit as st
import hashlib
import json
import os
import alpaca_trade_api as tradeapi
from config import get_api, BASE_URL, LIVE_BASE_URL
from pathlib import Path

USERS_FILE = Path(__file__).parent.parent / "users.json"


def _load_users():
    """Load users from JSON file. Falls back to AUTH_USERNAME/AUTH_PASSWORD env vars."""
    users = {}
    # Load from env var (admin account)
    admin_user = os.getenv("AUTH_USERNAME", "")
    admin_pass = os.getenv("AUTH_PASSWORD", "")
    if admin_user and admin_pass:
        users[admin_user] = {"password": admin_pass, "role": "admin"}

    # Load additional users from file
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE) as f:
                file_users = json.load(f)
                users.update(file_users)
        except Exception:
            pass

    return users


def _save_user(username, password, name=""):
    """Save a new user to the JSON file."""
    users = {}
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE) as f:
                users = json.load(f)
        except Exception:
            pass

    users[username] = {"password": password, "role": "family", "name": name}

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _make_token(username, password):
    """Create a simple auth token from credentials."""
    return hashlib.sha256(f"{username}:{password}:khmertrading".encode()).hexdigest()[:32]


def _show_logo():
    """Display the logo centered."""
    logo_path = Path(__file__).parent.parent / "khmertrading-logo.png"
    if logo_path.exists():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(str(logo_path), use_container_width=True)


def check_auth() -> bool:
    """Multi-user auth with login and signup."""
    if st.session_state.get("authenticated"):
        return True

    users = _load_users()
    if not users:
        return True

    # Check for auth token in query params (persistent login)
    params = st.query_params
    token = params.get("token", "")
    if token:
        for uname, udata in users.items():
            if _make_token(uname, udata["password"]) == token:
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = uname
                st.session_state["user_role"] = udata.get("role", "family")
                return True

    # Show logo
    _show_logo()

    # Tabs for Login / Sign Up
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username", autocomplete="off")
            password = st.text_input("Password", type="password", autocomplete="new-password")
            submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

        if submitted:
            users = _load_users()  # Reload in case new signup
            if username in users and users[username]["password"] == password:
                st.session_state["authenticated"] = True
                st.session_state["current_user"] = username
                st.session_state["user_role"] = users[username].get("role", "family")
                st.query_params["token"] = _make_token(username, password)
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with tab_signup:
        invite_code = os.getenv("INVITE_CODE", "family2024")
        with st.form("signup_form"):
            st.caption("Ask the admin for the invite code to create an account.")
            new_name = st.text_input("Your Name")
            new_user = st.text_input("Choose a Username")
            new_pass = st.text_input("Choose a Password", type="password")
            new_pass2 = st.text_input("Confirm Password", type="password")
            new_invite = st.text_input("Invite Code")
            signup_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

        if signup_submitted:
            if not new_name or not new_user or not new_pass:
                st.error("Please fill in all fields.")
            elif new_pass != new_pass2:
                st.error("Passwords don't match.")
            elif new_invite != invite_code:
                st.error("Invalid invite code.")
            elif new_user in _load_users():
                st.error("Username already taken.")
            else:
                _save_user(new_user, new_pass, new_name)
                st.success(f"Account created! You can now login as '{new_user}'.")

    return False


def get_user_api(live=False):
    """Return an Alpaca REST client."""
    user_key = st.session_state.get("user_api_key", "")
    user_secret = st.session_state.get("user_secret_key", "")

    if user_key and user_secret:
        url = LIVE_BASE_URL if live else BASE_URL
        return tradeapi.REST(user_key, user_secret, url, api_version='v2')

    return get_api(live=live)
