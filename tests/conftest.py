import sys
from unittest.mock import MagicMock

class MockStopwords:
    def __call__(self, lang):
        if lang == 'fr':
            return {'le', 'la'}
        elif lang == 'en':
            return {'the', 'and'}
        elif lang == 'ar':
            return {'من', 'إلى'}
        return set()

sys.modules['stopwordsiso'] = MagicMock()
sys.modules['stopwordsiso'].stopwords = MockStopwords()
sys.modules['wordcloud'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['bidi'] = MagicMock()

def mock_get_display(text):
    return "reshaped_" + str(text)

mock_bidi_algorithm = MagicMock()
mock_bidi_algorithm.get_display = mock_get_display
sys.modules['bidi.algorithm'] = mock_bidi_algorithm

class MockReshaperInstance:
    def reshape(self, text):
        return text + "_reshaped"

class MockArabicReshaper:
    def ArabicReshaper(self, configuration=None):
        return MockReshaperInstance()

sys.modules['arabic_reshaper'] = MockArabicReshaper()
