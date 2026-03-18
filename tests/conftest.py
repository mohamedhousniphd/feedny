import sys
from unittest.mock import MagicMock

# MOCK SECTION: Pre-emptively mock heavy/binary dependencies for testing environments
# This allows running tests even if these specialized libraries aren't installed.
mock_modules = [
    'wordcloud', 'matplotlib', 'matplotlib.pyplot',
    'stopwordsiso', 'pandas', 'httpx', 'reportlab', 'reportlab.pdfgen', 'reportlab.lib',
    'reportlab.lib.pagesizes', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts',
    'Pillow', 'resend', 'arabic_reshaper', 'bidi', 'bidi.algorithm', 'jose'
]

for mod in mock_modules:
    try:
        __import__(mod)
    except ImportError:
        sys.modules[mod] = MagicMock()

# Special handling for stopwordsiso mocking if needed by specific tests
if 'stopwordsiso' in sys.modules and isinstance(sys.modules['stopwordsiso'], MagicMock):
    def stopwords_mock(lang):
        return [] # Return empty list by default for mocks
    sys.modules['stopwordsiso'].stopwords = stopwords_mock

# Special handling for matplotlib.use
if 'matplotlib' in sys.modules and isinstance(sys.modules['matplotlib'], MagicMock):
    sys.modules['matplotlib'].use = MagicMock()

# Mock passlib if missing
try:
    import passlib
except ImportError:
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
