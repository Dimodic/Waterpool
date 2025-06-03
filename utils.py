# utils.py
from sqlalchemy.orm import sessionmaker
from models import User, Base, Timeslot, ClosedSlot, Booking, TrainerSchedule
from sqlalchemy import create_engine
import datetime

engine = create_engine("sqlite:///db.sqlite", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def validate_user(username: str, password: str):
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username, password=password).first()
        if user:
            return user.role
        return None

def add_user(username, password,
             first_name, last_name, middle_name,
             phone, gender, email,
             role="user", org_name=None, is_confirmed=0):
    with SessionLocal() as db:
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            return False
        user = User(
            username=username, password=password,
            first_name=first_name, last_name=last_name,
            middle_name=middle_name, phone=phone,
            gender=gender, email=email,
            role=role, org_name=org_name,
            is_confirmed=is_confirmed
        )
        db.add(user)
        db.commit()
        return True

def list_timeslots():
    """Возвращает список всех базовых тайм-слотов (строка "HH:MM")."""
    with SessionLocal() as db:
        rows = db.query(Timeslot).order_by(Timeslot.time).all()
        return [row.time.strftime("%H:%M") for row in rows]

def list_closed_slots(for_date: datetime.date):
    """Возвращает список закрытых слотов на конкретную дату."""
    with SessionLocal() as db:
        rows = db.query(ClosedSlot).filter_by(date=for_date).all()
        return [{"id": row.id, "date": row.date, "time": row.time.strftime("%H:%M"), "comment": row.comment}
                for row in rows]

def add_closed_slot(date, time_str, comment=""):
    """Добавляет закрытый слот. date: date, time_str: "HH:MM"."""
    with SessionLocal() as db:
        existing = db.query(ClosedSlot).filter_by(date=date, time=time_str).first()
        if existing:
            return False
        new = ClosedSlot(date=date, time=time_str, comment=comment)
        db.add(new)
        db.commit()
        return True

def remove_closed_slot(slot_id):
    """Удаляет закрытый слот по ID."""
    with SessionLocal() as db:
        slot = db.query(ClosedSlot).get(slot_id)
        if slot:
            db.delete(slot)
            db.commit()

def list_all_bookings_for_date(for_date: datetime.date):
    """Возвращает список всех бронирований на дату."""
    with SessionLocal() as db:
        rows = db.query(Booking).filter_by(date=for_date).all()
        return [
            {"id": row.id, "user": row.username, "date": row.date, "time": row.time.strftime("%H:%M"),
             "lane": row.lane, "trainer": row.trainer or ""}
            for row in rows
        ]

def lane_trainer_status(date, time_str):
    """Возвращает два списка: занятые дорожки и занятых тренеров на конкретную дату и время."""
    with SessionLocal() as db:
        bookings = db.query(Booking).filter_by(date=date, time=time_str).all()
        busy_lanes = [b.lane for b in bookings]
        busy_trainers = [b.trainer for b in bookings if b.trainer]
        return busy_lanes, busy_trainers

def is_slot_closed(date, time_str):
    """Проверяет, закрыт ли слот."""
    with SessionLocal() as db:
        return db.query(ClosedSlot).filter_by(date=date, time=time_str).first() is not None

def list_user_bookings(username):
    """Возвращает список бронирований конкретного пользователя."""
    with SessionLocal() as db:
        rows = db.query(Booking).filter_by(username=username).all()
        return [
            {"id": row.id, "date": row.date, "time": row.time.strftime("%H:%M"),
             "lane": row.lane, "trainer": row.trainer or ""}
            for row in rows
        ]

def add_booking(username, date, time_str, lane, trainer=None):
    """Пытается добавить бронирование. Возвращает True/False."""
    with SessionLocal() as db:
        # Если слот закрыт – отказ
        if db.query(ClosedSlot).filter_by(date=date, time=time_str).first():
            return False
        # Проверяем, нет ли той же дорожки и времени
        exists = db.query(Booking).filter_by(date=date, time=time_str, lane=lane).first()
        if exists:
            return False
        # Проверяем тренера: если выбран, он должен быть свободен
        if trainer:
            booked_tr = db.query(Booking).filter_by(date=date, time=time_str, trainer=trainer).first()
            if booked_tr:
                return False
        # Создаём
        new = Booking(username=username, date=date, time=time_str, lane=lane, trainer=trainer)
        db.add(new)
        db.commit()
        return True

def remove_booking(booking_id):
    """Удаляет бронирование по ID."""
    with SessionLocal() as db:
        b = db.query(Booking).get(booking_id)
        if b:
            db.delete(b)
            db.commit()

def update_booking(booking_id, date, time_str, lane, trainer=None):
    """Обновляет существующее бронирование."""
    with SessionLocal() as db:
        b = db.query(Booking).get(booking_id)
        if not b:
            return False
        # Проверить занятость новой дорожки
        exists = db.query(Booking).filter(
            Booking.date == date, Booking.time == time_str,
            Booking.lane == lane, Booking.id != booking_id
        ).first()
        if exists or is_slot_closed(date, time_str):
            return False
        if trainer:
            exists_tr = db.query(Booking).filter(
                Booking.date == date, Booking.time == time_str,
                Booking.trainer == trainer, Booking.id != booking_id
            ).first()
            if exists_tr:
                return False
        b.date = date
        b.time = time_str
        b.lane = lane
        b.trainer = trainer
        db.commit()
        return True

def list_trainers():
    """Возвращает список всех имен тренеров."""
    with SessionLocal() as db:
        rows = db.query(TrainerSchedule.trainer).distinct().all()
        return [r[0] for r in rows]

def add_trainer(name):
    """Добавляет нового тренера (в таблицу TrainerSchedule появятся записи при заполнении расписания)."""
    # Здесь логика может быть в зависимости от структуры модели.
    # Если TrainerSchedule создаётся только через расписание, а список тренеров ведётся отдельно, –
    # предполагаем, что список тренеров ведётся в отдельной таблице, или добавляем логику самостоятельно.
    pass

def remove_trainer(name):
    """Удаляет тренера по имени."""
    with SessionLocal() as db:
        db.query(TrainerSchedule).filter_by(trainer=name).delete()
        db.commit()

def list_trainer_schedule():
    """Возвращает список записей расписания тренеров."""
    with SessionLocal() as db:
        rows = db.query(TrainerSchedule).all()
        return [
            {"id": row.id, "trainer": row.trainer, "day_of_week": row.day_of_week, "time": row.time.strftime("%H:%M")}
            for row in rows
        ]

def add_trainer_schedule(trainer, day_of_week, time_str):
    """Добавляет запись расписания тренеру. day_of_week: 0–6."""
    with SessionLocal() as db:
        exists = db.query(TrainerSchedule).filter_by(
            trainer=trainer, day_of_week=day_of_week, time=time_str
        ).first()
        if exists:
            return False
        new = TrainerSchedule(trainer=trainer, day_of_week=day_of_week, time=time_str)
        db.add(new)
        db.commit()
        return True

def remove_trainer_schedule(schedule_id):
    """Удаляет запись расписания тренера."""
    with SessionLocal() as db:
        row = db.query(TrainerSchedule).get(schedule_id)
        if row:
            db.delete(row)
            db.commit()
