import streamlit as st
import utils
from datetime import date as dt_date

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    if st.session_state.get("role") == "org":
        booking_page_org()
        return

    # --- Мои бронирования ---
    st.markdown("### Мои бронирования")
    my_bookings = utils.list_user_bookings(st.session_state["username"])
    if my_bookings:
        import pandas as pd
        df = pd.DataFrame(my_bookings)
        for i, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([2,2,2,2,2])
            with col1:
                st.write(row["date"])
            with col2:
                st.write(row["time"])
            with col3:
                st.write(row["lane"])
            with col4:
                st.write(row["trainer"] if row["trainer"] else "Без тренера")
            with col5:
                if st.button(f"Удалить", key=f"del_{row['id']}"):
                    utils.remove_booking(row["id"])
                    st.success("Бронирование удалено")
                    utils.safe_rerun()
                if st.button(f"Изменить", key=f"edit_{row['id']}"):
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
    st.markdown("### Новое бронирование")
    sel_date = st.date_input("Дата бронирования", value=dt_date.today(), key="new_booking_date")
    if sel_date < dt_date.today():
        st.error("Нельзя бронировать прошедшие даты!")
        return
    slots = utils.list_timeslots()
    if not slots:
        st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
        return
    sel_time = st.selectbox("Время", slots, key="new_booking_time")

    # проверяем занятость
    busy_lanes, busy_trainers = utils.lane_trainer_status(sel_date, sel_time)

    # Проверка: слот закрыт?
    if utils.is_slot_closed(sel_date, sel_time):
        st.error("Этот слот закрыт для бронирования администратором.")
        return

    free_lanes = [l for l in range(1, 7) if l not in busy_lanes]
    if not free_lanes:
        st.warning("На это время нет свободных дорожек.")
        return
    lane = st.selectbox("Дорожка", free_lanes, key="new_booking_lane")

    # доступные по расписанию и незанятые тренеры
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
    st.markdown("### Мои бронирования (юридическое лицо)")
    my_groups = utils.list_org_booking_groups(st.session_state["username"])
    if my_groups:
        import pandas as pd
        df = pd.DataFrame(my_groups)
        for i, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([2,3,3,2])
            with col1:
                st.write(row["date"])
            with col2:
                st.write(f"Время: {row['times']}")
            with col3:
                st.write(f"Дорожки: {row['lanes']}")
            with col4:
                if st.button(f"Удалить", key=f"org_del_group_{row['id']}"):
                    utils.remove_org_booking_group(row["id"])
                    st.success("Групповая бронь удалена")
                    utils.safe_rerun()
                if st.button(f"Изменить", key=f"org_edit_group_{row['id']}"):
                    st.session_state["org_edit_group_id"] = row["id"]
                    st.session_state["org_edit_group_data"] = row
                    st.session_state["org_show_edit_group_form"] = True
    else:
        st.info("У вас нет бронирований.")

    # --- Форма редактирования группы ---
    if st.session_state.get("org_show_edit_group_form"):
        b = st.session_state["org_edit_group_data"]
        st.markdown("#### Изменить групповую бронь")
        new_date = st.date_input("Дата", value=b["date"], key="org_edit_group_date")
        slots = utils.list_timeslots()
        # Для редактирования: multiselect по времени
        old_times = b["times"].split(",")
        times_selected = st.multiselect("Время", slots, default=old_times, key="org_edit_group_times")
        busy_lanes, _ = utils.lane_trainer_status(new_date, old_times[0])
        old_lanes = [int(x) for x in b["lanes"].split(",")]
        free_lanes = [l for l in range(1, 7) if l not in busy_lanes or l in old_lanes]
        selected_lanes = st.multiselect("Дорожки", free_lanes, default=old_lanes, key="org_edit_group_lanes")
        if st.button("Сохранить изменения", key="org_save_edit_group"):
            if not selected_lanes or not times_selected:
                st.error("Выберите хотя бы одну дорожку и хотя бы одно время.")
            else:
                ok = utils.update_org_booking_group(
                    st.session_state["org_edit_group_id"],
                    new_date,
                    times_selected,
                    selected_lanes,
                )
                if ok:
                    st.success("Групповая бронь обновлена")
                    st.session_state["org_show_edit_group_form"] = False
                    utils.safe_rerun()
                else:
                    st.error("Ошибка при обновлении групповой брони")
        if st.button("Отмена", key="org_cancel_edit_group"):
            st.session_state["org_show_edit_group_form"] = False
            utils.safe_rerun()

    st.markdown("---")
    st.markdown("### Новое бронирование")
    sel_date = st.date_input("Дата бронирования", value=dt_date.today(), key="org_booking_date")
    if sel_date < dt_date.today():
        st.error("Нельзя бронировать прошедшие даты!")
        return
    slots = utils.list_timeslots()
    if not slots:
        st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
        return
    # Выбор времени начала и конца
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        start_time = st.selectbox("Время начала", slots, key="org_time_start")
    with col_time2:
        end_time = st.selectbox("Время конца", slots, index=len(slots)-1, key="org_time_end")
    # Получаем диапазон слотов
    try:
        start_idx = slots.index(start_time)
        end_idx = slots.index(end_time)
        if start_idx > end_idx:
            st.error("Время начала не может быть позже времени конца!")
            return
        times_to_book = slots[start_idx:end_idx+1]
    except Exception:
        times_to_book = []
    # Проверка: есть ли закрытые интервалы в диапазоне
    closed_times = [t for t in times_to_book if utils.is_slot_closed(sel_date, t)]
    if closed_times:
        st.error(f"Следующие интервалы закрыты для бронирования: {', '.join(closed_times)}")
        return
    busy_lanes, _ = utils.lane_trainer_status(sel_date, start_time)
    free_lanes = [l for l in range(1, 7) if l not in busy_lanes]
    st.write(f"Свободные дорожки: {', '.join(map(str, free_lanes)) if free_lanes else 'нет'}")
    all_pool = st.checkbox("Забронировать весь бассейн (все дорожки)", key="org_all_pool")
    if all_pool:
        lanes_to_book = free_lanes
    else:
        lanes_to_book = st.multiselect("Выберите дорожки для бронирования", free_lanes, key="org_lanes_multiselect")
    if st.button("Забронировать выбранные дорожки", key="org_booking_btn"):
        closed_times = [t for t in times_to_book if utils.is_slot_closed(sel_date, t)]
        if closed_times:
            st.error(f"Следующие интервалы закрыты для бронирования: {', '.join(closed_times)}")
            return
        if not lanes_to_book or not times_to_book:
            st.error("Выберите хотя бы одну дорожку и хотя бы одно время.")
            return
        ok = utils.add_org_booking_group(
            st.session_state["username"],
            sel_date,
            times_to_book,
            lanes_to_book,
        )
        if ok:
            st.success("Групповое бронирование подтверждено.")
            utils.safe_rerun()
        else:
            st.error("Не удалось забронировать (слоты заняты или ошибка данных). Обновите страницу.")
