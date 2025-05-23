import streamlit as st
from datetime import datetime, time as dt_time
import utils
import logging

logger = logging.getLogger(__name__)

TRAINERS = ["Тренер 1", "Тренер 2", "Тренер 3", "Тренер 4"]
WEEKDAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def admin_page():
    st.subheader("Панель администратора")
    tabs = st.tabs(["Слоты", "Расписание тренеров", "Пользователи"])

    # --- 1. Управление слотами ------------------------------------------------
    with tabs[0]:
        st.markdown("### Управление тайм-слотами")
        current = utils.list_timeslots()
        st.write("Текущие интервалы:", ", ".join(current) if current else "—")

        with st.form("slot_form", clear_on_submit=True):
            new_time = st.time_input("Новый интервал (чч:мм)", value=dt_time(9, 0))
            add = st.form_submit_button("Добавить интервал")
            if add:
                if utils.add_timeslot(new_time):
                    st.success(f"Добавлен {new_time.strftime('%H:%M')}")
                    logger.info(f"Admin added timeslot {new_time}")
                else:
                    st.warning("Такой интервал уже есть.")
        if current:
            with st.form("remove_form", clear_on_submit=True):
                rem = st.selectbox("Удалить интервал", current)
                remove = st.form_submit_button("Удалить выбранный")
                if remove:
                    utils.remove_timeslot(rem)
                    st.success(f"Удалён {rem}")
                    logger.info(f"Admin removed timeslot {rem}")

    # --- 2. Расписание тренеров ------------------------------------------------
    with tabs[1]:
        st.markdown("### Расписание тренеров")
        trainer = st.selectbox("Выберите тренера", TRAINERS)
        slots = utils.list_timeslots()
        # Сбор существующего расписания
        existing = utils.get_trainer_schedule(trainer)
        # Организация по дням
        schedule: dict[int, list[str]] = {dow: [] for dow in range(7)}
        for rec in existing:
            schedule[rec.day_of_week].append(rec.time.strftime("%H:%M"))

        # Форма редактирования полного расписания
        with st.form("schedule_form"):
            new_schedule: list[tuple[int, dt_time]] = []
            for dow in range(7):
                with st.expander(WEEKDAYS[dow], expanded=False):
                    sel = st.multiselect(
                        "Время",
                        slots,
                        default=schedule[dow],
                        key=f"sch_{trainer}_{dow}"
                    )
                    for t_str in sel:
                        t_obj = datetime.strptime(t_str, "%H:%M").time()
                        new_schedule.append((dow, t_obj))
            save = st.form_submit_button("Сохранить расписание")
            if save:
                utils.update_trainer_schedule(trainer, new_schedule)
                st.success(f"Расписание для {trainer} обновлено.")
                logger.info(f"Admin updated schedule for {trainer}")

    # --- 3. Управление пользователями ------------------------------------------
    with tabs[2]:
        st.markdown("### Список пользователей")
        search = st.text_input("Поиск по логину", value="", key="user_search")
        users = utils.list_users(search)
        if users:
            # Отображаем простую таблицу
            data = [{"Логин": u.username, "Роль": u.role} for u in users]
            st.table(data)
            logger.info(f"Admin viewed user list, filter='{search}' (count={len(users)})")
        else:
            st.info("Пользователи не найдены.")
