import streamlit as st
import utils
from datetime import date as dt_date

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    sel_date = st.date_input("Дата бронирования", value=dt_date.today())
    slots = utils.list_timeslots()
    if not slots:
        st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
        return
    sel_time = st.selectbox("Время", slots)

    # проверяем занятость
    busy_lanes, busy_trainers = utils.lane_trainer_status(sel_date, sel_time)

    free_lanes = [l for l in range(1, 7) if l not in busy_lanes]
    if not free_lanes:
        st.warning("На это время нет свободных дорожек.")
        return
    lane = st.selectbox("Дорожка", free_lanes)

    # доступные по расписанию и незанятые тренеры
    scheduled = utils.get_scheduled_trainers(sel_date, sel_time)
    free_trainers = [t for t in scheduled if t not in busy_trainers]
    if not free_trainers:
        st.warning("На это время нет доступных тренеров.")
        return
    trainer = st.selectbox("Тренер", free_trainers)

    if st.button("Забронировать"):
        ok = utils.add_booking(
            st.session_state["username"],
            sel_date,
            sel_time,
            lane,
            trainer,
        )
        if ok:
            st.success(f"Бронирование подтверждено: дорожка {lane}, {sel_time}, {trainer}.")
            utils.safe_rerun()
        else:
            st.error("Не удалось забронировать (слот уже занят). Обновите страницу.")
