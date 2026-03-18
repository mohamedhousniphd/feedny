from datetime import timedelta
from jose import jwt
import passlib.context
import pytest

from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    ALGORITHM
)


def test_verify_password_success():
    """Test successful password verification."""
    password = "correct_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True


def test_verify_password_failure():
    """Test failed password verification."""
    password = "correct_password"
    hashed = get_password_hash(password)
    assert verify_password("wrong_password", hashed) is False


def test_get_password_hash():
    """Test password hashing structure."""
    password = "my_password"
    hashed = get_password_hash(password)
    # The hash should not be the plaintext
    assert hashed != password
    # The hash should be a string
    assert isinstance(hashed, str)
    # The hash should be verifiable
    assert verify_password(password, hashed) is True


def test_create_access_token_default_expiry():
    """Test creating access token with default expiration."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    # Token should be a string
    assert isinstance(token, str)

    # Verify the token can be decoded by decode_access_token
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == "testuser"
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    """Test creating access token with custom expiration."""
    data = {"sub": "testuser"}
    expires = timedelta(minutes=30)
    token = create_access_token(data, expires_delta=expires)

    assert isinstance(token, str)

    # Verify the token can be decoded by decode_access_token
    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == "testuser"
    assert "exp" in payload


def test_decode_access_token_success():
    """Test successful decoding of an access token."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload.get("sub") == "testuser"


def test_decode_access_token_failure():
    """Test decoding an invalid access token returns None."""
    payload = decode_access_token("invalid_token.that.fails")
    assert payload is None
