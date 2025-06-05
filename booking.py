# booking.py
import streamlit as st
import utils
from datetime import datetime, timedelta, date as dt_date
import pandas as pd

@st.cache_data(ttl=300)
def get_timeslots():
    return utils.list_timeslots()

def get_week_dates(week_start):
    return [week_start + timedelta(days=i) for i in range(7)]

def booking_page():
    st.subheader("Бронирование дорожек и тренеров")

    if st.session_state.get("role") == "org":
        booking_page_org()
        return

    # --- Недельная таблица + Мои бронирования — в двух колонках ---
    cols = st.columns([2.7, 2])
    with cols[0]:
        # Таблица бронирования (оставляем весь html-код таблицы как раньше)
        # ... (код недельной таблицы из вашего предыдущего варианта)
        # Ниже — просто скопируйте из вашего предыдущего кода формирование html для недельной таблицы
        # ...
        week_start = st.session_state.get("week_start_user")
        if week_start is None:
            today = dt_date.today()
            week_start = today - timedelta(days=today.weekday())
            st.session_state["week_start_user"] = week_start

        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("<< Предыдущая неделя", key="prev_week_user"):
                st.session_state["week_start_user"] -= timedelta(days=7)
                utils.safe_rerun()
        with col2:
            if st.button("Следующая неделя >>", key="next_week_user"):
                st.session_state["week_start_user"] += timedelta(days=7)
                utils.safe_rerun()
        with col3:
            picked = st.date_input(
                label="Выберите любую дату недели",
                value=st.session_state["week_start_user"],
                key="pick_date_for_week_user"
            )
            if picked != st.session_state["week_start_user"]:
                st.session_state["week_start_user"] = picked - timedelta(days=picked.weekday())
                utils.safe_rerun()

        week_start = st.session_state["week_start_user"]
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        timeslots = get_timeslots()
        day_labels = [
            d.strftime("%d.%m") + " " + ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][d.weekday()]
            for d in week_dates
        ]
        my_bookings = utils.list_user_bookings(st.session_state["username"])
        my_slots = set((b["date"], b["time"]) for b in my_bookings)
        busy_slots = set()
        for d in week_dates:
            all_b = utils.list_all_bookings_for_date(d)
            for b in all_b:
                busy_slots.add((b["date"], b["time"]))
        closed_slots = set()
        for d in week_dates:
            for item in utils.list_closed_slots(d):
                closed_slots.add((item["date"], item["time"]))
        cell_height = 32
        html = "<style>.user-table td{height:%dpx;min-width:68px;text-align:center;font-size:12px;}</style>" % cell_height
        html += "<table class='user-table' style='width:100%%; border-collapse:collapse;'><tr><th>Время</th>"
        for label in day_labels:
            html += f"<th>{label}</th>"
        html += "</tr>"
        for t in timeslots:
            html += f"<tr><td>{t}</td>"
            for d in week_dates:
                key = (d, t)
                if key in my_slots:
                    color = "#1569c7"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};border-radius:2px;'></div><div style='font-size:11px;'>Ваша бронь</div>"
                elif key in closed_slots:
                    color = "#b7b7b7"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};opacity:0.7;border-radius:2px;'></div><div style='font-size:11px;'>Недоступно</div>"
                elif key in busy_slots:
                    color = "#FF7F7F"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};border-radius:2px;'></div><div style='font-size:11px;'>Занято</div>"
                else:
                    bar = ""
                html += f"<td style='padding:0;border:1px solid #e0e0e0;'>{bar}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

    with cols[1]:
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
                        st.success("Бронирование удалено")
                        utils.safe_rerun()
                    if st.button("Изменить", key=f"edit_{row['id']}"):
                        st.session_state["edit_booking_id"] = row["id"]
                        st.session_state["edit_booking_data"] = row
                        st.session_state["show_edit_form"] = True
        else:
            st.info("У вас нет бронирований.")

        # Форма редактирования
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
                    st.success("Бронирование обновлено")
                    st.session_state["show_edit_form"] = False
                    utils.safe_rerun()
                else:
                    st.error("Ошибка при обновлении бронирования")
            if st.button("Отмена", key="cancel_edit_booking"):
                st.session_state["show_edit_form"] = False
                utils.safe_rerun()

        # Форма нового бронирования
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
                st.success(f"Бронирование подтверждено: дорожка {lane}, {sel_time}, {trainer}.")
                utils.safe_rerun()
            else:
                st.error("Не удалось забронировать (слот уже занят или вы не подтверждены). Обновите страницу.")

def booking_page_org():
    st.subheader("Бронирование для юридических лиц (групповое)")

    cols = st.columns([2.7, 2])
    with cols[0]:
        # -- тут весь ваш код недельной таблицы как раньше (html-таблица с расписанием) --
        # ... (весь предыдущий код построения таблицы)

        if "week_start_org" not in st.session_state:
            today = dt_date.today()
            st.session_state.week_start_org = today - timedelta(days=today.weekday())

        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("<< Предыдущая неделя", key="prev_week_org"):
                st.session_state.week_start_org -= timedelta(days=7)
                utils.safe_rerun()
        with col2:
            if st.button("Следующая неделя >>", key="next_week_org"):
                st.session_state.week_start_org += timedelta(days=7)
                utils.safe_rerun()
        with col3:
            picked = st.date_input(
                label="Выберите любую дату недели",
                value=st.session_state["week_start_org"],
                key="pick_date_for_week_org"
            )
            if picked != st.session_state["week_start_org"]:
                st.session_state["week_start_org"] = picked - timedelta(days=picked.weekday())
                utils.safe_rerun()

        week_start = st.session_state["week_start_org"]
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        timeslots = get_timeslots()
        day_labels = [
            d.strftime("%d.%m") + " " + ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][d.weekday()]
            for d in week_dates
        ]

        groups = utils.list_org_booking_groups(st.session_state["username"])
        my_slots = set()
        group_lookup = dict()
        for g in groups:
            times = (g["times"].split(",") if g["times"] else [g["times"]])
            for t in times:
                my_slots.add((g["date"], t))
                group_lookup[(g["date"], t)] = g

        busy_slots = set()
        for d in week_dates:
            all_b = utils.list_all_bookings_for_date(d)
            for b in all_b:
                busy_slots.add((b["date"], b["time"]))
        closed_slots = set()
        for d in week_dates:
            for item in utils.list_closed_slots(d):
                closed_slots.add((item["date"], item["time"]))
        cell_height = 32
        html = "<style>.org-table td{height:%dpx;min-width:68px;text-align:center;font-size:12px;}</style>" % cell_height
        html += "<table class='org-table' style='width:100%%; border-collapse:collapse;'><tr><th>Время</th>"
        for label in day_labels:
            html += f"<th>{label}</th>"
        html += "</tr>"
        for t in timeslots:
            html += f"<tr><td>{t}</td>"
            for d in week_dates:
                key = (d, t)
                if key in my_slots:
                    color = "#1569c7"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};border-radius:2px;'></div><div style='font-size:11px;'>Ваша бронь</div>"
                elif key in closed_slots:
                    color = "#b7b7b7"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};opacity:0.7;border-radius:2px;'></div><div style='font-size:11px;'>Недоступно</div>"
                elif key in busy_slots:
                    color = "#FF7F7F"
                    bar = f"<div style='width:70%;height:8px;margin:auto;background:{color};border-radius:2px;'></div><div style='font-size:11px;'>Занято</div>"
                else:
                    bar = ""
                html += f"<td style='padding:0;border:1px solid #e0e0e0;'>{bar}</td>"
            html += "</tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)

    with cols[1]:
        st.markdown("### Мои групповые бронирования")
        groups = utils.list_org_booking_groups(st.session_state["username"])
        if groups:
            for g in groups:
                c1, c2, c3, c4, c5 = st.columns([2,2,2,3,2])
                with c1:
                    st.write(g["date"])
                with c2:
                    st.write(g["times"])
                with c3:
                    st.write("Все дорожки" if g["lanes"]=="1,2,3,4,5,6" else g["lanes"])
                with c4:
                    if st.button("Удалить", key=f"org_del_{g['id']}"):
                        utils.remove_org_booking_group(g["id"])
                        st.success("Бронирование удалено")
                        utils.safe_rerun()
                with c5:
                    if st.button("Изменить", key=f"org_edit_{g['id']}"):
                        st.session_state["org_edit_group_id"] = g["id"]
                        st.session_state["org_edit_group_data"] = g
                        st.session_state["show_org_edit_form"] = True
        else:
            st.info("У вашей организации нет активных бронирований.")

    if st.session_state.get("show_org_edit_form"):
        g = st.session_state["org_edit_group_data"]
        st.markdown("#### Изменить групповое бронирование")
        new_date = st.date_input("Дата", value=g["date"], key="org_edit_date")
        slots = get_timeslots()
        group_times = g["times"].split(",") if g["times"] else [g["times"]]
        start_time = st.selectbox("Время начала", slots, index=slots.index(group_times[0]))
        end_time = st.selectbox("Время конца", slots, index=slots.index(group_times[-1]))
        available_lanes = [1,2,3,4,5,6]
        default_lanes = [int(l) for l in g["lanes"].split(",")]
        sel_lanes = st.multiselect("Дорожки", available_lanes, default=default_lanes)
        if st.button("Сохранить изменения", key="org_save_edit"):
            start_idx = slots.index(start_time)
            end_idx = slots.index(end_time)
            if start_idx > end_idx:
                st.error("Время начала не может быть позже конца!")
                return
            time_range = slots[start_idx:end_idx+1]
            ok = utils.update_org_booking_group(
                g["id"], new_date, start_time, sel_lanes
            )
            if ok:
                st.success("Групповое бронирование изменено")
                st.session_state["show_org_edit_form"] = False
                utils.safe_rerun()
            else:
                st.error("Ошибка при обновлении")
        if st.button("Отмена", key="org_cancel_edit"):
            st.session_state["show_org_edit_form"] = False
            utils.safe_rerun()

    st.markdown("---")
    st.markdown("#### Новое групповое бронирование")
    sel_date = st.date_input("Дата", value=dt_date.today(), key="org_new_date")
    slots = get_timeslots()
    col1, col2 = st.columns(2)
    with col1:
        start_time = st.selectbox("Время начала", slots, key="org_new_time_start")
    with col2:
        end_time = st.selectbox("Время конца", slots, index=len(slots)-1, key="org_new_time_end")
    available_lanes = [1,2,3,4,5,6]
    all_lanes = st.checkbox("Все дорожки", key="org_new_all_lanes")
    if all_lanes:
        sel_lanes = available_lanes
    else:
        sel_lanes = st.multiselect("Дорожки", available_lanes, default=[1], key="org_new_lanes")
    if st.button("Забронировать", key="org_new_book_btn"):
        start_idx = slots.index(start_time)
        end_idx = slots.index(end_time)
        if start_idx > end_idx:
            st.error("Время начала не может быть позже конца!")
            return
        time_range = slots[start_idx:end_idx+1]
        ok = utils.add_org_booking_group(
            st.session_state["username"],
            sel_date,
            time_range,
            sel_lanes
        )
        if ok:
            st.success("Групповое бронирование подтверждено.")
            utils.safe_rerun()
        else:
            st.error("Не удалось создать бронирование (возможно, время/дорожка уже заняты).")
