import streamlit as st


def check_auth() -> bool:
    """Simple password-based auth using st.secrets.
    If secrets aren't configured, skip auth entirely (dev mode).
    """
    if st.session_state.get("authenticated"):
        return True

    try:
        expected_user = st.secrets["auth"]["username"]
        expected_pass = st.secrets["auth"]["password"]
    except (KeyError, FileNotFoundError):
        # Secrets not configured – skip auth so the app works in dev
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
