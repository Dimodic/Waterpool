import streamlit as st
from app import utils
import re

def is_valid_phone(phone):
    # Убираем пробелы и дефисы для удобства
    clean = phone.replace(" ", "").replace("-", "")
    return bool(re.fullmatch(r"\+7\d{10}", clean))


def is_valid_email(email):
    # Простая, но рабочая проверка email
    return bool(re.fullmatch(r"[^@ \t\r\n]+@[^@ \t\r\n]+\.[^@ \t\r\n]+", email))


def login():
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown("<h1 style='text-align:center;'>Система бронирования дорожек в бассейне</h1>",
                    unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>Вход</h2>", unsafe_allow_html=True)

        username = st.text_input("Логин", key="login_username", max_chars=20, help="До 20 символов",
                                 placeholder="Введите логин")
        password = st.text_input("Пароль", type="password", key="login_password", max_chars=32, help="До 32 символов",
                                 placeholder="Введите пароль")

        if st.button("Войти"):
            role = utils.validate_user(username, password)
            if role:
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
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown("<h1 style='text-align:center;'>Система бронирования дорожек в бассейне</h1>",
                    unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>Регистрация</h2>", unsafe_allow_html=True)

        username = st.text_input("Логин", key="reg_username", max_chars=20, help="До 20 символов",
                                 placeholder="Придумайте логин")
        password = st.text_input("Пароль", type="password", key="reg_password", max_chars=32, help="До 32 символов",
                                 placeholder="Придумайте пароль")
        first_name = st.text_input("Имя", key="reg_first_name", max_chars=30, placeholder="Имя")
        last_name = st.text_input("Фамилия", key="reg_last_name", max_chars=30, placeholder="Фамилия")
        middle_name = st.text_input("Отчество", key="reg_middle_name", max_chars=30,
                                    placeholder="Отчество (необязательно)")
        phone = st.text_input("Телефон", key="reg_phone", max_chars=15, placeholder="+7 ХХХ ХХХ ХХ ХХ")
        gender = st.selectbox("Пол", ["Мужской", "Женский", "Другое"], key="reg_gender")
        email = st.text_input("Email", key="reg_email", max_chars=40, placeholder="mail@example.com")

        if st.button("Зарегистрироваться"):
            if not all([username, password, first_name, last_name, phone, gender, email]):
                st.error("Заполните все обязательные поля.")
                return

            # Валидация телефона и email
            if not is_valid_phone(phone):
                st.error("Введите телефон в формате +7XXXXXXXXXX (пример: +7 912 345 67 89).")
                return
            if not is_valid_email(email):
                st.error("Некорректный email.")
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
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.markdown("<h1 style='text-align:center;'>Система бронирования дорожек в бассейне</h1>",
                    unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>Регистрация для юридических лиц</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            <style>
            .auth-input input {max-width: 300px;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        username = st.text_input("Логин", key="regorg_username", max_chars=20, placeholder="Придумайте логин").strip()
        password = st.text_input("Пароль", type="password", key="regorg_password", max_chars=32,
                                 placeholder="Придумайте пароль")
        org_name = st.text_input("Название организации", key="regorg_orgname", max_chars=50,
                                 placeholder="Название юр.лица")
        contact_name = st.text_input("Контактное лицо", key="regorg_contact_name", max_chars=50,
                                     placeholder="ФИО контактного лица")
        phone = st.text_input("Телефон", key="regorg_phone", max_chars=15, placeholder="+7 ХХХ ХХХ ХХ ХХ")
        email = st.text_input("Email", key="regorg_email", max_chars=40, placeholder="mail@example.com")

        if st.button("Зарегистрироваться как юр. лицо"):
            if not all([username, password, org_name, contact_name, phone, email]):
                st.error("Заполните все обязательные поля.")
                return

            # Валидация телефона и email
            if not is_valid_phone(phone):
                st.error("Введите телефон в формате +7XXXXXXXXXX (пример: +7 912 345 67 89).")
                return
            if not is_valid_email(email):
                st.error("Некорректный email.")
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
