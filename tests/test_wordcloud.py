import pytest
import os
from unittest.mock import patch, MagicMock

# The module under test
from app.services.wordcloud import (
    detect_has_arabic,
    process_arabic_word,
    get_multilingual_stopwords,
    get_french_stopwords,
    find_multilingual_font,
    create_wordcloud,
    get_top_words
)

def test_detect_has_arabic():
    # True cases
    assert detect_has_arabic("مرحبا") is True
    assert detect_has_arabic("hello مرحبا") is True
    assert detect_has_arabic("م") is True

    # False cases
    assert detect_has_arabic("hello") is False
    assert detect_has_arabic("1234") is False
    assert detect_has_arabic("!@#$") is False
    assert detect_has_arabic("") is False

@patch('app.services.wordcloud.arabic_reshaper.ArabicReshaper')
@patch('app.services.wordcloud.get_display')
def test_process_arabic_word(mock_get_display, mock_reshaper_class):
    mock_reshaper_instance = MagicMock()
    mock_reshaper_class.return_value = mock_reshaper_instance

    mock_reshaper_instance.reshape.return_value = "reshaped_arabic"
    mock_get_display.return_value = "displayed_arabic"

    # Arabic word
    result = process_arabic_word("مرحبا")
    assert result == "displayed_arabic"
    mock_reshaper_class.assert_called_once()
    mock_reshaper_instance.reshape.assert_called_with("مرحبا")
    mock_get_display.assert_called_with("reshaped_arabic")

    # Non-Arabic word should be returned as is
    mock_reshaper_class.reset_mock()
    mock_get_display.reset_mock()
    result = process_arabic_word("hello")
    assert result == "hello"
    mock_reshaper_class.assert_not_called()
    mock_get_display.assert_not_called()

def test_get_multilingual_stopwords():
    # conftest mocks the stopwords package to throw exception so this tests the fallback
    stopwords = get_multilingual_stopwords()

    # Check if some French words are in
    assert 'le' in stopwords
    assert 'la' in stopwords

    # Check if some English words are in
    assert 'the' in stopwords
    assert 'a' in stopwords

    # Check if some Arabic words are in
    assert 'من' in stopwords
    assert 'إلى' in stopwords

def test_get_french_stopwords():
    stopwords1 = get_multilingual_stopwords()
    stopwords2 = get_french_stopwords()
    assert stopwords1 == stopwords2

@patch('os.path.exists')
def test_find_multilingual_font_primary(mock_exists):
    mock_exists.return_value = True
    font_path = find_multilingual_font()
    assert font_path is not None
    assert font_path.endswith("Tajawal-Regular.ttf")

@patch('os.path.exists')
@patch('os.path.isdir')
@patch('os.walk')
def test_find_multilingual_font_fallback(mock_walk, mock_isdir, mock_exists):
    # Mock primary font does not exist
    mock_exists.return_value = False

    # Mock font dirs exist
    mock_isdir.return_value = True

    # Mock os.walk to find a tajawal font
    mock_walk.return_value = [
        ("/usr/share/fonts/truetype", [], ["tajawal-regular.ttf"])
    ]

    font_path = find_multilingual_font()
    assert font_path == "/usr/share/fonts/truetype/tajawal-regular.ttf"

@patch('os.path.exists')
@patch('os.path.isdir')
def test_find_multilingual_font_none(mock_isdir, mock_exists):
    mock_exists.return_value = False
    mock_isdir.return_value = False

    font_path = find_multilingual_font()
    assert font_path is None

@patch('app.services.wordcloud.WordCloud')
@patch('app.services.wordcloud.plt')
def test_create_wordcloud_empty_text(mock_plt, mock_wordcloud):
    img, freqs = create_wordcloud("")
    assert img is None
    assert freqs == {}

    img, freqs = create_wordcloud("   ")
    assert img is None
    assert freqs == {}

@patch('app.services.wordcloud.WordCloud')
@patch('app.services.wordcloud.plt')
def test_create_wordcloud_success(mock_plt, mock_wordcloud):
    # Setup mocks
    mock_wc_base = MagicMock()
    mock_wc_final = MagicMock()

    # WordCloud() returns different objects based on call order
    mock_wordcloud.side_effect = [mock_wc_base, mock_wc_final]

    mock_wc_base.process_text.return_value = {"word1": 10, "word2": 5}
    mock_wc_final.generate_from_frequencies.return_value = mock_wc_final
    mock_wc_final.words_ = {"word1": 10, "word2": 5}

    # Mock plt functions
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    # Mock io.BytesIO indirectly by patching it or just let the real one run
    # Let's just patch plt.savefig to write something to the buffer
    def mock_savefig(buffer, *args, **kwargs):
        buffer.write(b"fake image data")

    mock_plt.savefig.side_effect = mock_savefig

    img, freqs = create_wordcloud("word1 word2")

    assert img is not None
    # Base64 of "fake image data"
    assert img == "ZmFrZSBpbWFnZSBkYXRh"
    assert freqs == {"word1": 10, "word2": 5}

    # Verify processing
    mock_wc_base.process_text.assert_called_with("word1 word2")
    mock_wc_final.generate_from_frequencies.assert_called_once()

@patch('app.services.wordcloud.create_wordcloud')
def test_get_top_words(mock_create):
    mock_create.return_value = ("img", {"apple": 5, "banana": 10, "orange": 2})

    top = get_top_words("text", 2)

    assert len(top) == 2
    assert top[0] == ("banana", 10)
    assert top[1] == ("apple", 5)

@patch('app.services.wordcloud.WordCloud')
def test_create_wordcloud_exception(mock_wordcloud):
    mock_wordcloud.side_effect = Exception("Test error")

    img, freqs = create_wordcloud("test text")

    assert img is None
    assert freqs == {}
