import streamlit as st
import logging
from datetime import date as dt_date, datetime
import utils

logger = logging.getLogger(__name__)
TRAINERS = ["Тренер 1", "Тренер 2", "Тренер 3", "Тренер 4"]

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    sel_date = st.date_input("Дата бронирования", value=dt_date.today())
    weekday = sel_date.weekday()
    slots = utils.list_timeslots()
    if not slots:
        st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
        return
    sel_time = st.selectbox("Время", slots)

    # Проверяем занятость дорожек и тренеров
    busy_lanes, busy_trainers = utils.lane_trainer_status(sel_date, sel_time)
    free_lanes = [l for l in range(1, 7) if l not in busy_lanes]
    if not free_lanes:
        st.warning("На это время нет свободных дорожек.")
        return
    lane = st.selectbox("Дорожка", free_lanes)

    # Фильтрация тренеров по расписанию и занятости
    available_trainers = []
    for t in TRAINERS:
        sched = utils.get_trainer_schedule(t)
        works = any(rec.day_of_week == weekday and rec.time.strftime("%H:%M") == sel_time for rec in sched)
        if works and t not in busy_trainers:
            available_trainers.append(t)
    if not available_trainers:
        st.warning("На это время нет доступных тренеров.")
        return
    trainer = st.selectbox("Тренер", available_trainers)

    if st.button("Забронировать"):
        ok = utils.add_booking(
            st.session_state["username"], sel_date, sel_time, lane, trainer
        )
        if ok:
            st.success(f"Бронирование подтверждено: дорожка {lane}, {sel_time}, {trainer}.")
            logger.info(f"Booking confirmed: {st.session_state['username']} {sel_date} {sel_time} lane {lane} trainer {trainer}")
            utils.safe_rerun()
        else:
            st.error("Не удалось забронировать (слот уже занят).")