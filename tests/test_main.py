import pytest
from unittest.mock import MagicMock, patch
import asyncio

import app.main as main
from fastapi import Request, HTTPException

@pytest.mark.asyncio
async def test_get_current_teacher_missing_token():
    request = MagicMock(spec=Request)
    request.cookies.get.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await main.get_current_teacher(request)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Not authenticated"

@pytest.mark.asyncio
@patch('app.main.decode_access_token')
async def test_get_current_teacher_invalid_token(mock_decode):
    request = MagicMock(spec=Request)
    request.cookies.get.return_value = "invalid_token"
    mock_decode.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await main.get_current_teacher(request)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid token"

@pytest.mark.asyncio
@patch('app.main.decode_access_token')
@patch('app.main.get_teacher_by_email')
async def test_get_current_teacher_not_found(mock_get_teacher, mock_decode):
    request = MagicMock(spec=Request)
    request.cookies.get.return_value = "valid_token"
    mock_decode.return_value = {"sub": "test@example.com"}
    mock_get_teacher.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await main.get_current_teacher(request)

    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Teacher not found"

@pytest.mark.asyncio
@patch('app.main.decode_access_token')
@patch('app.main.get_teacher_by_email')
async def test_get_current_teacher_success(mock_get_teacher, mock_decode):
    request = MagicMock(spec=Request)
    request.cookies.get.return_value = "valid_token"
    mock_decode.return_value = {"sub": "test@example.com"}
    mock_teacher = {"email": "test@example.com", "name": "Test Teacher"}
    mock_get_teacher.return_value = mock_teacher

    teacher = await main.get_current_teacher(request)

    assert teacher == mock_teacher
