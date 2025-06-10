# db.py — ORM схема, синхронизированная с SQL-файлом
import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, Date, Time, BigInteger,
    ForeignKey, inspect
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import DBAPIError, OperationalError

#  engine

def get_engine(connection_url=None):
    if not connection_url:
        cfg = st.secrets["postgres"]
        connection_url = (
            f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
            f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
        )
    return create_engine(
        connection_url,
        pool_size=10,
        max_overflow=20,
        echo=False,
        future=True,
    )

def _connection_url() -> str:
    cfg = st.secrets["postgres"]
    return (
        f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}"
        f"@{cfg['host']}:{cfg['port']}/{cfg['dbname']}"
    )

ENGINE = create_engine(
    _connection_url(),
    pool_size=10,
    max_overflow=20,
    echo=False,
    future=True,
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

#  models

class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    username     = Column(String(50), nullable=False)
    pwd_hash     = Column(String(128), nullable=False)
    role         = Column(String(10), nullable=False)
    first_name   = Column(String(50), nullable=False)
    last_name    = Column(String(50), nullable=False)
    middle_name  = Column(String(50), nullable=False)
    phone        = Column(String(20), nullable=False)
    gender       = Column(String(10), nullable=False)
    email        = Column(String(50), nullable=False)
    is_confirmed = Column(Integer, nullable=False)

    bookings        = relationship("Booking", back_populates="user", cascade="all,delete")
    booking_groups  = relationship("OrgBookingGroup", back_populates="user", cascade="all,delete")


class Lane(Base):
    __tablename__ = "lanes"

    id     = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, nullable=False)
    name   = Column(String(50), nullable=False)


class Timeslot(Base):
    __tablename__ = "timeslots"

    id   = Column(Integer, primary_key=True, index=True)
    time = Column(Time, nullable=False)


class Trainer(Base):
    __tablename__ = "trainers"

    id           = Column(Integer, primary_key=True, index=True)
    first_name   = Column(String(50), nullable=False)
    last_name    = Column(String(50), nullable=False)
    middle_name  = Column(String(50), nullable=False)
    name         = Column(String(150), nullable=False)
    agebigint    = Column(Integer, nullable=False)
    description  = Column(String(200), nullable=False)

    schedules    = relationship("TrainerSchedule", back_populates="trainer", cascade="all,delete")

    @property
    def full_name(self) -> str:
        return f"{self.last_name} {self.first_name} {self.middle_name}" if self.middle_name else f"{self.last_name} {self.first_name}"


class TrainerSchedule(Base):
    __tablename__ = "trainer_schedules"

    id          = Column(Integer, primary_key=True, index=True)
    trainer_id  = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=False)
    timeslot_id = Column(Integer, ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon … 6=Sun

    trainer     = relationship("Trainer", back_populates="schedules")
    timeslot    = relationship("Timeslot")


class OrgBookingGroup(Base):
    __tablename__ = "org_booking_groups"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date        = Column(Date, nullable=False)
    time        = Column(Time, nullable=False)
    lanes       = Column(String(50), nullable=False)
    created_at  = Column(String(30), nullable=False)
    times       = Column(String(200), nullable=False)

    user        = relationship("User", back_populates="booking_groups")


class Booking(Base):
    __tablename__ = "bookings"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date      = Column(Date, nullable=False)
    timeslot_id = Column(Integer, ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)
    lane_id   = Column("lane", BigInteger, ForeignKey("lanes.id", ondelete="CASCADE"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id", ondelete="CASCADE"), nullable=True)
    group_id  = Column(Integer, ForeignKey("org_booking_groups.id", ondelete="CASCADE"), nullable=True)

    user      = relationship("User", back_populates="bookings")
    lane      = relationship("Lane")
    group     = relationship("OrgBookingGroup")
    timeslot  = relationship("Timeslot")
    trainer   = relationship("Trainer")


class ClosedSlot(Base):
    __tablename__ = "closed_slots"

    id          = Column(Integer, primary_key=True, index=True)
    date        = Column(Date, nullable=False)
    time        = Column(Time, nullable=False)
    comment     = Column(String(200), nullable=False)
    lane_id     = Column(Integer, ForeignKey("lanes.id", ondelete="CASCADE"), nullable=False)
    timeslot_id = Column(Integer, ForeignKey("timeslots.id", ondelete="CASCADE"), nullable=False)

    lane        = relationship("Lane")
    timeslot    = relationship("Timeslot")


class Table9(Base):
    __tablename__ = "table_9"

    id = Column(BigInteger, primary_key=True, index=True)

#  init

def init_db():
    """Создаём таблицы и сеем базовые справочники (6 дорожек, слоты 09:00–18:00)."""
    try:
        with ENGINE.connect():
            pass
    except OperationalError as e:
        st.error(f"Не удалось подключиться к БД:\n{e}")
        st.stop()

    try:
        Base.metadata.create_all(bind=ENGINE)
    except DBAPIError as e:
        st.error(f"Ошибка создания схемы:\n{e.orig if hasattr(e,'orig') else e}")
        st.stop()

    from datetime import time
    from passlib.hash import bcrypt

    with SessionLocal() as db:
        #  lanes
        if not db.query(Lane).count():
            for n in range(1, 7):
                db.add(Lane(number=n, name=f"Дорожка {n}"))

        #  timeslots
        default_hours = [time(h, 0) for h in range(9, 18)]
        for t in default_hours:
            if not db.query(Timeslot).filter_by(time=t).first():
                db.add(Timeslot(time=t))

        #  admin user
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(
                username="admin",
                pwd_hash=bcrypt.hash("admin"),
                role="admin",
                first_name="Админ",
                last_name="Админов",
                middle_name="",
                phone="",
                gender="other",
                email="admin@example.com",
                is_confirmed=1,
            ))

        db.commit()
