# main.py
import streamlit as st
st.set_page_config(layout='wide')

import logging
from app.db import init_db
from app import utils
from auth import login, register, register_org
from booking import booking_page
from admin import admin_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("../app.log", encoding="utf-8"),
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

def logout_action():
    user = st.session_state["username"]
    st.session_state.update(logged_in=False, username="", role="", auth_page="login")
    logger.info(f"User '{user}' logged out")
    utils.safe_rerun()

if not st.session_state["logged_in"]:
    if st.session_state["auth_page"] == "login":
        login()
    elif st.session_state["auth_page"] == "register_org":
        register_org()
    else:
        register()
else:
    if st.session_state["role"] == "admin":
        st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
        if st.sidebar.button("Выход"):
            logout_action()
        admin_page()
    else:
        # Обычный пользователь или юр. лицо: кнопка справа в первой строке
        cols = st.columns([6, 1])
        with cols[1]:
            st.write(
                f"<div style='text-align:right; font-weight:bold;'>"
                f"👤 {st.session_state['username']} "
                f"({'Организация' if st.session_state['role']=='org' else 'Пользователь'})"
                f"</div>", unsafe_allow_html=True)
            if st.button("Выйти", key="logout_btn_right"):
                logout_action()
        booking_page()
