import pytest
from unittest.mock import patch
from app.services.wordcloud import get_multilingual_stopwords

def test_get_multilingual_stopwords_happy_path():
    """Test get_multilingual_stopwords when stopwordsiso returns expected sets."""
    def mock_stopwords(lang):
        if lang == 'fr':
            return {'le', 'la'}
        elif lang == 'en':
            return {'the', 'a'}
        elif lang == 'ar':
            return {'من', 'إلى'}
        return set()

    with patch('app.services.wordcloud.stopwords', side_effect=mock_stopwords):
        stopwords = get_multilingual_stopwords()
        assert 'le' in stopwords
        assert 'la' in stopwords
        assert 'the' in stopwords
        assert 'a' in stopwords
        assert 'من' in stopwords
        assert 'إلى' in stopwords

def test_get_multilingual_stopwords_fallback_path():
    """Test get_multilingual_stopwords fallback paths when stopwordsiso raises an Exception."""
    def mock_stopwords_raise(lang):
        raise Exception(f"Mock exception for {lang}")

    with patch('app.services.wordcloud.stopwords', side_effect=mock_stopwords_raise):
        stopwords = get_multilingual_stopwords()
        # Check some French fallback words
        assert 'le' in stopwords
        assert 'la' in stopwords
        assert 'les' in stopwords
        # Check some English fallback words
        assert 'the' in stopwords
        assert 'a' in stopwords
        assert 'an' in stopwords
        # Check some Arabic fallback words
        assert 'من' in stopwords
        assert 'إلى' in stopwords
        assert 'على' in stopwords
