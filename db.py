import streamlit as st
from sqlalchemy import (
    create_engine,
    Column, Integer, String, Date, Time,
    ForeignKey, UniqueConstraint, inspect, text
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import DBAPIError, OperationalError

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
    echo=True,
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

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
    is_confirmed = Column(Integer, default=0)

    bookings     = relationship("Booking", back_populates="user", cascade="all,delete")

class Timeslot(Base):
    __tablename__ = "timeslots"

    id   = Column(Integer, primary_key=True, index=True)
    time = Column(Time, unique=True, nullable=False)

class Trainer(Base):
    __tablename__ = "trainers"

    id          = Column(Integer, primary_key=True, index=True)
    first_name  = Column(String(50), nullable=False)
    last_name   = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    name        = Column(String(150), unique=True, nullable=False)  # legacy для selectbox (оставим, это ФИО)
    age         = Column(Integer, nullable=True)
    description = Column(String(200), nullable=True)
    schedules   = relationship("TrainerSchedule", back_populates="trainer", cascade="all,delete")

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

class OrgBookingGroup(Base):
    __tablename__ = "org_booking_groups"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    lanes = Column(String(50), nullable=False)
    created_at = Column(String(30), nullable=True)
    times = Column(String(200), nullable=True)

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
    trainer   = Column(String(150), nullable=False)
    group_id  = Column(Integer, ForeignKey("org_booking_groups.id", ondelete="CASCADE"), nullable=True)

    user      = relationship("User", back_populates="bookings")

class ClosedSlot(Base):
    __tablename__ = "closed_slots"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    comment = Column(String(200), nullable=True)
    __table_args__ = (UniqueConstraint("date", "time", name="uq_closed_slot"),)

def init_db():
    try:
        with ENGINE.connect():
            pass
    except OperationalError as e:
        st.error(f"Не удалось подключиться к базе данных:\n{e}")
        st.stop()

    try:
        Base.metadata.create_all(bind=ENGINE)
    except DBAPIError as e:
        orig = getattr(e, "orig", e)
        st.error(f"Ошибка при создании таблиц:\n{orig}")
        st.stop()

    inspector = inspect(ENGINE)
    existing_cols = [col["name"] for col in inspector.get_columns("users")]
    existing_booking_cols = [col["name"] for col in inspector.get_columns("bookings")]
    existing_tables = inspector.get_table_names()

    migrations = {
        'first_name':  "VARCHAR(50) NOT NULL DEFAULT ''",
        'last_name':   "VARCHAR(50) NOT NULL DEFAULT ''",
        'middle_name': "VARCHAR(50)",
        'phone':       "VARCHAR(20)",
        'gender':      "VARCHAR(10)",
        'email':       "VARCHAR(100) NOT NULL DEFAULT ''",
        'is_confirmed': "INTEGER NOT NULL DEFAULT 0"
    }

    with ENGINE.begin() as conn:
        for col, definition in migrations.items():
            if col not in existing_cols:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {definition}"))
        if "group_id" not in existing_booking_cols:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN group_id INTEGER REFERENCES org_booking_groups(id) ON DELETE CASCADE"))
        if "org_booking_groups" not in existing_tables:
            conn.execute(text("""
                CREATE TABLE org_booking_groups (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    lanes VARCHAR(50) NOT NULL,
                    created_at VARCHAR(30),
                    times VARCHAR(200)
                )
            """))
        existing_org_group_cols = [col["name"] for col in inspector.get_columns("org_booking_groups")] if "org_booking_groups" in existing_tables else []
        if "org_booking_groups" in existing_tables and "times" not in existing_org_group_cols:
            conn.execute(text("ALTER TABLE org_booking_groups ADD COLUMN times VARCHAR(200)"))

        # --- Миграция для тренеров ---
        existing_trainer_cols = [col["name"] for col in inspector.get_columns("trainers")]
        if "first_name" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN first_name VARCHAR(50) NOT NULL DEFAULT ''"))
        if "last_name" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN last_name VARCHAR(50) NOT NULL DEFAULT ''"))
        if "middle_name" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN middle_name VARCHAR(50)"))
        if "age" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN age INTEGER"))
        if "description" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN description VARCHAR(200)"))
        if "name" not in existing_trainer_cols:
            conn.execute(text("ALTER TABLE trainers ADD COLUMN name VARCHAR(150) NOT NULL DEFAULT ''"))

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
