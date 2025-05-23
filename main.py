import streamlit as st
import logging
from db import init_db
import utils
from auth import login, register
from booking import booking_page
from admin import admin_page

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Инициализация БД
init_db()

# Состояние сессии по умолчанию
for key, val in [("logged_in", False), ("username", ""), ("role", "")]:
    st.session_state.setdefault(key, val)

st.title("Система бронирования дорожек в бассейне")

if not st.session_state["logged_in"]:
    action = st.selectbox("Действие", ["Войти", "Регистрация"])
    if action == "Войти":
        login()
    else:
        register()
else:
    st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Выход"):
        user = st.session_state["username"]
        st.session_state.update(logged_in=False, username="", role="")
        logger.info(f"User '{user}' logged out")
        utils.safe_rerun()

    if st.session_state["role"] == "admin":
        admin_page()
    else:
        booking_page()