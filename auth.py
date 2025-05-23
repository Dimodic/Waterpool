import streamlit as st
import utils

def login():
    st.subheader("Вход")
    username = st.text_input("Логин", key="login_username")
    password = st.text_input("Пароль", type="password", key="login_password")

    if st.button("Войти"):
        role = utils.validate_user(username, password)
        if role:
            st.session_state.update(
                logged_in=True,
                username=username,
                role=role,
            )
            st.success("Успешный вход.")
            utils.safe_rerun()
        else:
            st.error("Неверный логин или пароль.")

def register():
    st.subheader("Регистрация")
    username = st.text_input("Логин", key="reg_username")
    password = st.text_input("Пароль", type="password", key="reg_password")

    if st.button("Зарегистрироваться"):
        if not username or not password:
            st.error("Заполните оба поля.")
            return
        if utils.add_user(username, password):
            st.success("Регистрация прошла успешно. Теперь войдите.")
        else:
            st.error("Пользователь уже существует.")
