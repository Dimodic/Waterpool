# auth.py
import streamlit as st
import utils

def login():
    st.subheader("Вход")
    username = st.text_input("Логин", key="login_username")
    password = st.text_input("Пароль", type="password", key="login_password")

    if st.button("Войти"):
        role = utils.validate_user(username, password)
        if role:
            # Получаем флаг is_confirmed из БД
            from utils import SessionLocal, User
            with SessionLocal() as db:
                user = db.query(User).filter_by(username=username).first()

            st.session_state.update(
                logged_in=True,
                username=username,
                role=role,
                is_confirmed=user.is_confirmed  # 0 или 1
            )
            st.success("Успешный вход.")
            utils.safe_rerun()
        else:
            st.error("Неверный логин или пароль.")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Зарегистрироваться"):
            st.session_state["auth_page"] = "register"
            utils.safe_rerun()
    with col2:
        if st.button("Регистрация для юр. лиц"):
            st.session_state["auth_page"] = "register_org"
            utils.safe_rerun()

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
        if not all([username, password, first_name, last_name, phone, gender, email]):
            st.error("Заполните все обязательные поля.")
            return

        success = utils.add_user(
            username, password,
            first_name, last_name, middle_name,
            phone, gender, email
        )
        if success:
            role = utils.validate_user(username, password)
            st.session_state.update(
                logged_in=True,
                username=username,
                role=role,
                is_confirmed=False
            )
            st.success("Регистрация прошла успешно. Ждите подтверждения администрации.")
            utils.safe_rerun()
        else:
            st.error("Пользователь с таким логином или email уже существует.")

    st.markdown("---")
    if st.button("Назад ко входу"):
        st.session_state["auth_page"] = "login"
        utils.safe_rerun()

def register_org():
    st.subheader("Регистрация для юридических лиц")
    username     = st.text_input("Логин", key="regorg_username")
    password     = st.text_input("Пароль", type="password", key="regorg_password")
    org_name     = st.text_input("Название организации", key="regorg_orgname")
    contact_name = st.text_input("Контактное лицо", key="regorg_contact_name")
    phone        = st.text_input("Телефон", key="regorg_phone")
    email        = st.text_input("Email", key="regorg_email")

    if st.button("Зарегистрироваться как юр. лицо"):
        if not all([username, password, org_name, contact_name, phone, email]):
            st.error("Заполните все обязательные поля.")
            return
        success = utils.add_user(
            username, password,
            contact_name, "", "",
            phone, "", email,
            role="org",
            org_name=org_name,
            is_confirmed=1
        )
        if success:
            st.session_state.update(
                logged_in=True,
                username=username,
                role="org",
                is_confirmed=True
            )
            st.success("Регистрация организации прошла успешно. Вы вошли в систему.")
            utils.safe_rerun()
        else:
            st.error("Пользователь с таким логином или email уже существует.")

    st.markdown("---")
    if st.button("Назад ко входу", key="org_back"):
        st.session_state["auth_page"] = "login"
        utils.safe_rerun()
