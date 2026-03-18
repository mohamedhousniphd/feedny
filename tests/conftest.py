import sys
from unittest.mock import MagicMock

# Only mock if the modules are actually missing from the environment
try:
    import stopwordsiso
except ImportError:
    mock_stopwordsiso = MagicMock()
    def stopwords_mock(lang):
        raise Exception("Mock fallback")
    mock_stopwordsiso.stopwords = stopwords_mock
    sys.modules['stopwordsiso'] = mock_stopwordsiso

try:
    import wordcloud
except ImportError:
    sys.modules['wordcloud'] = MagicMock()

try:
    import matplotlib
except ImportError:
    sys.modules['matplotlib'] = MagicMock()
    sys.modules['matplotlib.pyplot'] = MagicMock()

try:
    import arabic_reshaper
except ImportError:
    sys.modules['arabic_reshaper'] = MagicMock()

try:
    import bidi
except ImportError:
    sys.modules['bidi'] = MagicMock()
    sys.modules['bidi.algorithm'] = MagicMock()
