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
    if st.session_state["role"] == "admin":
        # Оставляем старую боковую панель и кнопку выхода слева
        st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
        if st.sidebar.button("Выход"):
            user = st.session_state["username"]
            st.session_state.update(logged_in=False, username="", role="", auth_page="login")
            logger.info(f"User '{user}' logged out")
            utils.safe_rerun()
        admin_page()
    else:
        # --- Пользовательская панель: без sidebar, кнопка выхода сверху справа
        st.markdown(
            """
            <div style='position:fixed;top:1.5rem;right:2.5rem;z-index:1000;text-align:right;'>
                <span style="margin-right:1rem;font-weight:bold;">
                    👤 {username} ({role})
                </span>
                <form action="" method="post">
                    <button type="submit" name="logout-btn" style="
                        background:#f33;color:white;border:none;padding:0.4rem 1.2rem;
                        border-radius:7px;cursor:pointer;font-weight:bold;">
                        Выйти
                    </button>
                </form>
            </div>
            """.format(username=st.session_state['username'], role="Организация" if st.session_state['role']=="org" else "Пользователь"),
            unsafe_allow_html=True
        )

        # Реализация выхода через скрытый html-кликер
        if 'logout-btn' in st.session_state:
            user = st.session_state["username"]
            st.session_state.update(logged_in=False, username="", role="", auth_page="login")
            logger.info(f"User '{user}' logged out")
            utils.safe_rerun()

        st.write("")  # маленький отступ для красоты
        booking_page()
