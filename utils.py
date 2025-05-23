import streamlit as st
from datetime import time as dt_time
from passlib.hash import bcrypt

from db import (
    SessionLocal, User, Timeslot, Booking,
    Trainer, TrainerSchedule
)

# --------------------- Streamlit helper --------------------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ------------------ Аутентификация / пользователи ----------------------------
def add_user(
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    middle_name: str,
    phone: str,
    gender: str,
    email: str,
    role: str = "user"
) -> bool:
    with SessionLocal() as db:
        # Проверяем уникальность по username и email
        if db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first():
            return False
        user = User(
            username=username,
            pwd_hash=bcrypt.hash(password),
            role=role,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            phone=phone,
            gender=gender,
            email=email
        )
        db.add(user)
        db.commit()
        return True

def validate_user(username: str, password: str):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if user and bcrypt.verify(password, user.pwd_hash):
            return user.role
    return None

def list_users():
    """Возвращает список всех пользователей для администратора."""
    with SessionLocal() as db:
        users = db.query(User).all()
        return [
            {
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "middle_name": u.middle_name or "",
                "phone": u.phone or "",
                "gender": u.gender or "",
                "email": u.email,
            }
            for u in users
        ]

# ------------------ Тайм-слоты -----------------------------------------------
def list_timeslots():
    with SessionLocal() as db:
        return sorted([ts.time.strftime("%H:%M") for ts in db.query(Timeslot).all()])

def add_timeslot(time_obj: dt_time) -> bool:
    with SessionLocal() as db:
        if db.query(Timeslot).filter_by(time=time_obj).first():
            return False
        db.add(Timeslot(time=time_obj))
        db.commit()
        return True

def remove_timeslot(time_str: str):
    from datetime import datetime
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        db.query(Timeslot).filter_by(time=t).delete()
        db.commit()

# ------------------ Тренеры и их расписание ---------------------------------
def list_trainers():
    with SessionLocal() as db:
        return [t.name for t in db.query(Trainer).all()]

def add_trainer(name: str) -> bool:
    with SessionLocal() as db:
        if db.query(Trainer).filter_by(name=name).first():
            return False
        db.add(Trainer(name=name))
        db.commit()
        return True

def remove_trainer(name: str):
    with SessionLocal() as db:
        db.query(Trainer).filter_by(name=name).delete()
        db.commit()

def list_trainer_schedule():
    """Возвращает список всех записей расписания."""
    with SessionLocal() as db:
        sch = db.query(TrainerSchedule).all()
        return [
            {
                "id":     s.id,
                "trainer":   s.trainer.name,
                "day_of_week": s.day_of_week,
                "time":    s.timeslot.time.strftime("%H:%M"),
            }
            for s in sch
        ]

def add_trainer_schedule(trainer_name: str, day_of_week: int, time_str: str) -> bool:
    from datetime import datetime
    with SessionLocal() as db:
        trainer = db.query(Trainer).filter_by(name=trainer_name).first()
        t_time = datetime.strptime(time_str, "%H:%M").time()
        timeslot = db.query(Timeslot).filter_by(time=t_time).first()
        if not trainer or not timeslot:
            return False
        if db.query(TrainerSchedule).filter_by(
            trainer_id=trainer.id,
            timeslot_id=timeslot.id,
            day_of_week=day_of_week
        ).first():
            return False
        db.add(TrainerSchedule(
            trainer_id=trainer.id,
            timeslot_id=timeslot.id,
            day_of_week=day_of_week
        ))
        db.commit()
        return True

def remove_trainer_schedule(schedule_id: int):
    with SessionLocal() as db:
        db.query(TrainerSchedule).filter_by(id=schedule_id).delete()
        db.commit()

# ------------------ Бронирования ---------------------------------------------
def lane_trainer_status(date, time_str):
    """Вернуть занятые дорожки и тренеров на слот."""
    from datetime import datetime
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        bks = db.query(Booking).filter_by(date=date, time=t).all()
        lanes = [bk.lane for bk in bks]
        trainers = [bk.trainer for bk in bks]
    return lanes, trainers

def get_scheduled_trainers(date, time_str):
    """Тренеры, которые по расписанию работают в этот день и время."""
    from datetime import datetime
    t = datetime.strptime(time_str, "%H:%M").time()
    dow = date.weekday()  # 0=Mon … 6=Sun
    with SessionLocal() as db:
        ts = db.query(Timeslot).filter_by(time=t).first()
        if not ts:
            return []
        sch = db.query(TrainerSchedule).filter_by(
            day_of_week=dow,
            timeslot_id=ts.id
        ).all()
        return [s.trainer.name for s in sch]

def add_booking(username, date, time_str, lane, trainer):
    from datetime import datetime
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        db.add(Booking(
            user_id=user.id,
            date=date,
            time=t,
            lane=lane,
            trainer=trainer,
        ))
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
