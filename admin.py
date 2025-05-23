import streamlit as st
import pandas as pd
import utils
from datetime import time as dt_time

def admin_page():
    st.sidebar.title("Администрирование")
    section = st.sidebar.radio("Раздел", [
        "Слоты",
        "Тренеры",
        "Расписание тренеров",
        "Пользователи"
    ])

    if section == "Слоты":
        manage_timeslots()
    elif section == "Тренеры":
        manage_trainers()
    elif section == "Расписание тренеров":
        manage_trainer_schedule()
    elif section == "Пользователи":
        manage_users()

def manage_timeslots():
    st.subheader("Управление слотами")
    current = utils.list_timeslots()
    st.write("Текущие интервалы:", ", ".join(current) if current else "—")

    new_time = st.time_input("Новый интервал (чч:мм)", value=dt_time(9, 0), key="new_timeslot")
    if st.button("Добавить слот"):
        if utils.add_timeslot(new_time):
            st.success(f"Добавлен {new_time.strftime('%H:%M')}")
            utils.safe_rerun()
        else:
            st.warning("Такой интервал уже есть.")

    if current:
        rem = st.selectbox("Удалить интервал", current, key="rem_timeslot")
        if st.button("Удалить слот"):
            utils.remove_timeslot(rem)
            st.success(f"Удалён {rem}")
            utils.safe_rerun()

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
    schedules = utils.list_trainer_schedule()
    if schedules:
        df_sch = pd.DataFrame(schedules)
        # Преобразуем день недели в текст для наглядности
        dow_map = {0:"Пн",1:"Вт",2:"Ср",3:"Чт",4:"Пт",5:"Сб",6:"Вс"}
        df_sch["day"] = df_sch["day_of_week"].map(dow_map)
        st.dataframe(df_sch[["id","trainer","day","time"]])

    trainers  = utils.list_trainers()
    trainer   = st.selectbox("Тренер", trainers, key="sch_trainer")
    day_names = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
    day       = st.selectbox("День недели", day_names, key="sch_day")
    timeslots = utils.list_timeslots()
    time_sel  = st.selectbox("Время", timeslots, key="sch_time")

    dow_map = {name: idx for idx, name in enumerate(day_names)}
    if st.button("Добавить в расписание"):
        if utils.add_trainer_schedule(trainer, dow_map[day], time_sel):
            st.success("Запись добавлена в расписание")
            utils.safe_rerun()
        else:
            st.warning("Такая запись уже существует или неверные данные.")

    if schedules:
        opts = [
            f"{s['id']}: {s['trainer']}, {day_names[s['day_of_week']]} {s['time']}"
            for s in schedules
        ]
        sel = st.selectbox("Удалить запись", opts, key="del_sched")
        if st.button("Удалить из расписания"):
            sched_id = int(sel.split(":")[0])
            utils.remove_trainer_schedule(sched_id)
            st.success("Запись удалена")
            utils.safe_rerun()

def manage_users():
    st.subheader("Список пользователей")
    users = utils.list_users()
    df = pd.DataFrame(users)
    search = st.text_input("Поиск", key="user_search")
    if search:
        mask = df.apply(lambda row: row.astype(str)
                        .str.contains(search, case=False).any(), axis=1)
        df = df[mask]
    st.dataframe(df)
