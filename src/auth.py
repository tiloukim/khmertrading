import streamlit as st
import alpaca_trade_api as tradeapi
from config import get_api, BASE_URL, LIVE_BASE_URL


def check_auth() -> bool:
    """Simple password-based auth using st.secrets.
    If secrets aren't configured, skip auth entirely (dev mode).
    After login, optionally collect the user's own Alpaca API keys.
    """
    if st.session_state.get("authenticated"):
        # ── Optional API-key form (shown after login) ────────────
        if not st.session_state.get("api_keys_configured"):
            _show_api_key_form()
        return True

    import os
    # Check env vars first (Railway), then secrets.toml (local dev)
    expected_user = os.getenv("AUTH_USERNAME", "")
    expected_pass = os.getenv("AUTH_PASSWORD", "")
    if not expected_user or not expected_pass:
        try:
            expected_user = st.secrets["auth"]["username"]
            expected_pass = st.secrets["auth"]["password"]
        except (KeyError, FileNotFoundError):
            # No auth configured – skip auth (dev mode only)
            return True

    st.markdown(
        "<h2 style='text-align:center; margin-top:3rem;'>🔒 KhmerTrading Login</h2>",
        unsafe_allow_html=True,
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        if username == expected_user and password == expected_pass:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password.")

    return False


def _show_api_key_form():
    """Show a one-time form for users to enter their own Alpaca keys."""
    with st.sidebar.expander("🔑 Your Alpaca API Keys", expanded=False):
        st.caption("Leave blank to use the default (shared) keys.")
        user_key = st.text_input(
            "API Key",
            value=st.session_state.get("user_api_key", ""),
            key="_user_api_key_input",
        )
        user_secret = st.text_input(
            "Secret Key",
            value=st.session_state.get("user_secret_key", ""),
            type="password",
            key="_user_secret_key_input",
        )
        if st.button("Save Keys", key="_save_api_keys"):
            st.session_state["user_api_key"] = user_key.strip()
            st.session_state["user_secret_key"] = user_secret.strip()
            st.session_state["api_keys_configured"] = True
            st.success("API keys saved for this session.")
            st.rerun()
        if st.button("Use Default Keys", key="_use_default_keys"):
            st.session_state["user_api_key"] = ""
            st.session_state["user_secret_key"] = ""
            st.session_state["api_keys_configured"] = True
            st.rerun()


def get_user_api(live=False):
    # type: (bool) -> tradeapi.REST
    """Return an Alpaca REST client using the user's keys if provided,
    otherwise fall back to the default keys from config."""
    user_key = st.session_state.get("user_api_key", "")
    user_secret = st.session_state.get("user_secret_key", "")

    if user_key and user_secret:
        url = LIVE_BASE_URL if live else BASE_URL
        return tradeapi.REST(user_key, user_secret, url, api_version='v2')

    return get_api(live=live)
