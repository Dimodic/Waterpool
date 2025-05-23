import streamlit as st
from sqlalchemy import (
    create_engine,
    Column, Integer, String, Date, Time,
    ForeignKey, UniqueConstraint, inspect, text
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import DBAPIError, OperationalError

# --- Настройка подключения --------------------------------------------------
def _connection_url():
    cfg = st.secrets["postgres"]
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

ENGINE = create_engine(
    _connection_url(),
    pool_size=10,
    max_overflow=20,
    future=True,
    echo=True,  # логирование SQL-запросов
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# --- ORM-модели --------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), unique=True, nullable=False, index=True)
    pwd_hash     = Column(String(128), nullable=False)
    role         = Column(String(10), default="user")
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
        UniqueConstraint("trainer_id", "timeslot_id", "day_of_week"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    trainer_id   = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    timeslot_id  = Column(Integer, ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)
    day_of_week  = Column(Integer, nullable=False)

    trainer      = relationship("Trainer", back_populates="schedules")
    timeslot     = relationship("Timeslot")

class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("date", "time", "lane",    name="uq_lane_per_slot"),
        UniqueConstraint("date", "time", "trainer", name="uq_trainer_per_slot"),
    )

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date      = Column(Date,  nullable=False)
    time      = Column(Time,  nullable=False)
    lane      = Column(Integer, nullable=False)
    trainer   = Column(String(50), nullable=False)

    user      = relationship("User", back_populates="bookings")

# --- Инициализация и миграция ------------------------------------------------
def init_db():
    # 1) Проверка подключения
    try:
        with ENGINE.connect():
            pass
    except OperationalError as e:
        st.error(f"Не удалось подключиться к базе данных:\n{e}")
        st.stop()

    # 2) Создание таблиц
    try:
        Base.metadata.create_all(bind=ENGINE)
    except DBAPIError as e:
        orig = getattr(e, "orig", e)
        st.error(f"Ошибка при создании таблиц:\n{orig}")
        st.stop()

    # 3) Миграция: добавляем недостающие поля в users
    inspector = inspect(ENGINE)
    existing_cols = [col["name"] for col in inspector.get_columns("users")]

    migrations = {
        'first_name':  "VARCHAR(50) NOT NULL DEFAULT ''",
        'last_name':   "VARCHAR(50) NOT NULL DEFAULT ''",
        'middle_name': "VARCHAR(50)",
        'phone':       "VARCHAR(20)",
        'gender':      "VARCHAR(10)",
        'email':       "VARCHAR(100) NOT NULL DEFAULT ''"
    }

    with ENGINE.begin() as conn:
        for col, definition in migrations.items():
            if col not in existing_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))

    # 4) Дефолтные данные
    from passlib.hash import bcrypt
    from datetime import time

    with SessionLocal() as db:
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(
                username="admin",
                pwd_hash=bcrypt.hash("admin"),
                role="admin",
                first_name="Админ",
                last_name="Админов",
                middle_name="",
                phone="",
                gender="",
                email="admin@example.com"
            ))

        default_hours = [time(h, 0) for h in range(9, 18)]
        for t in default_hours:
            if not db.query(Timeslot).filter_by(time=t).first():
                db.add(Timeslot(time=t))

        db.commit()
