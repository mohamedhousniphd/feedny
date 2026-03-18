from unittest.mock import MagicMock, patch

try:
    from app.main import get_device_id
except ImportError:
    get_device_id = None

import pytest

@pytest.mark.skipif(get_device_id is None, reason="Dependencies not installed in this environment")
def test_get_device_id_has_cookie():
    request = MagicMock()
    request.cookies.get.return_value = "existing-device-id"

    device_id = get_device_id(request)

    assert device_id == "existing-device-id"
    request.cookies.get.assert_called_once_with("device_id")

@pytest.mark.skipif(get_device_id is None, reason="Dependencies not installed in this environment")
def test_get_device_id_no_cookie():
    with patch('app.main.uuid.uuid4', return_value="new-uuid-value"):
        request = MagicMock()
        request.cookies.get.return_value = None

        device_id = get_device_id(request)

        assert device_id == "new-uuid-value"
        request.cookies.get.assert_called_once_with("device_id")
