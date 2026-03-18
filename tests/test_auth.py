import pytest
from datetime import timedelta
from unittest.mock import patch

from app.auth import create_access_token, decode_access_token, JWTError

@patch("app.auth.jwt.decode")
@patch("app.auth.jwt.encode")
def test_decode_access_token_valid(mock_encode, mock_decode):
    """Test decoding a valid access token."""
    mock_encode.return_value = "mocked.token.string"
    mock_decode.return_value = {"sub": "testuser", "exp": 1234567890}

    data = {"sub": "testuser"}
    token = create_access_token(data)
    decoded = decode_access_token(token)

    assert decoded is not None
    assert decoded["sub"] == "testuser"
    assert "exp" in decoded

@patch("app.auth.jwt.decode")
def test_decode_access_token_invalid_string(mock_decode):
    """Test decoding an invalid string."""
    mock_decode.side_effect = JWTError("Invalid token")

    token = "invalid.token.string"
    decoded = decode_access_token(token)

    assert decoded is None

@patch("app.auth.jwt.decode")
@patch("app.auth.jwt.encode")
def test_decode_access_token_expired(mock_encode, mock_decode):
    """Test decoding an expired access token."""
    mock_encode.return_value = "mocked.expired.token"
    mock_decode.side_effect = JWTError("Signature has expired")

    data = {"sub": "testuser"}
    # Create a token that expired 15 minutes ago
    token = create_access_token(data, expires_delta=timedelta(minutes=-15))
    decoded = decode_access_token(token)

    assert decoded is None
