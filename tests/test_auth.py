# tests/test_auth.py

from app import auth


def test_is_valid_phone():
    # Валидные телефоны
    assert auth.is_valid_phone("+7 912 345-67-89")
    assert auth.is_valid_phone("+7 9123456789")
    assert auth.is_valid_phone("+79123456789")
    # Не валидные
    assert not auth.is_valid_phone("89123456789")      # Без +
    assert not auth.is_valid_phone("+7 912 345")       # Коротко
    assert not auth.is_valid_phone("12345")            # Вообще не телефон
    assert not auth.is_valid_phone("+7123456789a")     # Буква

def test_is_valid_email():
    # Валидные email
    assert auth.is_valid_email("user@example.com")
    assert auth.is_valid_email("test.user+something@domain.co.uk")
    # Не валидные email
    assert not auth.is_valid_email("user@")
    assert not auth.is_valid_email("user@com")
    assert not auth.is_valid_email("user@.com")
    assert not auth.is_valid_email("user.com")
    assert not auth.is_valid_email("@domain.com")
