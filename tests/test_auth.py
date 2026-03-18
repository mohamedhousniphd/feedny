import pytest
from datetime import timedelta
from app.auth import create_access_token, decode_access_token

def test_decode_valid_access_token():
    data = {"sub": "testuser"}
    token = create_access_token(data)

    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "testuser"
    assert "exp" in decoded

def test_decode_invalid_access_token():
    decoded = decode_access_token("invalid_token")
    assert decoded is None

def test_decode_expired_access_token():
    data = {"sub": "testuser", "status": "expired"}
    token = create_access_token(data, expires_delta=timedelta(minutes=-10))

    decoded = decode_access_token(token)
    assert decoded is None
