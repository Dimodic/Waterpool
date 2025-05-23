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
    username     = st.text_input("Логин", key="reg_username")
    password     = st.text_input("Пароль", type="password", key="reg_password")
    first_name   = st.text_input("Имя", key="reg_first_name")
    last_name    = st.text_input("Фамилия", key="reg_last_name")
    middle_name  = st.text_input("Отчество", key="reg_middle_name")
    phone        = st.text_input("Телефон", key="reg_phone")
    gender       = st.selectbox("Пол", ["Мужской", "Женский", "Другое"], key="reg_gender")
    email        = st.text_input("Email", key="reg_email")

    if st.button("Зарегистрироваться"):
        # Проверяем обязательные поля
        if not all([username, password, first_name, last_name, phone, gender, email]):
            st.error("Заполните все обязательные поля.")
            return
        success = utils.add_user(
            username, password,
            first_name, last_name, middle_name,
            phone, gender, email
        )
        if success:
            st.success("Регистрация прошла успешно. Теперь войдите.")
            utils.safe_rerun()
        else:
            st.error("Пользователь с таким логином или email уже существует.")
