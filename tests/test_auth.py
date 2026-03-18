"""Tests for authentication logic."""
import os
import calendar
from datetime import datetime, timedelta
import pytest
from jose import jwt

from app.auth import create_access_token

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
