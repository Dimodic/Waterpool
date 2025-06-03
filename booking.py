# booking.py
import streamlit as st
import utils
from datetime import timedelta, date as dt_date

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    if st.session_state.get("role") == "org":
        booking_page_org()
        return

    # --- ШАГ 1: Недельный обзор занятости дорожек ---
    if "week_start_user" not in st.session_state:
        today = dt_date.today()
        st.session_state.week_start_user = today - timedelta(days=today.weekday())

    nav1, nav2, nav3 = st.columns([1, 1, 3])
    with nav1:
        if st.button("<< Предыдущая неделя", key="prev_week_user"):
            st.session_state.week_start_user -= timedelta(days=7)
            utils.safe_rerun()
    with nav2:
        if st.button("Следующая неделя >>", key="next_week_user"):
            st.session_state.week_start_user += timedelta(days=7)
            utils.safe_rerun()
    with nav3:
        picked = st.date_input(
            label="Выберите любую дату недели",
            value=st.session_state.week_start_user,
            key="pick_date_for_week_user"
        )
        if picked != st.session_state.week_start_user:
            st.session_state.week_start_user = picked - timedelta(days=picked.weekday())
            utils.safe_rerun()

    week_dates = [
        st.session_state.week_start_user + timedelta(days=i) for i in range(7)
    ]
    day_labels = [
        d.strftime("%d.%m") + " " + ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"][d.weekday()]
        for d in week_dates
    ]

    timeslots = utils.list_timeslots()

    # Собираем информацию о занятости (True/False) для каждой ячейки
    data = {}
    for t in timeslots:
        row = []
        for single_date in week_dates:
            busy_lanes, _ = utils.lane_trainer_status(single_date, t)
            # Если меньше 6 занятых — есть свободное место
            status = "Свободно" if len(busy_lanes) < 6 and not utils.is_slot_closed(single_date, t) else "Занято"
            row.append(status)
        data[t] = row

    # Создаём DataFrame
    import pandas as pd
    df = pd.DataFrame(data, index=day_labels).T
    df.index.name = "Время"
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    # --- ШАГ 2: Мои текущие бронирования ---
    st.markdown("### Мои бронирования")
    my_bookings = utils.list_user_bookings(st.session_state["username"])
    if my_bookings:
        dfb = pd.DataFrame(my_bookings)
        for _, row in dfb.iterrows():
            c1, c2, c3, c4, c5 = st.columns([2,2,2,2,2])
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
                    st.success("Бронирование удалено")
                    utils.safe_rerun()
                if st.button("Изменить", key=f"edit_{row['id']}"):
                    st.session_state["edit_booking_id"] = row["id"]
                    st.session_state["edit_booking_data"] = row
                    st.session_state["show_edit_form"] = True
    else:
        st.info("У вас нет бронирований.")

    # --- Форма редактирования ---
    if st.session_state.get("show_edit_form"):
        b = st.session_state["edit_booking_data"]
        st.markdown("#### Изменить бронирование")
        new_date = st.date_input("Дата", value=b["date"], key="edit_date")
        slots = utils.list_timeslots()
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
                st.success("Бронирование обновлено")
                st.session_state["show_edit_form"] = False
                utils.safe_rerun()
            else:
                st.error("Ошибка при обновлении бронирования")
        if st.button("Отмена", key="cancel_edit_booking"):
            st.session_state["show_edit_form"] = False
            utils.safe_rerun()

    st.markdown("---")
    # --- ШАГ 3: Новое бронирование (только для подтверждённых) ---
    if not st.session_state.get("is_confirmed", False):
        st.warning("Ваша регистрация ожидает подтверждения администрацией. Пожалуйста, принесите все необходимые бумаги в бассейн.")
        return

    sel_date = st.date_input("Дата бронирования", value=dt_date.today(), key="new_booking_date")
    if sel_date < dt_date.today():
        st.error("Нельзя бронировать прошедшие даты!")
        return

    slots = utils.list_timeslots()
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
            st.success(f"Бронирование подтверждено: дорожка {lane}, {sel_time}, {trainer}.")
            utils.safe_rerun()
        else:
            st.error("Не удалось забронировать (слот уже занят или вы не подтверждены). Обновите страницу.")

def booking_page_org():
    # Логика для юр. лиц остаётся без изменений...
    pass
