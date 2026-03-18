import pytest
from app.auth import verify_password, get_password_hash

def test_get_password_hash():
    """Test generating a password hash."""
    password = "my_secure_password"
    hashed = get_password_hash(password)

    assert hashed is not None
    assert isinstance(hashed, str)
    assert hashed != password

def test_verify_password_success():
    """Test successful password verification."""
    password = "correct_password"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True

def test_verify_password_failure():
    """Test failed password verification."""
    password = "correct_password"
    wrong_password = "wrong_password"
    hashed = get_password_hash(password)

    assert verify_password(wrong_password, hashed) is False

def test_verify_password_empty():
    """Test verification with empty strings."""
    password = ""
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
    assert verify_password("", get_password_hash("something")) is False

def test_verify_password_special_chars():
    """Test password verification with special characters."""
    password = "p@$$w0rd!#%^&*"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
