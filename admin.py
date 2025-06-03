# admin.py
import streamlit as st
import pandas as pd
import utils
from datetime import datetime, timedelta, date as dt_date

# Кэширование списков слотов и бронирований
@st.cache_data(ttl=300)
def get_timeslots_admin():
    return utils.list_timeslots()

@st.cache_data(ttl=300)
def get_closed_map(week_start_iso):
    week_start = datetime.fromisoformat(week_start_iso).date()
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    closed_map = {}
    for single_date in week_dates:
        for item in utils.list_closed_slots(single_date):
            closed_map[(item["date"], item["time"])] = item["id"]
    return closed_map

@st.cache_data(ttl=300)
def get_booking_map(week_start_iso):
    week_start = datetime.fromisoformat(week_start_iso).date()
    booking_map = set()
    for i in range(7):
        single_date = week_start + timedelta(days=i)
        for b in utils.list_all_bookings_for_date(single_date):
            booking_map.add((b["date"], b["time"]))
    return booking_map

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

# ------------------ Недельный календарь закрытых слотов --------------------
def manage_timeslots():
    st.subheader("Управление слотами (закрытые слоты)")

    if "week_start_admin" not in st.session_state:
        today = dt_date.today()
        st.session_state.week_start_admin = today - timedelta(days=today.weekday())

    nav1, nav2, nav3 = st.columns([1, 1, 3])
    with nav1:
        if st.button("<< Предыдущая неделя", key="admin_prev_week"):
            st.session_state.week_start_admin -= timedelta(days=7)
            get_closed_map.clear()
            get_booking_map.clear()
            utils.safe_rerun()
    with nav2:
        if st.button("Следующая неделя >>", key="admin_next_week"):
            st.session_state.week_start_admin += timedelta(days=7)
            get_closed_map.clear()
            get_booking_map.clear()
            utils.safe_rerun()
    with nav3:
        picked = st.date_input(
            label="Выберите любую дату недели",
            value=st.session_state.week_start_admin,
            key="pick_date_for_week_admin"
        )
        if picked != st.session_state.week_start_admin:
            st.session_state.week_start_admin = picked - timedelta(days=picked.weekday())
            get_closed_map.clear()
            get_booking_map.clear()
            utils.safe_rerun()

    week_start_iso = st.session_state.week_start_admin.isoformat()
    week_dates = [st.session_state.week_start_admin + timedelta(days=i) for i in range(7)]
    day_labels = [
        d.strftime("%d.%m") + " " + ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()]
        for d in week_dates
    ]

    timeslots = get_timeslots_admin()
    closed_map = get_closed_map(week_start_iso)
    booking_map = get_booking_map(week_start_iso)

    # Строим таблицу: первая строка — заголовки
    header_cols = st.columns([1] + [1]*7)
    header_cols[0].write("Время")
    for idx, label in enumerate(day_labels):
        header_cols[idx+1].write(label)

    for t in timeslots:
        row_cols = st.columns([1] + [1]*7)
        row_cols[0].write(t)
        for idx, single_date in enumerate(week_dates):
            cell_key = f"cell_admin_{single_date}_{t}"
            if (single_date, t) in closed_map:
                if row_cols[idx+1].button("❌", key=cell_key):
                    utils.remove_closed_slot(closed_map[(single_date, t)])
                    get_closed_map.clear()
                    get_booking_map.clear()
                    st.success(f"Слот {t} на {single_date} снова доступен")
                    utils.safe_rerun()
            elif (single_date, t) in booking_map:
                row_cols[idx+1].write("📌")
            else:
                row_cols[idx+1].write("")

    st.markdown("---")
    st.markdown("#### Добавить новый закрытый слот")
    add_date = st.date_input(
        label="Дата слота",
        value=dt_date.today(),
        key="add_closed_date_admin"
    )
    add_time = st.selectbox(
        label="Время слота",
        options=timeslots,
        key="add_closed_time_admin"
    )
    add_comment = st.text_input("Комментарий (необязательно)", key="add_closed_comment_admin")

    if st.button("Добавить закрытый слот"):
        ok = utils.add_closed_slot(add_date, add_time, add_comment)
        if ok:
            get_closed_map.clear()
            st.success(f"Слот {add_time} на {add_date} закрыт")
            utils.safe_rerun()
        else:
            st.warning("Такой закрытый слот уже существует.")

# ------------------ Управление тренерами и прочее ----------------------------
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
    st.session_state.setdefault("show_add_trainer_schedule", False)
    schedules = utils.list_trainer_schedule()
    day_names = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]

    if schedules:
        header_cols = st.columns([2,2,2,1])
        for col, text in zip(header_cols, ["Тренер", "День недели", "Время", "Удалить"]):
            col.write(text)

        for row in schedules:
            cols = st.columns([2,2,2,1])
            with cols[0]:
                st.write(row["trainer"])
            with cols[1]:
                st.write(day_names[row["day_of_week"]])
            with cols[2]:
                st.write(row["time"])
            with cols[3]:
                if st.button("🗑️", key=f"del_sched_{row['id']}"):
                    utils.remove_trainer_schedule(row["id"])
                    st.success("Запись удалена")
                    utils.safe_rerun()
    else:
        st.info("Нет записей в расписании.")

    st.markdown("---")
    if not st.session_state["show_add_trainer_schedule"]:
        if st.button("Добавить расписание"):
            st.session_state["show_add_trainer_schedule"] = True

    if st.session_state["show_add_trainer_schedule"]:
        st.markdown("#### Добавить записи в расписание")
        trainers = utils.list_trainers()
        if not trainers:
            st.warning("Сначала добавьте хотя бы одного тренера в разделе «Тренеры».")
        else:
            trainer = st.selectbox("Тренер", trainers, key="new_sch_trainer")
            day = st.selectbox("День недели", day_names, key="new_sch_day")
            timeslots = get_timeslots_admin()
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                start_time = st.selectbox("Время начала", timeslots, key="new_sch_time_start")
            with col_time2:
                end_time = st.selectbox("Время конца", timeslots, index=len(timeslots)-1, key="new_sch_time_end")
            dow_map = {name: idx for idx, name in enumerate(day_names)}

            col_btn1, col_btn2 = st.columns([1,1])
            with col_btn1:
                if st.button("Добавить", key="add_trainer_schedule_btn"):
                    start_idx = timeslots.index(start_time)
                    end_idx = timeslots.index(end_time)
                    if start_idx > end_idx:
                        st.warning("Время начала не может быть позже времени конца!")
                    else:
                        ok_all = True
                        for tt in timeslots[start_idx:end_idx+1]:
                            ok = utils.add_trainer_schedule(trainer, dow_map[day], tt)
                            ok_all = ok_all and ok
                        if ok_all:
                            st.success("Записи добавлены в расписание")
                        else:
                            st.warning("Некоторые записи уже существуют или возникла ошибка.")
                        st.session_state["show_add_trainer_schedule"] = False
                        utils.safe_rerun()
            with col_btn2:
                if st.button("Отмена", key="cancel_trainer_schedule"):
                    st.session_state["show_add_trainer_schedule"] = False
                    utils.safe_rerun()

def manage_users():
    st.subheader("Список пользователей")
    users = utils.list_users()
    df = pd.DataFrame(users)
    search = st.text_input("Поиск", key="user_search")
    if search:
        mask = df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)
        df = df[mask]
    if df.empty:
        st.info("Нет пользователей по вашему запросу.")
        return

    header_cols = st.columns([3,2,2,3,2,2,2,2,2])
    headers = [
        "Логин", "Имя", "Фамилия", "Email", "Телефон", "Роль", "Статус", "Подтвердить", "Удалить"
    ]
    for col, text in zip(header_cols, headers):
        col.write(text)

    for _, row in df.iterrows():
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
                    if st.button("✅", key=f"confirm_{row['id']}"):
                        utils.confirm_user(row["id"])
                        get_closed_map.clear()
                        get_booking_map.clear()
                        st.success(f"Пользователь {row['username']} подтвержден")
                        utils.safe_rerun()
            with cols[8]:
                if row["username"] != "admin":
                    if st.button("🗑️", key=f"delete_{row['id']}"):
                        utils.remove_user(row["id"])
                        st.success(f"Пользователь {row['username']} удален")
                        utils.safe_rerun()

def manage_bookings():
    st.subheader("Бронирования на выбранный день")
    sel_date = st.date_input("Дата", value=dt_date.today(), key="admin_bookings_date")
    all_bookings = utils.list_all_bookings_for_date(sel_date)
    if not all_bookings:
        st.info("На выбранный день нет бронирований.")
        return

    header_cols = st.columns([2,2,2,2,2,2,1])
    headers = [
        "Пользователь", "Дата", "Время", "Дорожка", "Тренер", "ID", "Удалить"
    ]
    for col, text in zip(header_cols, headers):
        col.write(text)

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
