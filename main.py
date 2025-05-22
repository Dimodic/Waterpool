import streamlit as st
from db import init_db
import utils
from auth import login, register
from booking import booking_page
from admin import admin_page

# --- инициализация БД (создаёт таблицы при первом запуске) --------------------
init_db()

# --- session state ------------------------------------------------------------
for key, val in [("logged_in", False), ("username", ""), ("role", "")]:
    st.session_state.setdefault(key, val)

# --- UI -----------------------------------------------------------------------
st.title("Система бронирования дорожек в бассейне")

if not st.session_state["logged_in"]:
    action = st.selectbox("Действие", ["Войти", "Регистрация"])
    login() if action == "Войти" else register()
else:
    st.sidebar.write(f"👤 **{st.session_state['username']}** ({st.session_state['role']})")
    if st.sidebar.button("Выход"):
        st.session_state.update(logged_in=False, username="", role="")
        utils.safe_rerun()

    if st.session_state["role"] == "admin":
        admin_page()
    else:
        booking_page()
