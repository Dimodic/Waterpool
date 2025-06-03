import streamlit as st
st.set_page_config(layout='wide')
import pandas as pd
import utils
from datetime import time as dt_time, date as dt_date

def admin_page():
    st.sidebar.title("Администрирование")
    section = st.sidebar.radio("Раздел", [
        "Слоты",
        "Тренеры",
        "Расписание тренеров",
        "Пользователи",
        "Бронирования"
    ])

    if section == "Слоты":
        manage_timeslots()
    elif section == "Тренеры":
        manage_trainers()
    elif section == "Расписание тренеров":
        manage_trainer_schedule()
    elif section == "Пользователи":
        manage_users()
    elif section == "Бронирования":
        manage_bookings()

def manage_timeslots():
    st.subheader("Управление слотами")
    current = utils.list_timeslots()
    st.write("Текущие интервалы:", ", ".join(current) if current else "—")

    new_time = st.time_input("Новый интервал (чч:мм)", value=dt_time(9, 0), key="new_timeslot")
    if st.button("Добавить слот"):
        if utils.add_timeslot(new_time):
            st.success(f"Добавлен {new_time.strftime('%H:%M')}")
            utils.safe_rerun()
        else:
            st.warning("Такой интервал уже есть.")

    if current:
        rem = st.selectbox("Удалить интервал", current, key="rem_timeslot")
        if st.button("Удалить слот"):
            utils.remove_timeslot(rem)
            st.success(f"Удалён {rem}")
            utils.safe_rerun()

    st.markdown("---")
    st.subheader("Закрытые слоты на дату")
    sel_date = st.date_input("Дата для управления закрытыми слотами", value=dt_date.today(), key="closed_slots_date")
    closed = utils.list_closed_slots(sel_date)
    if closed:
        st.write("Закрытые интервалы:")
        header_cols = st.columns([2,2,4,1])
        for col, text in zip(header_cols, ["Время", "Дата", "Комментарий", "Удалить"]):
            col.write(text)
        for row in closed:
            cols = st.columns([2,2,4,1])
            with cols[0]:
                st.write(row["time"])
            with cols[1]:
                st.write(str(row["date"]))
            with cols[2]:
                st.write(row["comment"] or "")
            with cols[3]:
                if st.button("🗑️", key=f"del_closed_{row['id']}"):
                    utils.remove_closed_slot(row["id"])
                    st.success("Слот снова доступен для бронирования")
                    utils.safe_rerun()
    else:
        st.info("Нет закрытых слотов на выбранную дату.")

    st.markdown("---")
    st.subheader("Закрыть интервалы на дату по диапазону")
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("Время начала (закрыть с)", current, key="closed_start_time")
    with col2:
        end_time = st.selectbox("Время конца (закрыть по)", current, index=len(current)-1, key="closed_end_time")
    comment = st.text_input("Комментарий (необязательно)", key="closed_comment")
    if st.button("Закрыть выбранные интервалы"):
        start_idx = current.index(start_time)
        end_idx = current.index(end_time)
        if start_idx > end_idx:
            st.warning("Время начала не может быть позже времени конца!")
        else:
            count = utils.add_closed_slots_range(sel_date, start_time, end_time, comment)
            if count:
                st.success(f"Закрыто {count} интервал(ов) на {sel_date}")
                utils.safe_rerun()
            else:
                st.warning("Ни один слот не был закрыт (возможно, уже закрыты или ошибка диапазона)")

def manage_trainers():
    st.subheader("Управление тренерами")
    trainers = utils.list_trainers()
    st.write("Существующие тренеры:", ", ".join(trainers) if trainers else "—")

    new_tr = st.text_input("Имя нового тренера", key="new_trainer")
    if st.button("Добавить тренера"):
        if utils.add_trainer(new_tr):
            st.success(f"Добавлен тренер {new_tr}")
            utils.safe_rerun()
        else:
            st.warning("Тренер с таким именем уже есть.")

    if trainers:
        rem_tr = st.selectbox("Удалить тренера", trainers, key="rem_trainer")
        if st.button("Удалить тренера"):
            utils.remove_trainer(rem_tr)
            st.success(f"Тренер {rem_tr} удалён")
            utils.safe_rerun()

def manage_trainer_schedule():
    st.subheader("Управление расписанием тренеров")
    trainers  = utils.list_trainers()
    trainer   = st.selectbox("Тренер", trainers, key="sch_trainer")
    schedules = utils.list_trainer_schedule()
    # Фильтруем расписание по выбранному тренеру
    filtered = [s for s in schedules if s["trainer"] == trainer]
    if filtered:
        df = pd.DataFrame(filtered)
        header_cols = st.columns([2,2,2,2,1])
        headers = ["Тренер", "День недели", "Время", "ID", "Удалить"]
        for col, text in zip(header_cols, headers):
            col.write(text)
        day_names = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        for i, row in df.iterrows():
            cols = st.columns([2,2,2,2,1])
            with cols[0]:
                st.write(row["trainer"])
            with cols[1]:
                st.write(day_names[row["day_of_week"]])
            with cols[2]:
                st.write(row["time"])
            with cols[3]:
                st.write(row["id"])
            with cols[4]:
                if st.button("🗑️", key=f"del_sched_{row['id']}"):
                    utils.remove_trainer_schedule(row["id"])
                    st.success("Запись удалена")
                    utils.safe_rerun()
    else:
        st.info("Нет расписания для выбранного тренера.")

    day_names = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    day       = st.selectbox("День недели", day_names, key="sch_day")
    timeslots = utils.list_timeslots()
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        start_time = st.selectbox("Время начала", timeslots, key="sch_time_start")
    with col_time2:
        end_time = st.selectbox("Время конца", timeslots, index=len(timeslots)-1, key="sch_time_end")
    dow_map = {name: idx for idx, name in enumerate(day_names)}
    if st.button("Добавить в расписание"):
        start_idx = timeslots.index(start_time)
        end_idx = timeslots.index(end_time)
        if start_idx > end_idx:
            st.warning("Время начала не может быть позже времени конца!")
        else:
            ok_all = True
            for t in timeslots[start_idx:end_idx+1]:
                ok = utils.add_trainer_schedule(trainer, dow_map[day], t)
                ok_all = ok_all and ok
            if ok_all:
                st.success("Записи добавлены в расписание")
                utils.safe_rerun()
            else:
                st.warning("Некоторые записи уже существуют или неверные данные.")

def manage_users():
    st.subheader("Список пользователей")
    users = utils.list_users()
    df = pd.DataFrame(users)
    search = st.text_input("Поиск", key="user_search")
    if search:
        mask = df.apply(lambda row: row.astype(str)
                        .str.contains(search, case=False).any(), axis=1)
        df = df[mask]
    if df.empty:
        st.info("Нет пользователей по вашему запросу.")
        return
    # Заголовки
    header_cols = st.columns([3,2,2,3,2,2,2,2,2])
    headers = [
        "Логин", "Имя", "Фамилия", "Email", "Телефон", "Роль", "Статус", "Подтвердить", "Удалить"
    ]
    for col, text in zip(header_cols, headers):
        col.write(text)
    # Данные
    for i, row in df.iterrows():
        color_class = "confirmed" if row["is_confirmed"] else "not-confirmed"
        with st.container():
            cols = st.columns([3,2,2,3,2,2,2,2,2])
            with cols[0]:
                st.write(row["username"])
            with cols[1]:
                st.write(row["first_name"])
            with cols[2]:
                st.write(row["last_name"])
            with cols[3]:
                st.write(row["email"])
            with cols[4]:
                st.write(row["phone"])
            with cols[5]:
                st.write(row["role"])
            with cols[6]:
                st.write("Подтвержден" if row["is_confirmed"] else "Ожидает подтверждения")
            with cols[7]:
                if not row["is_confirmed"]:
                    if st.button("\u2705", key=f"confirm_{row['id']}"):
                        utils.confirm_user(row["id"])
                        st.success(f"Пользователь {row['username']} подтвержден")
                        utils.safe_rerun()
            with cols[8]:
                if row["username"] != "admin":
                    if st.button("\U0001F5D1", key=f"delete_{row['id']}"):
                        utils.remove_user(row["id"])
                        st.success(f"Пользователь {row['username']} удален")
                        utils.safe_rerun()

def manage_bookings():
    st.subheader("Бронирования на выбранный день")
    from datetime import date as dt_date
    sel_date = st.date_input("Дата", value=dt_date.today(), key="admin_bookings_date")
    all_bookings = utils.list_all_bookings_for_date(sel_date)
    if not all_bookings:
        st.info("На выбранный день нет бронирований.")
        return
    # Заголовки
    header_cols = st.columns([2,2,2,2,2,2,1])
    headers = [
        "Пользователь", "Дата", "Время", "Дорожка", "Тренер", "ID", "Удалить"
    ]
    for col, text in zip(header_cols, headers):
        col.write(text)
    # Данные
    for row in all_bookings:
        cols = st.columns([2,2,2,2,2,2,1])
        with cols[0]:
            st.write(row["user"])
        with cols[1]:
            st.write(str(row["date"]))
        with cols[2]:
            st.write(row["time"])
        with cols[3]:
            st.write(row["lane"])
        with cols[4]:
            st.write(row["trainer"])
        with cols[5]:
            st.write(row["id"])
        with cols[6]:
            if st.button("🗑️", key=f"admin_del_booking_{row['id']}"):
                utils.remove_booking(row["id"])
                st.success("Бронирование удалено")
                utils.safe_rerun()
