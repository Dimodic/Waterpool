from app import utils
from datetime import date, time

def test_add_and_remove_trainer(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    ok = utils.add_trainer("Тренер Тест", "Тест", "Тестов", "", 35, "Описание")
    assert ok
    trainers = utils.list_trainers(full=True)
    assert any(t["name"] == "Тренер Тест" for t in trainers)
    utils.remove_trainer("Тренер Тест")
    trainers = utils.list_trainers(full=True)
    assert all(t["name"] != "Тренер Тест" for t in trainers)

def test_confirm_user(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    utils.add_user("unconfirmed", "pw", "Новый", "Пользователь", "", "+79992223344", "male", "unconf@wp.ru", is_confirmed=0)
    user_id = [u["id"] for u in utils.list_users() if u["username"] == "unconfirmed"][0]
    utils.confirm_user(user_id)
    user = [u for u in utils.list_users() if u["id"] == user_id][0]
    assert user["is_confirmed"] == 1

def test_remove_user(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    utils.add_user("todelete", "pw", "Del", "Me", "", "+79995556677", "male", "del@wp.ru")
    user_id = [u["id"] for u in utils.list_users() if u["username"] == "todelete"][0]
    utils.remove_user(user_id)
    users = utils.list_users()
    assert all(u["username"] != "todelete" for u in users)

def test_add_and_remove_closed_slot(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    today = date.today()
    slot_time = time(12, 0)
    utils.add_timeslot(slot_time)
    ok = utils.add_closed_slot(today, "12:00", "тест закрытия")
    assert ok
    closed = utils.list_closed_slots(today)
    assert any(s["time"] == "12:00" for s in closed)
    slot_id = [s["id"] for s in closed if s["time"] == "12:00"][0]
    utils.remove_closed_slot(slot_id)
    closed = utils.list_closed_slots(today)
    assert all(s["time"] != "12:00" for s in closed)
