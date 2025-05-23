import streamlit as st
from datetime import time as dt_time
from passlib.hash import bcrypt
from db import SessionLocal, User, Timeslot, Booking

# --------------------- SESSION-HELPER для Streamlit ---------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ------------------ Аутентификация / пользователи ----------------------------
def add_user(username: str, password: str, role: str = "user") -> bool:
    with SessionLocal() as db:
        if db.query(User).filter_by(username=username).first():
            return False
        db.add(User(username=username, pwd_hash=bcrypt.hash(password), role=role))
        db.commit()
        return True

def validate_user(username: str, password: str):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if user and bcrypt.verify(password, user.pwd_hash):
            return user.role
    return None

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

def add_booking(username, date, time_str, lane, trainer):
    from datetime import datetime
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        db.add(
            Booking(
                user_id=user.id,
                date=date,
                time=t,
                lane=lane,
                trainer=trainer,
            )
        )
        try:
            db.commit()
            return True
        except Exception as e:          # нарушили уникальный ключ
            db.rollback()
            return False
