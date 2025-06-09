# utils.py — адаптирован под новую схему
# -----------------------------------------------------------------------------
import streamlit as st
from datetime import datetime, time as dt_time
from passlib.hash import bcrypt

from db import (
    SessionLocal, User, Lane, Timeslot, Trainer, TrainerSchedule,
    Booking, OrgBookingGroup, ClosedSlot
)

# --------------------------------------------------------------------- helpers
def safe_rerun() -> None:
    """Аккуратная перезагрузка страницы в Streamlit."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# -------- внутренняя «лента» и «слот» ----------------------------------------
def _get_lane(db, lane_number: int) -> Lane:
    lane = db.query(Lane).filter_by(number=lane_number).first()
    if not lane:
        lane = Lane(number=lane_number, name=f"Дорожка {lane_number}")
        db.add(lane)
        db.flush()
    return lane


def _get_timeslot(db, time_str: str) -> Timeslot:
    t = datetime.strptime(time_str, "%H:%M").time()
    ts = db.query(Timeslot).filter_by(time=t).first()
    if not ts:
        ts = Timeslot(time=t)
        db.add(ts)
        db.flush()
    return ts


# --------------------------------------------------------------------- users
def add_user(
    username: str, password: str,
    first_name: str, last_name: str, middle_name: str,
    phone: str, gender: str, email: str,
    role: str = "user", org_name: str | None = None,
    is_confirmed: int = 0
) -> bool:
    with SessionLocal() as db:
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


def validate_user(username: str, password: str) -> str | None:
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if user and bcrypt.verify(password, user.pwd_hash):
            return user.role
    return None


def list_users():
    with SessionLocal() as db:
        users = db.query(User).all()
        return [{
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
        } for u in users]


def confirm_user(user_id: int):
    with SessionLocal() as db:
        if (u := db.query(User).filter_by(id=user_id).first()):
            u.is_confirmed = 1
            db.commit()


def remove_user(user_id: int):
    with SessionLocal() as db:
        db.query(User).filter_by(id=user_id).delete()
        db.commit()


# --------------------------------------------------------------------- lanes & timeslots
def list_lanes():
    with SessionLocal() as db:
        return sorted([l.number for l in db.query(Lane).all()])


def list_timeslots():
    with SessionLocal() as db:
        return sorted([t.time.strftime("%H:%M") for t in db.query(Timeslot).all()])


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


# --------------------------------------------------------------------- trainers (интерфейс прежний)
def list_trainers(full: bool = False):
    with SessionLocal() as db:
        query = db.query(Trainer).all()
        if full:
            return [{
                "name": t.name,
                "short_fio": f"{t.last_name} {t.first_name[0]}.{t.middle_name[0] + '.' if t.middle_name else ''}",
                "age": t.age,
                "description": t.description,
            } for t in query]
        return [t.name for t in query]


def add_trainer(name: str, first: str, last: str, middle: str,
                age: int, desc: str) -> bool:
    with SessionLocal() as db:
        if db.query(Trainer).filter_by(name=name).first():
            return False
        db.add(Trainer(
            name=name,
            first_name=first,
            last_name=last,
            middle_name=middle,
            age=age,
            description=desc
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
                "last_name":  t.last_name,
                "middle_name": t.middle_name or "",
                "age": t.age,
                "description": t.description,
            }
        return None


# --------------------------------------------------------------------- trainer schedule
def list_trainer_schedule():
    with SessionLocal() as db:
        sch = db.query(TrainerSchedule).all()
        return [{
            "id": s.id,
            "trainer": s.trainer.name,
            "day_of_week": s.day_of_week,
            "time": s.timeslot.time.strftime("%H:%M"),
        } for s in sch]


def add_trainer_schedule(trainer_name: str, dow: int, time_str: str) -> bool:
    with SessionLocal() as db:
        trainer = db.query(Trainer).filter_by(name=trainer_name).first()
        if not trainer:
            return False
        timeslot = _get_timeslot(db, time_str)
        if db.query(TrainerSchedule).filter_by(
            trainer_id=trainer.id, timeslot_id=timeslot.id, day_of_week=dow
        ).first():
            return False
        db.add(TrainerSchedule(
            trainer_id=trainer.id,
            timeslot_id=timeslot.id,
            day_of_week=dow
        ))
        db.commit()
        return True


def remove_trainer_schedule(schedule_id: int):
    with SessionLocal() as db:
        db.query(TrainerSchedule).filter_by(id=schedule_id).delete()
        db.commit()


# --------------------------------------------------------------------- bookings
def _booking_exists(db, date, timeslot_id, lane_id=None, trainer_id=None) -> bool:
    q = db.query(Booking).filter_by(date=date, timeslot_id=timeslot_id)
    if lane_id is not None:
        q = q.filter_by(lane_id=lane_id)
    if trainer_id is not None:
        q = q.filter_by(trainer_id=trainer_id)
    return q.first() is not None


def add_booking(username, date, time_str, lane_number, trainer_name=None, group_id=None):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user or (user.role != "org" and not user.is_confirmed):
            return False

        lane      = _get_lane(db, lane_number)
        timeslot  = _get_timeslot(db, time_str)
        trainer   = db.query(Trainer).filter_by(name=trainer_name).first() if trainer_name else None

        if _booking_exists(db, date, timeslot.id, lane_id=lane.id):
            return False
        if trainer and _booking_exists(db, date, timeslot.id, trainer_id=trainer.id):
            return False

        db.add(Booking(
            user_id=user.id,
            date=date,
            timeslot_id=timeslot.id,
            lane_id=lane.id,
            trainer_id=trainer.id if trainer else None,
            group_id=group_id
        ))
        try:
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False


def list_user_bookings(username):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return []
        bookings = db.query(Booking).filter_by(user_id=user.id).all()
        return [{
            "id": b.id,
            "date": b.date,
            "time": b.timeslot.time.strftime("%H:%M"),
            "lane": b.lane.number,
            "trainer": b.trainer.name if b.trainer else "—",
        } for b in bookings]


def remove_booking(booking_id: int):
    with SessionLocal() as db:
        db.query(Booking).filter_by(id=booking_id).delete()
        db.commit()


def list_all_bookings_for_date(date):
    with SessionLocal() as db:
        bookings = db.query(Booking).filter_by(date=date).all()
        return [{
            "id": b.id,
            "user": b.user.username,
            "date": b.date,
            "time": b.timeslot.time.strftime("%H:%M"),
            "lane": b.lane.number,
            "trainer": b.trainer.name if b.trainer else "—",
        } for b in bookings]


def lane_trainer_status(date, time_str):
    with SessionLocal() as db:
        ts  = _get_timeslot(db, time_str)
        bks = db.query(Booking).filter_by(date=date, timeslot_id=ts.id).all()
        lanes     = [bk.lane.number for bk in bks]
        trainers  = [bk.trainer.name for bk in bks if bk.trainer]
    return lanes, trainers


def get_scheduled_trainers(date, time_str):
    dow = date.weekday()
    with SessionLocal() as db:
        ts = _get_timeslot(db, time_str)
        sch = db.query(TrainerSchedule).filter_by(
            day_of_week=dow, timeslot_id=ts.id
        ).all()
        return [s.trainer.name for s in sch]


# --------------------------- групповые бронирования ---------------------------
def add_org_booking_group(username, date, times, lanes):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if not user:
            return False

        # Базовый слот (для колонки timeslot_id в группе)
        base_ts = _get_timeslot(db, times[0])

        group = OrgBookingGroup(
            user_id=user.id,
            date=date,
            timeslot_id=base_ts.id,
            lanes=",".join(str(l) for l in lanes),
            times=",".join(times)
        )
        db.add(group)
        db.flush()  # получаем group.id

        try:
            for t_str in times:
                ts = _get_timeslot(db, t_str)
                for lane_num in lanes:
                    lane = _get_lane(db, lane_num)
                    db.add(Booking(
                        user_id=user.id,
                        date=date,
                        timeslot_id=ts.id,
                        lane_id=lane.id,
                        trainer_id=None,
                        group_id=group.id
                    ))
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
        groups = db.query(OrgBookingGroup).filter_by(user_id=user.id).all()
        return [{
            "id": g.id,
            "date": g.date,
            "times": g.times,
            "lanes": g.lanes,
        } for g in groups]


def remove_org_booking_group(group_id: int):
    with SessionLocal() as db:
        db.query(Booking).filter_by(group_id=group_id).delete()
        db.query(OrgBookingGroup).filter_by(id=group_id).delete()
        db.commit()


# --------------------------------------------------------------------- closed slots
def list_closed_slots(date):
    with SessionLocal() as db:
        slots = db.query(ClosedSlot).filter_by(date=date).order_by(ClosedSlot.timeslot_id).all()
        return [{
            "id": s.id,
            "date": s.date,
            "time": s.timeslot.time.strftime("%H:%M"),
            "comment": s.comment or "",
        } for s in slots]


def add_closed_slot(date, time_str, comment=None) -> bool:
    with SessionLocal() as db:
        ts = _get_timeslot(db, time_str)
        if db.query(ClosedSlot).filter_by(date=date, timeslot_id=ts.id).first():
            return False
        db.add(ClosedSlot(date=date, timeslot_id=ts.id, comment=comment))
        db.commit()
        return True


def remove_closed_slot(slot_id: int):
    with SessionLocal() as db:
        db.query(ClosedSlot).filter_by(id=slot_id).delete()
        db.commit()


def is_slot_closed(date, time_str) -> bool:
    with SessionLocal() as db:
        ts = _get_timeslot(db, time_str)
        return db.query(ClosedSlot).filter_by(date=date, timeslot_id=ts.id).first() is not None
