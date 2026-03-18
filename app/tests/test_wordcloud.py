import pytest
import sys
from unittest.mock import patch, MagicMock

# Import dependencies safely. They might be mocked by conftest if missing.
from app.services.wordcloud import process_arabic_word

def test_process_arabic_word_empty_string():
    assert process_arabic_word("") == ""

def test_process_arabic_word_non_arabic():
    assert process_arabic_word("hello") == "hello"
    assert process_arabic_word("12345") == "12345"
    assert process_arabic_word("bonjour") == "bonjour"
    assert process_arabic_word("!@#$%") == "!@#$%"

@patch('app.services.wordcloud.arabic_reshaper.ArabicReshaper')
@patch('app.services.wordcloud.get_display')
def test_process_arabic_word_arabic(mock_get_display, mock_arabic_reshaper):
    word = "مرحبا"

    mock_reshaper_instance = MagicMock()
    mock_arabic_reshaper.return_value = mock_reshaper_instance
    mock_reshaper_instance.reshape.return_value = "reshaped_word"
    mock_get_display.return_value = "bidi_word"

    result = process_arabic_word(word)

    # Verify the config was passed correctly based on the actual source code
    mock_arabic_reshaper.assert_called_once_with(configuration={
        'delete_harakat': True,
        'delete_tatweel': True,
        'support_ligatures': True,
        'shift_harakat_position': False
    })

    mock_reshaper_instance.reshape.assert_called_once_with(word)
    mock_get_display.assert_called_once_with("reshaped_word")
    assert result == "bidi_word"

@patch('app.services.wordcloud.arabic_reshaper.ArabicReshaper')
@patch('app.services.wordcloud.get_display')
def test_process_arabic_word_mixed(mock_get_display, mock_arabic_reshaper):
    word = "helloمرحبا"

    mock_reshaper_instance = MagicMock()
    mock_arabic_reshaper.return_value = mock_reshaper_instance
    mock_reshaper_instance.reshape.return_value = "reshaped_word"
    mock_get_display.return_value = "bidi_word"

    result = process_arabic_word(word)

    mock_reshaper_instance.reshape.assert_called_once_with(word)
    mock_get_display.assert_called_once_with("reshaped_word")
    assert result == "bidi_word"
