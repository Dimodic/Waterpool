# booking.py
import streamlit as st
import utils
from datetime import datetime, timedelta, date as dt_date

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    # Если роль — юридическое лицо, перекладываем на свой сценарий
    if st.session_state.get("role") == "org":
        booking_page_org()
        return

    # --- ШАГ 1: Сначала показываем «Недельный календарь» для наглядности ---
    # (При этом и неподтверждённый пользователь увидит календарь, но «новая бронь» будет недоступна.)
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

    timeslots = utils.list_timeslots()  # базовые интервалы

    # Собираем занятые дорожки (бронирования) за каждую дату/время
    busy_map = {}
    for single_date in week_dates:
        for t in timeslots:
            busy_lanes, _ = utils.lane_trainer_status(single_date, t)
            busy_map[(single_date, t)] = busy_lanes

    # Строим стилизованную HTML-таблицу «дорожек»
    table_html = """
    <style>
        table.week-calendar { border-collapse: collapse; width: 100%; }
        table.week-calendar th, table.week-calendar td {
            border: 1px solid #999;
            padding: 4px;
            vertical-align: middle;
            text-align: center;
        }
        th.day-header { background-color: #f0f0f0; }
        td.time-cell { background-color: #fafafa; font-weight: bold; }
        .lane { display: inline-block; width: 14px; height: 14px; margin: 1px; border: 1px solid #555; border-radius: 3px; }
        .free { background-color: #90ee90; }
        .busy { background-color: #ff7f7f; }
    </style>
    <table class="week-calendar">
      <tr>
        <th class="day-header">Время</th>"""
    for label in day_labels:
        table_html += f"<th class='day-header'>{label}</th>"
    table_html += "</tr>"

    for t in timeslots:
        table_html += f"<tr><td class='time-cell'>{t}</td>"
        for single_date in week_dates:
            lanes_busy = busy_map.get((single_date, t), [])
            cell_content = ""
            # Рисуем 6 «квадратиков» — дорожек 1..6
            for lane_no in range(1, 7):
                if lane_no in lanes_busy:
                    cell_content += "<span class='lane busy' title='Дорожка {} занята'></span>".format(lane_no)
                else:
                    cell_content += "<span class='lane free' title='Дорожка {} свободна'></span>".format(lane_no)
            table_html += f"<td>{cell_content}</td>"
        table_html += "</tr>"

    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.markdown("---")
    # --- ШАГ 2: Блок «Мои бронирования» (оставляем без изменений) ---
    st.markdown("### Мои бронирования")
    my_bookings = utils.list_user_bookings(st.session_state["username"])
    if my_bookings:
        import pandas as pd
        df = pd.DataFrame(my_bookings)
        for _, row in df.iterrows():
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

    # --- Форма редактирования (если нужно) — без изменений ---
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
    # --- ШАГ 3: Блок «Новое бронирование» — показываем только для подтверждённых ---
    if not st.session_state.get("is_confirmed", False):
        st.warning("Ваша регистрация ожидает подтверждения администрацией. Пожалуйста, принесите все необходимые бумаги в бассейн.")
        return

    # Если подтвердили — показываем сам форму для новой брони
    sel_date = st.date_input("Дата бронирования", value=dt_date.today(), key="new_booking_date")
    if sel_date < dt_date.today():
        st.error("Нельзя бронировать прошедшие даты!")
        return

    slots = utils.list_timeslots()
    if not slots:
        st.warning("Нет доступных временных интервалов. Обратитесь к администратору.")
        return

    sel_time = st.selectbox("Время", slots, key="new_booking_time")

    busy_lanes, busy_trainers = utils.lane_trainer_status(sel_date, sel_time)
    if utils.is_slot_closed(sel_date, sel_time):
        st.error("Этот слот закрыт для бронирования администратором.")
        return

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
