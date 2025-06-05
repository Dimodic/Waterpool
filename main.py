# main.py
import streamlit as st
st.set_page_config(layout='wide')

import logging
from db import init_db
import utils
from auth import login, register, register_org
from booking import booking_page
from admin import admin_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

init_db()

for key, val in [
    ("logged_in", False),
    ("username", ""),
    ("role", ""),
    ("auth_page", "login")
]:
    st.session_state.setdefault(key, val)

if not st.session_state["logged_in"]:
    st.title("Система бронирования дорожек в бассейне")
    if st.session_state["auth_page"] == "login":
        login()
    elif st.session_state["auth_page"] == "register_org":
        register_org()
    else:
        register()
else:
    # Кнопка выхода и имя пользователя в правом верхнем углу
    col_user, col_logout = st.columns([9, 1])
    with col_user:
        st.markdown(
            f"<div style='text-align: right; font-weight: bold;'>"
            f"👤 {st.session_state['username']} ({st.session_state['role']})"
            f"</div>",
            unsafe_allow_html=True,
        )
    with col_logout:
        if st.button("Выйти"):
            user = st.session_state["username"]
            st.session_state.update(logged_in=False, username="", role="", auth_page="login")
            logger.info(f"User '{user}' logged out")
            utils.safe_rerun()

    st.markdown("---")

    if st.session_state["role"] != "admin":
        st.title("Система бронирования дорожек в бассейне")
        booking_page()
    else:
        admin_page()
