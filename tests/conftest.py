import sys
from unittest.mock import MagicMock

# Mock out modules that aren't available in the test environment
mock_modules = [
    'stopwordsiso',
    'wordcloud',
    'matplotlib',
    'matplotlib.pyplot',
    'arabic_reshaper',
    'bidi',
    'bidi.algorithm'
]

for mod in mock_modules:
    sys.modules[mod] = MagicMock()

# Configure specific mocks if needed
sys.modules['matplotlib'].use = MagicMock()
