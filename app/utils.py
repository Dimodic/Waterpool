# utils.py — адаптирован под новую схему
import streamlit as st
from datetime import datetime, time as dt_time
from passlib.hash import bcrypt

from app.db import (
    SessionLocal, User, Lane, Timeslot, Trainer, TrainerSchedule,
    Booking, OrgBookingGroup, ClosedSlot
)

def with_session(func):
    def wrapper(*args, **kwargs):
        with SessionLocal() as db:
            return func(db, *args, **kwargs)
    return wrapper

#  helpers
def safe_rerun() -> None:
    getattr(st, "rerun", st.experimental_rerun)()


#  внутренняя «лента» и «слот»
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


#  users
@with_session
def add_user(db, username: str, password: str,
             first_name: str, last_name: str, middle_name: str,
             phone: str, gender: str, email: str,
             role: str = "user", org_name: str | None = None,
             is_confirmed: int = 0) -> bool:
    if db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first():
        return False

    db.add(User(
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
    ))
    db.commit()
    return True


@with_session
def validate_user(db, username: str, password: str) -> str | None:
    user = db.query(User).filter_by(username=username).first()
    return user.role if user and bcrypt.verify(password, user.pwd_hash) else None


@with_session
def list_users(db):
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


@with_session
def confirm_user(db, user_id: int):
    if (u := db.query(User).filter_by(id=user_id).first()):
        u.is_confirmed = 1
        db.commit()


@with_session
def remove_user(db, user_id: int):
    db.query(User).filter_by(id=user_id).delete()
    db.commit()


#  lanes & timeslots
@with_session
def list_lanes(db):
    return sorted(l.number for l in db.query(Lane).all())


@with_session
def list_timeslots(db):
    return sorted(t.time.strftime("%H:%M") for t in db.query(Timeslot).all())


@with_session
def add_timeslot(db, time_obj: dt_time) -> bool:
    if db.query(Timeslot).filter_by(time=time_obj).first():
        return False
    db.add(Timeslot(time=time_obj))
    db.commit()
    return True


@with_session
def remove_timeslot(db, time_str: str):
    t = datetime.strptime(time_str, "%H:%M").time()
    db.query(Timeslot).filter_by(time=t).delete()
    db.commit()


#  trainers (интерфейс прежний)
@with_session
def list_trainers(db, full: bool = False):
    query = db.query(Trainer).all()
    if full:
        return [{
            "name": t.name,
            "short_fio": f"{t.last_name} {t.first_name[0]}.{t.middle_name[0] + '.' if t.middle_name else ''}",
            "age": t.agebigint,
            "description": t.description,
        } for t in query]
    return [t.name for t in query]


@with_session
def add_trainer(db, name: str, first: str, last: str, middle: str,
                age: int, desc: str) -> bool:
    if db.query(Trainer).filter_by(name=name).first():
        return False
    db.add(Trainer(
        name=name,
        first_name=first,
        last_name=last,
        middle_name=middle,
        agebigint=age,
        description=desc
    ))
    db.commit()
    return True


@with_session
def remove_trainer(db, name: str):
    db.query(Trainer).filter_by(name=name).delete()
    db.commit()


@with_session
def get_trainer_by_name(db, name: str):
    t = db.query(Trainer).filter_by(name=name).first()
    if t:
        return {
            "first_name": t.first_name,
            "last_name":  t.last_name,
            "middle_name": t.middle_name or "",
            "age": t.agebigint,
            "description": t.description,
        }
    return None


#  trainer schedule
@with_session
def list_trainer_schedule(db):
    sch = db.query(TrainerSchedule).all()
    return [{
        "id": s.id,
        "trainer": s.trainer.name,
        "day_of_week": s.day_of_week,
        "time": s.timeslot.time.strftime("%H:%M"),
    } for s in sch]


@with_session
def add_trainer_schedule(db, trainer_name: str, dow: int, time_str: str) -> bool:
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


@with_session
def remove_trainer_schedule(db, schedule_id: int):
    db.query(TrainerSchedule).filter_by(id=schedule_id).delete()
    db.commit()


#  bookings
def _booking_exists(db, date, timeslot_id, lane_id=None, trainer_id=None) -> bool:
    q = db.query(Booking).filter_by(date=date, timeslot_id=timeslot_id)
    if lane_id is not None:
        q = q.filter_by(lane_id=lane_id)
    if trainer_id is not None:
        q = q.filter_by(trainer_id=trainer_id)
    return q.first() is not None


@with_session
def add_booking(db, username, date, time_str, lane_number, trainer_name=None):
    user = db.query(User).filter_by(username=username).first()
    ts = _get_timeslot(db, time_str)
    lane = _get_lane(db, lane_number)
    trainer = db.query(Trainer).filter_by(name=trainer_name).first() if trainer_name else None

    exists = db.query(Booking).filter_by(
        user_id=user.id,
        date=date,
        timeslot_id=ts.id,
        lane_id=lane.id,
        trainer_id=trainer.id if trainer else None
    ).first()
    if exists:
        return False

    booking = Booking(
        user_id=user.id,
        date=date,
        timeslot_id=ts.id,
        lane_id=lane.id,
        trainer_id=trainer.id if trainer else None
    )
    db.add(booking)
    db.commit()
    return True


@with_session
def list_user_bookings(db, username):
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


@with_session
def remove_booking(db, booking_id: int):
    db.query(Booking).filter_by(id=booking_id).delete()
    db.commit()


@with_session
def list_all_bookings_for_date(db, date):
    bookings = db.query(Booking).filter_by(date=date).all()
    return [{
        "id": b.id,
        "user": b.user.username,
        "date": b.date,
        "time": b.timeslot.time.strftime("%H:%M"),
        "lane": b.lane.number,
        "trainer": b.trainer.name if b.trainer else "—",
    } for b in bookings]


@with_session
def lane_trainer_status(db, date, time_str):
    ts = _get_timeslot(db, time_str)
    bks = db.query(Booking).filter_by(date=date, timeslot_id=ts.id).all()
    lanes = [bk.lane.number for bk in bks]
    trainers = [bk.trainer.name for bk in bks if bk.trainer]
    return lanes, trainers


@with_session
def get_scheduled_trainers(db, date, time_str):
    ts = _get_timeslot(db, time_str)
    sch = db.query(TrainerSchedule).filter_by(
        day_of_week=date.weekday(), timeslot_id=ts.id
    ).all()
    return [s.trainer.name for s in sch]


#  групповые бронирования
@with_session
def add_org_booking_group(db, username, date, times, lanes):
    user = db.query(User).filter_by(username=username).first()
    if not user:
        return False

    base_ts = _get_timeslot(db, times[0])
    group = OrgBookingGroup(
        user_id=user.id,
        date=date,
        lanes=",".join(str(l) for l in lanes),
        times=",".join(times),
        time=base_ts.time,
        created_at=datetime.now().isoformat()
    )
    db.add(group)
    db.flush()

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


@with_session
def list_org_booking_groups(db, username):
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


@with_session
def remove_org_booking_group(db, group_id: int):
    db.query(Booking).filter_by(group_id=group_id).delete()
    db.query(OrgBookingGroup).filter_by(id=group_id).delete()
    db.commit()


#  closed slots
@with_session
def list_closed_slots(db, date):
    slots = db.query(ClosedSlot).filter_by(date=date).order_by(ClosedSlot.timeslot_id).all()
    return [{
        "id": s.id,
        "date": s.date,
        "time": s.timeslot.time.strftime("%H:%M"),
        "comment": s.comment or "",
    } for s in slots]


@with_session
def add_closed_slot(db, date, time_str, comment=None, lane_number=1) -> bool:
    ts = _get_timeslot(db, time_str)
    lane = _get_lane(db, lane_number)
    if db.query(ClosedSlot).filter_by(date=date, timeslot_id=ts.id, lane_id=lane.id).first():
        return False
    db.add(ClosedSlot(
        date=date,
        time=ts.time,
        comment=comment or "",
        lane_id=lane.id,
        timeslot_id=ts.id
    ))
    db.commit()
    return True


@with_session
def remove_closed_slot(db, slot_id: int):
    db.query(ClosedSlot).filter_by(id=slot_id).delete()
    db.commit()


@with_session
def is_slot_closed(db, date, time_str) -> bool:
    ts = _get_timeslot(db, time_str)
    return db.query(ClosedSlot).filter_by(date=date, timeslot_id=ts.id).first() is not None

@with_session
def add_slot(db, trainer_name: str, date: str, time_start: str, time_end: str) -> bool:
    from datetime import datetime as dt
    trainer = db.query(Trainer).filter_by(name=trainer_name).first()
    if not trainer:
        return False
    t_start = dt.strptime(time_start, "%H:%M").time()
    ts = db.query(Timeslot).filter_by(time=t_start).first()
    if not ts:
        ts = Timeslot(time=t_start)
        db.add(ts)
        db.flush()
    dow = dt.strptime(date, "%Y-%m-%d").weekday()
    if db.query(TrainerSchedule).filter_by(trainer_id=trainer.id, timeslot_id=ts.id, day_of_week=dow).first():
        return False
    db.add(TrainerSchedule(trainer_id=trainer.id, timeslot_id=ts.id, day_of_week=dow))
    db.commit()
    return True
