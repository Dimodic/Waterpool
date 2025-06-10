from app import utils
from datetime import time as dt_time, date, time


def setup_user_trainer_schedule():
    utils.add_user("vasya", "pass", "Vasya", "Pupkin", "", "+79991112233", "male", "vasya@wp.ru", is_confirmed=1)
    utils.add_trainer("Тренер Иван Иванович", "Иван", "Иванов", "Иванович", 30, "Супер тренер")
    utils.add_timeslot(time(10, 0))
    utils.add_trainer_schedule("Тренер Иван Иванович", 0, "10:00")  # Понедельник
    return "vasya", "Тренер Иван Иванович", "10:00"

def test_user_booking_and_cancel():
    username, trainer, time_str = setup_user_trainer_schedule()
    today = date.today()
    ok = utils.add_booking(username, today, time_str, 1, trainer)
    assert ok
    bookings = utils.list_user_bookings(username)
    assert any(b["trainer"] == trainer for b in bookings)
    booking_id = [b["id"] for b in bookings if b["trainer"] == trainer][0]
    utils.remove_booking(booking_id)
    bookings = utils.list_user_bookings(username)
    assert all(b["trainer"] != trainer for b in bookings)

def test_double_booking():
    username, trainer, time_str = setup_user_trainer_schedule()
    today = date.today()
    ok1 = utils.add_booking(username, today, time_str, 1, trainer)
    assert ok1
    ok2 = utils.add_booking(username, today, time_str, 1, trainer)
    assert not ok2


def test_lane_trainer_status():
    utils.add_user("vasya", "pass", "Vasya", "Pupkin", "", "+79991112233", "male", "vasya@wp.ru", is_confirmed=1)
    utils.add_trainer("Тренер Иван Иванович", "Иван", "Иванов", "Иванович", 30, "Супер тренер")
    utils.add_timeslot(dt_time(10, 0))
    utils.add_trainer_schedule("Тренер Иван Иванович", 0, "10:00")
    today = date.today()
    # Бронируем только lane 2
    utils.add_booking("vasya", today, "10:00", 2, "Тренер Иван Иванович")
    print("ALL BOOKINGS:", utils.list_all_bookings_for_date(today))
    lanes, trainers = utils.lane_trainer_status(today, "10:00")
    print("lanes:", lanes)
    assert 2 in lanes
    assert "Тренер Иван Иванович" in trainers


def test_group_org_booking():
    utils.add_user(
        "orguser", "pw", "Org", "User", None, "+79991111111", "other", "org@t.ru",
        role="org", org_name="Org Organization", is_confirmed=1
    )
    utils.add_timeslot(time(9, 0))
    utils.add_timeslot(time(10, 0))
    today = date.today()
    ok = utils.add_org_booking_group("orguser", today, ["09:00", "10:00"], [1, 2])
    assert ok
    groups = utils.list_org_booking_groups("orguser")
    assert any(g["date"] == today for g in groups)
