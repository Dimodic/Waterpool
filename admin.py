import streamlit as st
import utils
from datetime import datetime, time as dt_time

def admin_page():
    st.subheader("Панель администратора — управление слотами")

    current = utils.list_timeslots()
    st.write("Текущие интервалы:", ", ".join(current) if current else "—")

    # --- добавить слот --------------------------------------------------------
    new_time = st.time_input("Новый интервал (чч:мм)", value=dt_time(9, 0))
    if st.button("Добавить интервал"):
        if utils.add_timeslot(new_time):
            st.success(f"Добавлен {new_time.strftime('%H:%M')}")
            utils.safe_rerun()
        else:
            st.warning("Такой интервал уже есть.")

    # --- удалить слот ---------------------------------------------------------
    if current:
        rem = st.selectbox("Удалить интервал", current)
        if st.button("Удалить выбранный"):
            utils.remove_timeslot(rem)
            st.success(f"Удалён {rem}")
            utils.safe_rerun()

    st.info("Здесь можно добавить и другие функции администрирования.")
