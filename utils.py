# utils.py — бизнес-логика и доступ к БД

import logging
from datetime import datetime, time as dt_time
from typing import List
from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError
import streamlit as st
from passlib.hash import bcrypt

from db import SessionLocal, User, Timeslot, Booking, TrainerSchedule

logger = logging.getLogger(__name__)

# ----------------- Streamlit rerun-safe -------------------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ----------------- Аутентификация -------------------------------------------
def add_user(username: str, password: str, role: str = "user") -> bool:
    with SessionLocal.begin() as db:
        if db.scalars(select(User).filter_by(username=username)).first():
            logger.warning(f"Регистрация не удалась: пользователь '{username}' уже существует")
            return False
        db.add(User(username=username, pwd_hash=bcrypt.hash(password), role=role))
        logger.info(f"Пользователь '{username}' зарегистрирован")
        return True

def validate_user(username: str, password: str):
    with SessionLocal() as db:
        user = db.scalars(select(User).filter_by(username=username)).first()
        if user and bcrypt.verify(password, user.pwd_hash):
            logger.info(f"Пользователь '{username}' вошёл в систему")
            return user.role
    logger.warning(f"Ошибка входа для пользователя '{username}'")
    return None

# ----------------- Тайм-слоты -----------------------------------------------
def list_timeslots() -> List[str]:
    with SessionLocal() as db:
        return sorted([ts.time.strftime("%H:%M") for ts in db.scalars(select(Timeslot)).all()])

def add_timeslot(time_obj: dt_time) -> bool:
    with SessionLocal.begin() as db:
        if db.scalars(select(Timeslot).filter_by(time=time_obj)).first():
            return False
        db.add(Timeslot(time=time_obj))
        logger.info(f"Добавлен новый тайм-слот: {time_obj}")
        return True

def remove_timeslot(time_str: str):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal.begin() as db:
        db.execute(
            select(Timeslot).filter_by(time=t).delete()
        )
        logger.info(f"Удалён тайм-слот: {time_str}")

# ----------------- Бронирования ---------------------------------------------
def lane_trainer_status(date, time_str):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        bookings = db.scalars(
            select(Booking).filter_by(date=date, time=t)
        ).all()
        return [b.lane for b in bookings], [b.trainer for b in bookings]

def add_booking(username, date, time_str, lane, trainer):
    t = datetime.strptime(time_str, "%H:%M").time()
    try:
        with SessionLocal.begin() as db:
            user = db.scalars(select(User).filter_by(username=username)).first()
            db.add(Booking(
                user_id=user.id,
                date=date,
                time=t,
                lane=lane,
                trainer=trainer,
            ))
            logger.info(f"Новое бронирование: пользователь={username}, дата={date}, время={time_str}, дорожка={lane}, тренер={trainer}")
            return True
    except IntegrityError as e:
        logger.error(f"Конфликт при бронировании: {e}")
        return False

# ----------------- Расписание тренеров --------------------------------------
def get_trainer_schedule(trainer_name: str) -> List[TrainerSchedule]:
    with SessionLocal() as db:
        return db.scalars(
            select(TrainerSchedule).filter_by(trainer_name=trainer_name)
        ).all()

def update_trainer_schedule(trainer_name: str, schedule: List[tuple[int, dt_time]]):
    with SessionLocal.begin() as db:
        db.execute(
            TrainerSchedule.__table__.delete().where(TrainerSchedule.trainer_name == trainer_name)
        )
        for day, t in schedule:
            db.add(TrainerSchedule(trainer_name=trainer_name, day_of_week=day, time=t))
        logger.info(f"Обновлено расписание тренера: {trainer_name}")

# ----------------- Пользователи ---------------------------------------------
def list_users(search: str = "") -> List[User]:
    with SessionLocal() as db:
        stmt = select(User)
        if search:
            stmt = stmt.filter(User.username.ilike(f"%{search}%"))
        return db.scalars(stmt.order_by(User.username)).all()
