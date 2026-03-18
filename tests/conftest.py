import sys
from unittest.mock import MagicMock

# Mock out modules that might not be installed in the test environment
sys.modules['stopwordsiso'] = MagicMock()
sys.modules['wordcloud'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['arabic_reshaper'] = MagicMock()
sys.modules['bidi'] = MagicMock()
sys.modules['bidi.algorithm'] = MagicMock()
