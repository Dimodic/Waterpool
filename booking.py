# booking.py
import streamlit as st
import utils
from datetime import datetime, timedelta, date as dt_date
import pandas as pd

# Кэширование тяжёлых запросов
@st.cache_data(ttl=300)
def get_timeslots():
    return utils.list_timeslots()

@st.cache_data(ttl=300)
def get_slot_status(week_start_iso: str, username: str):
    week_start = datetime.fromisoformat(week_start_iso).date()
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    timeslots = get_timeslots()

    user_bookings = utils.list_user_bookings(username)
    user_set = {(b["date"], b["time"]) for b in user_bookings}

    booking_map = set()
    for single_date in week_dates:
        all_b = utils.list_all_bookings_for_date(single_date)
        for b in all_b:
            booking_map.add((b["date"], b["time"]))

    closed_set = set()
    for single_date in week_dates:
        for item in utils.list_closed_slots(single_date):
            closed_set.add((item["date"], item["time"]))

    data = {}
    for t in timeslots:
        row = []
        for single_date in week_dates:
            key = (single_date, t)
            if key in user_set:
                status = "Ваша запись"
            elif key in closed_set or key in booking_map:
                status = "Недоступно"
            else:
                status = "Доступно"
            row.append(status)
        data[t] = row

    day_labels = [
        d.strftime("%d.%m") + " " + ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][d.weekday()]
        for d in week_dates
    ]
    df = pd.DataFrame(data, index=day_labels).T
    df.index.name = "Время"
    return df

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    if st.session_state.get("role") == "org":
        booking_page_org()
        return

    # Инициализируем начало недели (понедельник)
    if "week_start_user" not in st.session_state:
        today = dt_date.today()
        st.session_state.week_start_user = today - timedelta(days=today.weekday())

    # Навигация по неделям
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("<< Предыдущая неделя", key="prev_week_user"):
            st.session_state.week_start_user -= timedelta(days=7)
            get_slot_status.clear()
            utils.safe_rerun()
    with col2:
        if st.button("Следующая неделя >>", key="next_week_user"):
            st.session_state.week_start_user += timedelta(days=7)
            get_slot_status.clear()
            utils.safe_rerun()
    with col3:
        picked = st.date_input(
            label="Выберите любую дату недели",
            value=st.session_state.week_start_user,
            key="pick_date_for_week_user"
        )
        if picked != st.session_state.week_start_user:
            st.session_state.week_start_user = picked - timedelta(days=picked.weekday())
            get_slot_status.clear()
            utils.safe_rerun()

    week_start_iso = st.session_state.week_start_user.isoformat()
    df = get_slot_status(week_start_iso, st.session_state["username"])

    # --- Основная двухколоночная раскладка: слева брони, справа таблица занятости ---
    left, right = st.columns([2, 3])

    with right:
        st.markdown("### Занятость дорожек на неделе")
        def color_cells(val):
            if val == "Ваша запись":
                return "background-color: #ADD8E6"
            elif val == "Недоступно":
                return "background-color: #FF7F7F"
            else:
                return "background-color: #90EE90"
        styled = df.style.applymap(color_cells)
        st.dataframe(styled, use_container_width=True)

    with left:
        st.markdown("### Мои бронирования")
        my_bookings = utils.list_user_bookings(st.session_state["username"])
        if my_bookings:
            dfb = pd.DataFrame(my_bookings)
            for _, row in dfb.iterrows():
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                with c1:
                    st.write(row["date"])
                with c2:
                    st.write(row["time"])
                with c3:
                    st.write(row["lane"])
                with c4:
                    st.write(row["trainer"] if row["trainer"] else "Без тренера")
                with c5:
                    if st.button("Удалить", key=f"del_{row['id']}"):
                        utils.remove_booking(row["id"])
                        get_slot_status.clear()
                        st.success("Бронирование удалено")
                        utils.safe_rerun()
                    if st.button("Изменить", key=f"edit_{row['id']}"):
                        st.session_state["edit_booking_id"] = row["id"]
                        st.session_state["edit_booking_data"] = row
                        st.session_state["show_edit_form"] = True
        else:
            st.info("У вас нет бронирований.")

        if st.session_state.get("show_edit_form"):
            b = st.session_state["edit_booking_data"]
            st.markdown("#### Изменить бронирование")
            new_date = st.date_input("Дата", value=b["date"], key="edit_date")
            slots = get_timeslots()
            new_time = st.selectbox("Время", slots, index=slots.index(b["time"]))
            busy_lanes, busy_trainers = utils.lane_trainer_status(new_date, new_time)
            free_lanes = [l for l in range(1, 7) if l not in busy_lanes or l == b["lane"]]
            new_lane = st.selectbox("Дорожка", free_lanes, index=free_lanes.index(b["lane"]))
            scheduled = utils.get_scheduled_trainers(new_date, new_time)
            free_trainers = [t for t in scheduled if t not in busy_trainers or t == b["trainer"]]
            trainer_options = ["Без тренера"] + free_trainers
            trainer_index = trainer_options.index(b["trainer"] if b["trainer"] else "Без тренера")
            new_trainer = st.selectbox("Тренер", trainer_options, index=trainer_index)
            if st.button("Сохранить изменения", key="save_edit_booking"):
                trainer_val = None if new_trainer == "Без тренера" else new_trainer
                ok = utils.update_booking(
                    st.session_state["edit_booking_id"],
                    new_date,
                    new_time,
                    new_lane,
                    trainer_val,
                )
                if ok:
                    get_slot_status.clear()
                    st.success("Бронирование обновлено")
                    st.session_state["show_edit_form"] = False
                    utils.safe_rerun()
                else:
                    st.error("Ошибка при обновлении бронирования")
            if st.button("Отмена", key="cancel_edit_booking"):
                st.session_state["show_edit_form"] = False
                utils.safe_rerun()

        st.markdown("---")
        if not st.session_state.get("is_confirmed", False):
            st.warning("Ваша регистрация ожидает подтверждения администрацией. Пожалуйста, принесите все необходимые бумаги в бассейн.")
            return

        sel_date = st.date_input("Дата бронирования", value=dt_date.today(), key="new_booking_date")
        if sel_date < dt_date.today():
            st.error("Нельзя бронировать прошедшие даты!")
            return

        slots = get_timeslots()
        if not slots:
            st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
            return

        sel_time = st.selectbox("Время", slots, key="new_booking_time")
        if utils.is_slot_closed(sel_date, sel_time):
            st.error("Этот слот закрыт для бронирования администратором.")
            return

        busy_lanes, busy_trainers = utils.lane_trainer_status(sel_date, sel_time)
        free_lanes = [l for l in range(1, 7) if l not in busy_lanes]
        if not free_lanes:
            st.warning("На это время нет свободных дорожек.")
            return

        lane = st.selectbox("Дорожка", free_lanes, key="new_booking_lane")
        scheduled = utils.get_scheduled_trainers(sel_date, sel_time)
        free_trainers = [t for t in scheduled if t not in busy_trainers]
        trainer_options = ["Без тренера"] + free_trainers
        trainer = st.selectbox("Тренер", trainer_options, key="new_booking_trainer")

        if st.button("Забронировать", key="new_booking_btn"):
            if utils.is_slot_closed(sel_date, sel_time):
                st.error("Этот слот закрыт для бронирования администратором.")
                return
            trainer_val = None if trainer == "Без тренера" else trainer
            ok = utils.add_booking(
                st.session_state["username"],
                sel_date,
                sel_time,
                lane,
                trainer_val,
            )
            if ok:
                get_slot_status.clear()
                st.success(f"Бронирование подтверждено: дорожка {lane}, {sel_time}, {trainer}.")
                utils.safe_rerun()
            else:
                st.error("Не удалось забронировать (слот уже занят или вы не подтверждены). Обновите страницу.")

def booking_page_org():
    # Реализация для юр. лиц: аналогично — левая колонка (бронирования/создание), правая (таблица занятости)
    st.subheader("Бронирование дорожек для юридических лиц")

    if "week_start_org" not in st.session_state:
        today = dt_date.today()
        st.session_state.week_start_org = today - timedelta(days=today.weekday())

    # Навигация по неделям
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("<< Предыдущая неделя", key="prev_week_org"):
            st.session_state.week_start_org -= timedelta(days=7)
            get_slot_status.clear()
            utils.safe_rerun()
    with col2:
        if st.button("Следующая неделя >>", key="next_week_org"):
            st.session_state.week_start_org += timedelta(days=7)
            get_slot_status.clear()
            utils.safe_rerun()
    with col3:
        picked = st.date_input(
            label="Выберите любую дату недели",
            value=st.session_state.week_start_org,
            key="pick_date_for_week_org"
        )
        if picked != st.session_state.week_start_org:
            st.session_state.week_start_org = picked - timedelta(days=picked.weekday())
            get_slot_status.clear()
            utils.safe_rerun()

    week_start_iso = st.session_state.week_start_org.isoformat()
    df = get_slot_status(week_start_iso, st.session_state["username"])

    left, right = st.columns([2, 3])

    with right:
        st.markdown("### Занятость дорожек на неделе")
        def color_cells(val):
            if val == "Ваша запись":
                return "background-color: #ADD8E6"
            elif val == "Недоступно":
                return "background-color: #FF7F7F"
            else:
                return "background-color: #90EE90"
        styled = df.style.applymap(color_cells)
        st.dataframe(styled, use_container_width=True)

    with left:
        st.markdown("### Групповые бронирования")
        my_groups = utils.list_org_booking_groups(st.session_state["username"])
        if my_groups:
            dfb = pd.DataFrame(my_groups)
            for _, row in dfb.iterrows():
                c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
                with c1:
                    st.write(row["date"])
                with c2:
                    st.write(row["times"])
                with c3:
                    st.write(row["lanes"])
                with c4:
                    if st.button("Удалить", key=f"org_del_{row['id']}"):
                        utils.remove_org_booking_group(row["id"])
                        get_slot_status.clear()
                        st.success("Групповое бронирование удалено")
                        utils.safe_rerun()
        else:
            st.info("Нет групповых бронирований.")

        # --- Форма нового группового бронирования (можно доработать под вашу логику) ---
        st.markdown("---")
        st.markdown("#### Новое групповое бронирование")
        sel_date = st.date_input("Дата", value=dt_date.today(), key="org_new_group_date")
        slots = get_timeslots()
        sel_times = st.multiselect("Времена", slots, key="org_new_group_times")
        sel_lanes = st.multiselect("Дорожки", list(range(1, 7)), key="org_new_group_lanes")
        if st.button("Забронировать группу", key="org_new_group_btn"):
            if not sel_times or not sel_lanes:
                st.error("Выберите хотя бы одну дорожку и время")
                return
            ok = utils.add_org_booking_group(
                st.session_state["username"],
                sel_date,
                sel_times,
                sel_lanes,
            )
            if ok:
                get_slot_status.clear()
                st.success("Групповое бронирование создано.")
                utils.safe_rerun()
            else:
                st.error("Ошибка бронирования. Возможно, выбранные дорожки уже заняты.")

