import pytest
from unittest.mock import patch, MagicMock
from app.services.wordcloud import detect_has_arabic, process_arabic_word, get_multilingual_stopwords, get_french_stopwords, find_multilingual_font, create_wordcloud, get_top_words

def test_detect_has_arabic():
    # Simple cases
    assert detect_has_arabic("مرحبا") == True
    assert detect_has_arabic("Hello") == False

    # Mixed cases
    assert detect_has_arabic("مرحبا Hello") == True
    assert detect_has_arabic("Hello مرحبا") == True

    # Other languages/scripts
    assert detect_has_arabic("Bonjour") == False
    assert detect_has_arabic("こんにちは") == False

    # Empty/numbers
    assert detect_has_arabic("") == False
    assert detect_has_arabic("12345") == False
    assert detect_has_arabic("!?@#") == False

@patch('app.services.wordcloud.detect_has_arabic')
@patch('app.services.wordcloud.arabic_reshaper.ArabicReshaper')
@patch('app.services.wordcloud.get_display')
def test_process_arabic_word(mock_get_display, mock_arabic_reshaper, mock_detect_has_arabic):
    # Setup mock
    mock_detect_has_arabic.return_value = True
    mock_reshaper_instance = mock_arabic_reshaper.return_value
    mock_reshaper_instance.reshape.return_value = "reshaped_word"
    mock_get_display.return_value = "displayed_word"

    result = process_arabic_word("مرحبا")

    assert result == "displayed_word"
    mock_detect_has_arabic.assert_called_once_with("مرحبا")
    mock_arabic_reshaper.assert_called_once_with(configuration={
        'delete_harakat': True,
        'delete_tatweel': True,
        'support_ligatures': True,
        'shift_harakat_position': False
    })
    mock_reshaper_instance.reshape.assert_called_once_with("مرحبا")
    mock_get_display.assert_called_once_with("reshaped_word")

def test_process_arabic_word_no_arabic():
    # Setup mock
    with patch('app.services.wordcloud.detect_has_arabic', return_value=False) as mock_detect_has_arabic:
        result = process_arabic_word("Hello")

        assert result == "Hello"
        mock_detect_has_arabic.assert_called_once_with("Hello")

@patch('app.services.wordcloud.stopwords')
def test_get_multilingual_stopwords(mock_stopwords):
    # Define what the mock should return for different languages
    def stopwords_side_effect(lang):
        if lang == 'fr':
            return {'le', 'la'}
        elif lang == 'en':
            return {'the', 'a'}
        elif lang == 'ar':
            return {'في', 'من'}
        raise Exception("Unknown language")

    mock_stopwords.side_effect = stopwords_side_effect

    stopwords_set = get_multilingual_stopwords()

    assert 'le' in stopwords_set
    assert 'la' in stopwords_set
    assert 'the' in stopwords_set
    assert 'a' in stopwords_set
    assert 'في' in stopwords_set
    assert 'من' in stopwords_set

@patch('app.services.wordcloud.stopwords')
def test_get_multilingual_stopwords_exception_fallback(mock_stopwords):
    # Simulate the module throwing an exception to test the fallback block
    mock_stopwords.side_effect = Exception("Test Exception")

    stopwords_set = get_multilingual_stopwords()

    # Check that fallback stopwords are loaded
    assert 'le' in stopwords_set
    assert 'the' in stopwords_set
    assert 'من' in stopwords_set

def test_get_french_stopwords():
    with patch('app.services.wordcloud.get_multilingual_stopwords', return_value={'le', 'la'}) as mock_multilingual:
        result = get_french_stopwords()
        assert result == {'le', 'la'}
        mock_multilingual.assert_called_once()

@patch('app.services.wordcloud.os.path.exists')
def test_find_multilingual_font_bundled(mock_exists):
    # Simulate the bundled font existing
    mock_exists.return_value = True

    font_path = find_multilingual_font()
    assert font_path is not None
    assert "Tajawal-Regular.ttf" in font_path

@patch('app.services.wordcloud.os.path.exists')
@patch('app.services.wordcloud.os.path.isdir')
@patch('app.services.wordcloud.os.walk')
def test_find_multilingual_font_system(mock_walk, mock_isdir, mock_exists):
    # Simulate the bundled font not existing
    mock_exists.return_value = False

    # Simulate a font directory existing
    mock_isdir.return_value = True

    # Mock os.walk to return a matching font
    mock_walk.return_value = [
        ('/usr/share/fonts', ('truetype',), ('cairo-regular.ttf', 'otherfont.ttf'))
    ]

    font_path = find_multilingual_font()
    assert font_path is not None
    assert "cairo-regular.ttf" in font_path

@patch('app.services.wordcloud.os.path.exists')
@patch('app.services.wordcloud.os.path.isdir')
def test_find_multilingual_font_not_found(mock_isdir, mock_exists):
    # Simulate the bundled font not existing
    mock_exists.return_value = False

    # Simulate no font directories existing
    mock_isdir.return_value = False

    font_path = find_multilingual_font()
    assert font_path is None

@patch('app.services.wordcloud.WordCloud')
@patch('app.services.wordcloud.plt')
def test_create_wordcloud_empty_text(mock_plt, mock_wordcloud):
    image_base64, word_frequencies = create_wordcloud("")
    assert image_base64 is None
    assert word_frequencies == {}

    image_base64, word_frequencies = create_wordcloud("   \n  ")
    assert image_base64 is None
    assert word_frequencies == {}

@patch('app.services.wordcloud.WordCloud')
@patch('app.services.wordcloud.plt')
def test_create_wordcloud_success(mock_plt, mock_wordcloud):
    # Setup mocks
    mock_wc_instance = mock_wordcloud.return_value
    mock_wc_instance.process_text.return_value = {'word1': 2, 'word2': 1}
    mock_wc_instance.generate_from_frequencies.return_value = mock_wc_instance
    mock_wc_instance.words_ = {'word1': 0.66, 'word2': 0.33}

    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, mock_ax)

    image_base64, word_frequencies = create_wordcloud("word1 word1 word2")

    assert image_base64 is not None
    assert word_frequencies == {'word1': 0.66, 'word2': 0.33}

    # Check that it tried to generate plot
    mock_plt.subplots.assert_called_once()
    mock_ax.imshow.assert_called_once()
    mock_plt.savefig.assert_called_once()
    mock_plt.close.assert_called_once()

@patch('app.services.wordcloud.WordCloud')
def test_create_wordcloud_exception(mock_wordcloud):
    # Make WordCloud raise an exception
    mock_wordcloud.side_effect = Exception("Test Error")

    image_base64, word_frequencies = create_wordcloud("word1 word2")

    assert image_base64 is None
    assert word_frequencies == {}

@patch('app.services.wordcloud.create_wordcloud')
def test_get_top_words(mock_create_wordcloud):
    mock_create_wordcloud.return_value = ("base64_data", {'word1': 0.8, 'word2': 0.5, 'word3': 0.2})

    top_words = get_top_words("text doesn't matter here", n=2)

    assert len(top_words) == 2
    assert top_words[0] == ('word1', 0.8)
    assert top_words[1] == ('word2', 0.5)
