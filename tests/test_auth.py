import pytest
from app.auth import verify_password, get_password_hash

def test_verify_password_correct():
    """Test that a correct password matches its hash."""
    password = "supersecretpassword123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True

def test_verify_password_incorrect():
    """Test that an incorrect password does not match the hash."""
    password = "supersecretpassword123"
    wrong_password = "wrongpassword"
    hashed = get_password_hash(password)
    assert verify_password(wrong_password, hashed) is False

def test_verify_password_empty_string():
    """Test empty string behavior."""
    password = ""
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("notempty", hashed) is False

def test_verify_password_type_handling():
    """Test behavior with non-string inputs.
    We expect it to raise an exception like TypeError, depending on the underlying passlib implementation.
    """
    hashed = get_password_hash("password")

    with pytest.raises(Exception):
        verify_password(12345, hashed)
