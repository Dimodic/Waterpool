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

def logout_action():
    user = st.session_state["username"]
    st.session_state.update(logged_in=False, username="", role="", auth_page="login")
    logger.info(f"User '{user}' logged out")
    utils.safe_rerun()

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
        st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
        if st.sidebar.button("Выход"):
            logout_action()
        admin_page()
    else:
        # --- Кнопка выхода справа вверху (только для user/org) ---
        st.markdown("""
        <style>
        .logout-btn-wrap {
            position: fixed;
            top: 1.2rem;
            right: 2.2rem;
            z-index: 10000;
            display: flex;
            align-items: center;
        }
        .logout-btn-profile {
            font-weight: bold;
            margin-right: 1.2rem;
        }
        </style>
        """, unsafe_allow_html=True)
        col_logout = st.columns([12, 1])
        with col_logout[1]:
            st.empty()  # чтобы не было кнопки в потоке обычного вывода

        # Теперь реальный лайфхак: размещаем через place!
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        logout_btn_placeholder = st.empty()
        with logout_btn_placeholder.container():
            st.markdown(
                f"""
                <div class="logout-btn-wrap">
                    <span class="logout-btn-profile">
                        👤 {st.session_state['username']} ({'Организация' if st.session_state['role']=='org' else 'Пользователь'})
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
            btn = st.button("Выйти", key="logout_top_btn", help="Выйти из профиля", use_container_width=False)

        if btn:
            logout_action()

        booking_page()
