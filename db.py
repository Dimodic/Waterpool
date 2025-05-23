import os
import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Time,
    ForeignKey, UniqueConstraint, Table
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.ext.hybrid import hybrid_property

# --- Подключение к базе -----------------------------------------------------
def _connection_url():
    cfg = st.secrets["postgres"]
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

ENGINE = create_engine(_connection_url(), pool_size=10, max_overflow=20, future=True)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
Base = declarative_base()

# --- Модели ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    pwd_hash = Column(String(128), nullable=False)
    role = Column(String(10), default="user")

    bookings = relationship("Booking", back_populates="user", cascade="all, delete")


class Timeslot(Base):
    __tablename__ = "timeslots"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(Time, unique=True, nullable=False)


class TrainerSchedule(Base):
    __tablename__ = "trainer_schedule"
    __table_args__ = (
        UniqueConstraint("trainer_name", "day_of_week", "time", name="uq_trainer_schedule"),
    )

    id = Column(Integer, primary_key=True)
    trainer_name = Column(String(50), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    time = Column(Time, nullable=False)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("date", "time", "lane", name="uq_lane_per_slot"),
        UniqueConstraint("date", "time", "trainer", name="uq_trainer_per_slot"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    lane = Column(Integer, nullable=False)
    trainer = Column(String(50), nullable=False)

    user = relationship("User", back_populates="bookings")


# --- Инициализация БД --------------------------------------------------------
def init_db():
    import logging
    from passlib.hash import bcrypt
    from datetime import time

    logger = logging.getLogger(__name__)

    Base.metadata.create_all(bind=ENGINE)
    with SessionLocal() as db:
        if not db.query(User).filter_by(username="admin").first():
            admin = User(
                username="admin",
                pwd_hash=bcrypt.hash("admin"),
                role="admin",
            )
            db.add(admin)
            logger.info("Добавлен администратор по умолчанию")

        default_hours = [time(h, 0) for h in range(9, 18)]
        for t in default_hours:
            if not db.query(Timeslot).filter_by(time=t).first():
                db.add(Timeslot(time=t))

        db.commit()