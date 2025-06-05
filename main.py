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
    st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Выход"):
        user = st.session_state["username"]
        st.session_state.update(logged_in=False, username="", role="", auth_page="login")
        logger.info(f"User '{user}' logged out")
        utils.safe_rerun()

    if st.session_state["role"] != "admin":
        st.title("Система бронирования дорожек в бассейне")
        booking_page()
    else:
        admin_page()
