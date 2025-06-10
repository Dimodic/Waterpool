from app import utils

def test_add_user(monkeypatch, session):
    # Подменяем SessionLocal на тестовую сессию
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    ok = utils.add_user(
        "testuser", "testpass", "Иван", "Иванов", "", "+79990001122", "male", "test@t.ru"
    )
    assert ok

def test_validate_user(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    # Сначала добавим пользователя
    utils.add_user(
        "testuser2", "pw", "Петр", "Петров", "", "+79991112233", "male", "test2@t.ru"
    )
    role = utils.validate_user("testuser2", "pw")
    assert role == "user"
    role_bad = utils.validate_user("testuser2", "badpass")
    assert role_bad is None

def test_remove_user(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    utils.add_user(
        "toremove", "pw", "Имя", "Фам", "", "+79998887766", "male", "remove@t.ru"
    )
    user_id = [u["id"] for u in utils.list_users() if u["username"] == "toremove"][0]
    utils.remove_user(user_id)
    users = utils.list_users()
    assert all(u["username"] != "toremove" for u in users)

def test_add_duplicate_user(monkeypatch, session):
    monkeypatch.setattr(utils, "SessionLocal", lambda: session)
    ok = utils.add_user(
        "dupl", "pass", "Имя", "Фам", "", "+79997778899", "male", "dupl@t.ru"
    )
    assert ok
    # Попытка добавить с тем же username/email
    fail = utils.add_user(
        "dupl", "pass2", "Имя2", "Фам2", "", "+78889997777", "male", "dupl@t.ru"
    )
    assert fail is False
