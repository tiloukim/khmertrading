import streamlit as st
import hashlib
import os
import alpaca_trade_api as tradeapi
from config import get_api, BASE_URL, LIVE_BASE_URL


def _make_token(username, password):
    """Create a simple auth token from credentials."""
    return hashlib.sha256(f"{username}:{password}:khmertrading".encode()).hexdigest()[:32]


def check_auth() -> bool:
    """Auth with cookie-based persistence via query params.
    Press Enter to submit (uses st.form).
    """
    if st.session_state.get("authenticated"):
        return True

    # Get expected credentials
    expected_user = os.getenv("AUTH_USERNAME", "")
    expected_pass = os.getenv("AUTH_PASSWORD", "")
    if not expected_user or not expected_pass:
        try:
            expected_user = st.secrets["auth"]["username"]
            expected_pass = st.secrets["auth"]["password"]
        except (KeyError, FileNotFoundError):
            return True

    # Check for auth token in query params (persistent login)
    expected_token = _make_token(expected_user, expected_pass)
    params = st.query_params
    if params.get("token") == expected_token:
        st.session_state["authenticated"] = True
        return True

    # Show login form
    st.markdown(
        "<h2 style='text-align:center; margin-top:3rem;'>KhmerTrading</h2>"
        "<p style='text-align:center; color:#94a3b8; font-size:0.85rem; margin-bottom:2rem;'>"
        "Private Family Investment Platform &mdash; Authorized Access Only</p>",
        unsafe_allow_html=True,
    )

    # Disable Chrome password manager popup
    st.markdown("""
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('input').forEach(function(el) {
            el.setAttribute('autocomplete', 'off');
            el.setAttribute('data-lpignore', 'true');
            el.setAttribute('data-form-type', 'other');
        });
    });
    // Also try on Streamlit rerender
    setTimeout(function() {
        document.querySelectorAll('input').forEach(function(el) {
            el.setAttribute('autocomplete', 'off');
            el.setAttribute('data-lpignore', 'true');
            el.setAttribute('data-form-type', 'other');
        });
    }, 1000);
    </script>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username", autocomplete="off")
        password = st.text_input("Password", type="password", autocomplete="new-password")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

    if submitted:
        if username == expected_user and password == expected_pass:
            st.session_state["authenticated"] = True
            # Set token in URL for persistence across refreshes
            st.query_params["token"] = _make_token(username, password)
            st.rerun()
        else:
            st.error("Invalid username or password.")

    return False


def get_user_api(live=False):
    """Return an Alpaca REST client using the user's keys if provided,
    otherwise fall back to the default keys from config."""
    user_key = st.session_state.get("user_api_key", "")
    user_secret = st.session_state.get("user_secret_key", "")

    if user_key and user_secret:
        url = LIVE_BASE_URL if live else BASE_URL
        return tradeapi.REST(user_key, user_secret, url, api_version='v2')

    return get_api(live=live)
