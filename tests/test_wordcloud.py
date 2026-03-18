import pytest
from app.services.wordcloud import (
    detect_has_arabic,
    process_arabic_word,
    get_multilingual_stopwords,
    get_french_stopwords,
    find_multilingual_font,
)
import os
from unittest.mock import patch, MagicMock

def test_detect_has_arabic():
    # Test text containing Arabic
    assert detect_has_arabic("مرحبا") is True
    assert detect_has_arabic("Hello مرحبا") is True
    assert detect_has_arabic("Bonjour العالم") is True

    # Test text without Arabic
    assert detect_has_arabic("Hello world") is False
    assert detect_has_arabic("12345") is False
    assert detect_has_arabic("!@#$%^&*()") is False
    assert detect_has_arabic("") is False

def test_process_arabic_word():
    # Test English/French text (should remain unchanged)
    assert process_arabic_word("Hello") == "Hello"
    assert process_arabic_word("Bonjour") == "Bonjour"

    # Test Arabic text (should be reshaped and bidi-processed)
    arabic_word = "مرحبا"
    processed = process_arabic_word(arabic_word)
    # The processed word should be different from the original (or same if single char, but for "مرحبا" it will be different)
    assert processed != arabic_word
    assert len(processed) > 0

def test_get_multilingual_stopwords():
    stopwords_set = get_multilingual_stopwords()

    # Should contain French stopwords
    assert 'le' in stopwords_set
    assert 'la' in stopwords_set

    # Should contain English stopwords
    assert 'the' in stopwords_set
    assert 'and' in stopwords_set

    # Should contain Arabic stopwords
    assert 'من' in stopwords_set
    assert 'إلى' in stopwords_set

def test_get_french_stopwords():
    stopwords_set = get_french_stopwords()
    assert 'le' in stopwords_set
    assert 'the' in stopwords_set # Since it's an alias to get_multilingual_stopwords

def test_find_multilingual_font():
    font_path = find_multilingual_font()
    if font_path is not None:
        assert isinstance(font_path, str)
        assert os.path.exists(font_path)

from app.services.wordcloud import create_wordcloud, get_top_words

def test_create_wordcloud_empty_text():
    base64_img, freqs = create_wordcloud("")
    assert base64_img is None
    assert freqs == {}

    base64_img, freqs = create_wordcloud("   ")
    assert base64_img is None
    assert freqs == {}

@patch('app.services.wordcloud.WordCloud')
@patch('app.services.wordcloud.plt')
def test_create_wordcloud_success(mock_plt, mock_wc_class):
    # Mock WordCloud behavior
    mock_wc_instance = MagicMock()
    mock_wc_instance.process_text.return_value = {'hello': 2, 'world': 1}
    mock_wc_instance.generate_from_frequencies.return_value = mock_wc_instance
    mock_wc_instance.words_ = {'hello': 0.6, 'world': 0.3}

    mock_wc_class.return_value = mock_wc_instance

    # Mock plt.subplots and plt.savefig
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    def mock_savefig(buffer, **kwargs):
        buffer.write(b"fake_image_data")

    mock_plt.savefig.side_effect = mock_savefig

    # Run function
    base64_img, freqs = create_wordcloud("hello hello world")

    # Assertions
    assert base64_img == "ZmFrZV9pbWFnZV9kYXRh"  # base64 for "fake_image_data"
    assert freqs == {'hello': 0.6, 'world': 0.3}
    mock_wc_class.assert_called()
    mock_plt.savefig.assert_called_once()
    mock_plt.close.assert_called_once_with(mock_fig)

@patch('app.services.wordcloud.create_wordcloud')
def test_get_top_words(mock_create_wordcloud):
    mock_create_wordcloud.return_value = ("fake_base64", {'hello': 2.0, 'world': 1.0, 'test': 3.0})

    # Test top 2 words
    top_words = get_top_words("text", n=2)

    assert len(top_words) == 2
    assert top_words[0] == ('test', 3.0)
    assert top_words[1] == ('hello', 2.0)

@patch('app.services.wordcloud.WordCloud')
def test_create_wordcloud_exception(mock_wc_class):
    mock_wc_class.side_effect = Exception("Test Exception")

    base64_img, freqs = create_wordcloud("hello")

    assert base64_img is None
    assert freqs == {}
