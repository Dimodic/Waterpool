# main.py
import streamlit as st
import logging

# 1) Широкий режим всего приложения
st.set_page_config(layout='wide')

from db import init_db
import utils
from auth import login, register, register_org
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
for key, val in [
    ("logged_in", False),
    ("username", ""),
    ("role", ""),
    ("auth_page", "login")  # login / register / register_org
]:
    st.session_state.setdefault(key, val)

# 2) Если пользователь не залогинен — показываем заголовок + форма входа/регистрации
if not st.session_state["logged_in"]:
    st.title("Система бронирования дорожек в бассейне")
    if st.session_state["auth_page"] == "login":
        login()
    elif st.session_state["auth_page"] == "register_org":
        register_org()
    else:
        register()

# 3) Если залогинен, рисуем сайдбар и переключаемся по ролям
else:
    st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Выход"):
        user = st.session_state["username"]
        st.session_state.update(logged_in=False, username="", role="", auth_page="login")
        logger.info(f"User '{user}' logged out")
        utils.safe_rerun()

    # 4) Если не админ — показываем заголовок + страницу броней
    if st.session_state["role"] != "admin":
        st.title("Система бронирования дорожек в бассейне")
        booking_page()
    # 5) Если админ — переходим в админский раздел (заголовок уже не нужен)
    else:
        admin_page()
