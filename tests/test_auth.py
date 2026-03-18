import os
from datetime import timedelta
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

def test_create_access_token_no_expires():
    data = {"sub": "user_id"}
    token = create_access_token(data)

    # Verify the token is a string and has 3 parts (header.payload.signature)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    # Decode to verify contents
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user_id"
    assert "exp" in payload

def test_create_access_token_with_expires():
    data = {"sub": "user_id"}
    expires = timedelta(minutes=30)

    token = create_access_token(data, expires_delta=expires)

    # Verify the token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user_id"
    assert "exp" in payload

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
