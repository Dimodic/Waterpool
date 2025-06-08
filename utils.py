# utils.py
import streamlit as st
from datetime import datetime, time as dt_time
from passlib.hash import bcrypt

# Импортируем все ORM-модели и сессию из db.py, а не из несуществующего models.py
from db import (
    SessionLocal,
    User,
    Timeslot,
    Booking,
    Trainer,
    TrainerSchedule,
    OrgBookingGroup,
    ClosedSlot
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
    role: str = "user",
    org_name: str = None,
    is_confirmed: int = 0
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
            middle_name=org_name if role == "org" else middle_name,
            phone=phone,
            gender=gender,
            email=email,
            is_confirmed=is_confirmed
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
                "is_confirmed": u.is_confirmed,
            }
            for u in users
        ]

def confirm_user(user_id: int):
    with SessionLocal() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            user.is_confirmed = 1
            db.commit()

def remove_user(user_id: int):
    with SessionLocal() as db:
        db.query(User).filter_by(id=user_id).delete()
        db.commit()

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
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        db.query(Timeslot).filter_by(time=t).delete()
        db.commit()

# ------------------ Тренеры и их расписание ---------------------------------
def list_trainers(full=False):
    with SessionLocal() as db:
        if full:
            return [{
                'name': t.name,
                'short_fio': f"{t.last_name} {t.first_name[0]}.{t.middle_name[0] + '.' if t.middle_name else ''}",
                'age': t.age,
                'description': t.description
            } for t in db.query(Trainer).all()]
        # Для selectbox возвращаем полное ФИО
        return [t.name for t in db.query(Trainer).all()]

def add_trainer(name: str, first_name: str, last_name: str, middle_name: str, age: int, description: str) -> bool:
    with SessionLocal() as db:
        if db.query(Trainer).filter_by(name=name).first():
            return False
        db.add(Trainer(
            name=name,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            age=age,
            description=description
        ))
        db.commit()
        return True

def remove_trainer(name: str):
    with SessionLocal() as db:
        db.query(Trainer).filter_by(name=name).delete()
        db.commit()

def get_trainer_by_name(name: str):
    with SessionLocal() as db:
        t = db.query(Trainer).filter_by(name=name).first()
        if t:
            return {
                "first_name": t.first_name,
                "last_name": t.last_name,
                "middle_name": t.middle_name or "",
                "age": t.age,
                "description": t.description
            }
        return None

def list_trainer_schedule():
    """Возвращает список всех записей расписания."""
    with SessionLocal() as db:
        sch = db.query(TrainerSchedule).all()
        return [
            {
                "id": s.id,
                "trainer": s.trainer.name,
                "day_of_week": s.day_of_week,
                "time": s.timeslot.time.strftime("%H:%M"),
            }
            for s in sch
        ]

def add_trainer_schedule(trainer_name: str, day_of_week: int, time_str: str) -> bool:
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        trainer = db.query(Trainer).filter_by(name=trainer_name).first()
        timeslot = db.query(Timeslot).filter_by(time=t).first()
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
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        bks = db.query(Booking).filter_by(date=date, time=t).all()
        lanes = [bk.lane for bk in bks]
        trainers = [bk.trainer for bk in bks]
    return lanes, trainers

def get_scheduled_trainers(date, time_str):
    """Тренеры, которые по расписанию работают в этот день и время."""
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

def add_org_booking_group(username, date, times, lanes):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return False
        # times — список строк ('09:00', ...)
        group = OrgBookingGroup(
            user_id=user.id,
            date=date,
            time=datetime.strptime(times[0], "%H:%M").time(),
            lanes=','.join(str(l) for l in lanes),
            times=','.join(times)
        )
        db.add(group)
        db.commit()
        for time_str in times:
            t = datetime.strptime(time_str, "%H:%M").time()
            for lane in lanes:
                db.add(Booking(
                    user_id=user.id,
                    date=date,
                    time=t,
                    lane=lane,
                    trainer=f"org_lane_{lane}",
                    group_id=group.id
                ))
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

def list_org_booking_groups(username):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return []
        groups = db.query(OrgBookingGroup).filter_by(user_id=user.id).order_by(OrgBookingGroup.date.desc(), OrgBookingGroup.time.desc()).all()
        return [
            {
                "id": g.id,
                "date": g.date,
                "times": g.times or g.time.strftime("%H:%M"),
                "lanes": g.lanes,
            }
            for g in groups
        ]

def remove_org_booking_group(group_id):
    with SessionLocal() as db:
        db.query(OrgBookingGroup).filter_by(id=group_id).delete()
        db.query(Booking).filter_by(group_id=group_id).delete()
        db.commit()

def update_org_booking_group(group_id, date, time_str, lanes):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        group = db.query(OrgBookingGroup).filter_by(id=group_id).first()
        if not group:
            return False
        group.date = date
        group.time = t
        group.lanes = ','.join(str(l) for l in lanes)
        db.query(Booking).filter_by(group_id=group_id).delete()
        user_id = group.user_id
        for lane in lanes:
            db.add(Booking(
                user_id=user_id,
                date=date,
                time=t,
                lane=lane,
                trainer=f"org_lane_{lane}",
                group_id=group_id
            ))
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

def add_booking(username, date, time_str, lane, trainer, group_id=None):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user or (user.role != "org" and not user.is_confirmed):
            return False
        exists = db.query(Booking).filter_by(date=date, time=t, lane=lane).first()
        if exists:
            return False
        if trainer:
            exists_tr = db.query(Booking).filter_by(date=date, time=t, trainer=trainer).first()
            if exists_tr:
                return False
        db.add(Booking(
            user_id=user.id,
            date=date,
            time=t,
            lane=lane,
            trainer=trainer if trainer else "",
            group_id=group_id
        ))
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

def list_user_bookings(username: str):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return []
        bookings = db.query(Booking).filter_by(user_id=user.id).all()
        return [
            {
                "id": b.id,
                "date": b.date,
                "time": b.time.strftime("%H:%M"),
                "lane": b.lane,
                "trainer": b.trainer,
            }
            for b in bookings
        ]

def remove_booking(booking_id: int):
    with SessionLocal() as db:
        db.query(Booking).filter_by(id=booking_id).delete()
        db.commit()

def update_booking(booking_id: int, date, time_str, lane, trainer):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        booking = db.query(Booking).filter_by(id=booking_id).first()
        if booking:
            booking.date = date
            booking.time = t
            booking.lane = lane
            booking.trainer = trainer if trainer else ""
            db.commit()
            return True
        return False

def list_all_bookings_for_date(date):
    with SessionLocal() as db:
        bookings = db.query(Booking).filter_by(date=date).all()
        return [
            {
                "id": b.id,
                "user": b.user.username if b.user else "",
                "date": b.date,
                "time": b.time.strftime("%H:%M"),
                "lane": b.lane,
                "trainer": b.trainer,
            }
            for b in bookings
        ]

# ------------------ Закрытые слоты ------------------------------------------
def list_closed_slots(date):
    with SessionLocal() as db:
        slots = db.query(ClosedSlot).filter_by(date=date).order_by(ClosedSlot.time).all()
        return [
            {"id": s.id, "date": s.date, "time": s.time.strftime("%H:%M"), "comment": s.comment}
            for s in slots
        ]

def add_closed_slot(date, time_str, comment=None):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        if db.query(ClosedSlot).filter_by(date=date, time=t).first():
            return False
        db.add(ClosedSlot(date=date, time=t, comment=comment))
        db.commit()
        return True

def add_closed_slots_range(date, start_time_str, end_time_str, comment=None):
    timeslots = list_timeslots()
    try:
        start_idx = timeslots.index(start_time_str)
        end_idx = timeslots.index(end_time_str)
    except ValueError:
        return 0
    if start_idx > end_idx:
        return 0
    count = 0
    for t_str in timeslots[start_idx:end_idx+1]:
        if add_closed_slot(date, t_str, comment):
            count += 1
    return count

def remove_closed_slot(slot_id):
    with SessionLocal() as db:
        db.query(ClosedSlot).filter_by(id=slot_id).delete()
        db.commit()
        return True

def is_slot_closed(date, time_str):
    t = datetime.strptime(time_str, "%H:%M").time()
    with SessionLocal() as db:
        return db.query(ClosedSlot).filter_by(date=date, time=t).first() is not None
