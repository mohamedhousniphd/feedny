import sys
from unittest.mock import MagicMock

# Mock jose
sys.modules['jose'] = MagicMock()

# Mock passlib
class MockCryptContext:
    def __init__(self, schemes=None, deprecated=None):
        self.schemes = schemes
        self.deprecated = deprecated

    def verify(self, plain_password, hashed_password):
        return hashed_password == f"hashed_{plain_password}"

    def hash(self, password):
        return f"hashed_{password}"

mock_passlib = MagicMock()
mock_passlib.context = MagicMock()
mock_passlib.context.CryptContext = MockCryptContext
sys.modules['passlib'] = mock_passlib
sys.modules['passlib.context'] = mock_passlib.context
