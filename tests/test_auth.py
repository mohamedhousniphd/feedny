"""Tests for authentication logic."""
import os
import calendar
from datetime import datetime, timedelta
import pytest
from jose import jwt, JWTError

from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    SECRET_KEY,
    ALGORITHM,
    pwd_context
)

def test_verify_password():
    password = "secret_password"
    # Create a real hash to test verification
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_get_password_hash():
    password = "secret_password"
    hashed = get_password_hash(password)

    # Hash should be different from password and verifiable
    assert hashed != password
    assert pwd_context.verify(password, hashed) is True

def test_create_access_token_default_expiry():
    """Test creating an access token with default expiry (15 minutes)."""
    data = {"sub": "testuser"}

    # Create token
    token = create_access_token(data)

    # Verify token type
    assert isinstance(token, str)

    # Decode token using unverified claims to inspect them without needing the secret
    payload = jwt.get_unverified_claims(token)

    # Verify data payload
    assert payload["sub"] == "testuser"

    # Verify expiry claim is present
    assert "exp" in payload

    # Calculate expected expiry (approx 15 mins from now)
    expected_exp = datetime.utcnow() + timedelta(minutes=15)
    expected_exp_timestamp = calendar.timegm(expected_exp.utctimetuple())

    # Assert expiry is roughly 15 minutes in the future (allow 5 seconds difference for execution time)
    assert abs(payload["exp"] - expected_exp_timestamp) <= 5

def test_create_access_token_custom_expiry():
    """Test creating an access token with custom expiry."""
    data = {"sub": "customuser", "role": "admin"}
    expires_delta = timedelta(hours=1)

    # Create token
    token = create_access_token(data, expires_delta=expires_delta)

    # Verify token type
    assert isinstance(token, str)

    # Decode token using unverified claims
    payload = jwt.get_unverified_claims(token)

    # Verify data payload
    assert payload["sub"] == "customuser"
    assert payload["role"] == "admin"
    assert "exp" in payload

    # Calculate expected custom expiry
    expected_exp = datetime.utcnow() + timedelta(hours=1)
    expected_exp_timestamp = calendar.timegm(expected_exp.utctimetuple())

    # Assert expiry is roughly 1 hour in the future (allow 5 seconds difference)
    assert abs(payload["exp"] - expected_exp_timestamp) <= 5

def test_decode_access_token_success():
    data = {"sub": "user_id"}
    token = create_access_token(data)

    # Test the decode function
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user_id"
    assert "exp" in payload

def test_decode_access_token_failure():
    # Test with an invalid token
    invalid_token = "invalid.token.string"
    payload = decode_access_token(invalid_token)

    assert payload is None
