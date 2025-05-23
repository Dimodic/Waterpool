import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Time,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

def _connection_url():
    cfg = st.secrets["postgres"]  # host, port, user, password, dbname
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

ENGINE = create_engine(_connection_url(), pool_size=10, max_overflow=20, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), unique=True, nullable=False, index=True)
    pwd_hash     = Column(String(128), nullable=False)
    role         = Column(String(10), default="user")  # 'user' | 'admin'
    first_name   = Column(String(50), nullable=False)
    last_name    = Column(String(50), nullable=False)
    middle_name  = Column(String(50), nullable=True)
    phone        = Column(String(20), nullable=True)
    gender       = Column(String(10), nullable=True)
    email        = Column(String(100), unique=True, nullable=False, index=True)

    bookings     = relationship("Booking", back_populates="user", cascade="all,delete")

class Timeslot(Base):
    __tablename__ = "timeslots"

    id   = Column(Integer, primary_key=True, index=True)
    time = Column(Time, unique=True, nullable=False)

class Trainer(Base):
    __tablename__ = "trainers"

    id        = Column(Integer, primary_key=True, index=True)
    name      = Column(String(50), unique=True, nullable=False)

    schedules = relationship("TrainerSchedule", back_populates="trainer", cascade="all,delete")

class TrainerSchedule(Base):
    __tablename__ = "trainer_schedules"
    __table_args__ = (
        UniqueConstraint("trainer_id", "timeslot_id", "day_of_week", name="uq_trainer_schedule"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    trainer_id   = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    timeslot_id  = Column(Integer, ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)
    day_of_week  = Column(Integer, nullable=False)  # 0=Monday … 6=Sunday

    trainer      = relationship("Trainer", back_populates="schedules")
    timeslot     = relationship("Timeslot")

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("date", "time", "lane", name="uq_lane_per_slot"),
        UniqueConstraint("date", "time", "trainer", name="uq_trainer_per_slot"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date      = Column(Date,  nullable=False)
    time      = Column(Time,  nullable=False)
    lane      = Column(Integer, nullable=False)         # 1–6
    trainer   = Column(String(50), nullable=False)      # имя тренера

    user      = relationship("User", back_populates="bookings")

def init_db():
    """Создаём таблицы, если их ещё нет, и добавляем дефолтные данные."""
    Base.metadata.create_all(bind=ENGINE)

    from passlib.hash import bcrypt
    from datetime import time
    with SessionLocal() as db:
        # --- администратор по умолчанию ---
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(
                username="admin", pwd_hash=bcrypt.hash("admin"), role="admin",
                first_name="Админ", last_name="Админов", middle_name="",
                phone="", gender="", email="admin@example.com"
            ))
        # --- стандартные слоты (09:00–17:00) ---
        default_hours = [time(h, 0) for h in range(9, 18)]
        for t in default_hours:
            if not db.query(Timeslot).filter_by(time=t).first():
                db.add(Timeslot(time=t))
        # --- стандартные тренеры ---
        default_trainers = ["Тренер 1", "Тренер 2", "Тренер 3", "Тренер 4"]
        for name in default_trainers:
            if not db.query(Trainer).filter_by(name=name).first():
                db.add(Trainer(name=name))
        db.commit()
