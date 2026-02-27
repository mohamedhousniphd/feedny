import os
import io
import base64
import re
from typing import Optional
from stopwordsiso import stopwords
from wordcloud import WordCloud
import matplotlib
import matplotlib.pyplot as plt
import urllib.request
import arabic_reshaper
from bidi.algorithm import get_display


# Set backend to Agg to avoid display issues
matplotlib.use('Agg')


def detect_has_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
    return bool(arabic_pattern.search(text))


def process_arabic_word(word: str) -> str:
    """Correctly shape and order Arabic words for display in PIL."""
    if detect_has_arabic(word):
        # Specific configuration tailored for basic WordCloud use
        reshaper_config = {
            'delete_harakat': True,
            'delete_tatweel': True,
            'support_ligatures': True,
            'shift_harakat_position': False
        }
        reshaped = arabic_reshaper.ArabicReshaper(configuration=reshaper_config).reshape(word)
        return get_display(reshaped)
    return word


def get_multilingual_stopwords() -> set[str]:
    """Get combined stopwords for French, English, and Arabic."""
    combined_stopwords = set()
    
    # Add French stopwords
    try:
        combined_stopwords.update(stopwords('fr'))
    except Exception:
        combined_stopwords.update([
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
            'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles', 'je', 'tu',
            'et', 'ou', 'or', 'mais', 'où', 'dont', 'que', 'qui',
            'en', 'pour', 'avec', 'sur', 'dans', 'par', 'chez', 'sans',
            'être', 'avoir', 'ce', 'cette', 'ces', 'cela', 'ça',
            'très', 'plus', 'moins', 'bien', 'mal', 'non', 'oui', 'si',
            'tout', 'tous', 'toute', 'toutes'
        ])
    
    # Add English stopwords
    try:
        combined_stopwords.update(stopwords('en'))
    except Exception:
        combined_stopwords.update([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'this', 'that', 'these', 'those', 'it', 'its', 'i', 'you', 'he',
            'she', 'we', 'they', 'my', 'your', 'his', 'her', 'our', 'their',
            'very', 'more', 'most', 'some', 'any', 'no', 'not', 'only', 'just'
        ])
    
    # Add Arabic stopwords
    try:
        combined_stopwords.update(stopwords('ar'))
    except Exception:
        combined_stopwords.update([
            'من', 'إلى', 'على', 'في', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'تلك',
            'التي', 'الذي', 'الذين', 'هو', 'هي', 'هم', 'أنا', 'نحن', 'أنت', 'أنتم',
            'كان', 'كانت', 'يكون', 'تكون', 'أن', 'إن', 'لا', 'ما', 'لم', 'لن',
            'و', 'أو', 'ثم', 'بل', 'لكن', 'حتى', 'إذا', 'كل', 'بعض', 'غير',
            'قد', 'عند', 'بين', 'فوق', 'تحت', 'أمام', 'وراء', 'قبل', 'بعد'
        ])
    
    return combined_stopwords


def get_french_stopwords() -> set[str]:
    """Get French stopwords for filtering (kept for backward compatibility)."""
    return get_multilingual_stopwords()


def find_multilingual_font() -> Optional[str]:
    """Find a font that supports Arabic + Latin characters or download a solid fallback."""
    # Search common font directories native to system
    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/System/Library/Fonts",           # macOS
        "/Library/Fonts",                   # macOS
        os.path.expanduser("~/Library/Fonts"),  # macOS user
        os.path.expanduser("~/.local/share/fonts"), 
        "/app/data/fonts"                   # Docker fallback directory
    ]
    
    # Fonts known to support both Arabic and extended Latin well
    target_fonts = ["tajawal", "cairo", "dejavu", "notosans-regular", "notosansarabic"]
    
    for font_dir in font_dirs:
        if not os.path.isdir(font_dir):
            continue
        for root, dirs, files in os.walk(font_dir):
            for f in files:
                f_lower = f.lower()
                if f.endswith(('.ttf', '.otf')) and any(t in f_lower for t in target_fonts):
                    return os.path.join(root, f)

    # If we get here, no good multilingual font found. Let's auto-download Tajawal-Regular
    print("No native multilingual font found. Downloading Tajawal-Regular...")
    try:
        font_dir = "/app/data/fonts"
        if not os.path.exists(font_dir):
            os.makedirs(font_dir, exist_ok=True)
            
        font_path = os.path.join(font_dir, "Tajawal-Regular.ttf")
        if not os.path.exists(font_path):
            tajawal_url = "https://github.com/googlefonts/tajawal/raw/master/fonts/ttf/Tajawal-Regular.ttf"
            urllib.request.urlretrieve(tajawal_url, font_path)
            print("Successfully downloaded Tajawal-Regular.ttf")
        return font_path
    except Exception as e:
        print(f"Failed to download fallback font: {e}")
        return None


# Cache the font path at module load
_FONT_PATH = find_multilingual_font()
if _FONT_PATH:
    print(f"Wordcloud font: {_FONT_PATH}")
else:
    print("Warning: No multilingual font found, Arabic may render as squares")


def create_wordcloud(
    text: str,
    width: int = 800,
    height: int = 400,
    max_words: int = 100,
    prefer_horizontal: float = 0.9,
    colormap: str = 'tab20'
) -> tuple[Optional[str], dict]:
    """
    Create a wordcloud from text with multi-language support (French, English, Arabic).

    Returns:
        Tuple of (base64_encoded_image, word_frequencies_dict)
    """
    if not text or not text.strip():
        return None, {}

    try:
        # Get multi-language stopwords
        stopwords_set = get_multilingual_stopwords()

        # Construct regex dynamically to safely extract words
        arabic_range = f"{chr(0x0600)}-{chr(0x06FF)}{chr(0x0750)}-{chr(0x077F)}{chr(0x08A0)}-{chr(0x08FF)}"
        regex_pattern = f"[\\w{arabic_range}']+"

        # Instead of directly feeding text, we process the text using WordCloud's default logic
        # to extract words and frequencies.
        wc_base = WordCloud(
            stopwords=stopwords_set,
            regexp=regex_pattern,
            collocations=False
        )
        base_frequencies = wc_base.process_text(text)
        
        # Now we reshape/bidi only the extracted words, which handles right-to-left layout correctly
        # and translates raw Arabic chars into presentation forms supported by the font.
        reshaped_frequencies = {}
        for word, freq in base_frequencies.items():
            reshaped_word = process_arabic_word(word)
            reshaped_frequencies[reshaped_word] = freq

        # Create wordcloud with reshaped frequencies
        wordcloud = WordCloud(
            width=width,
            height=height,
            background_color='white',
            max_words=max_words,
            colormap=colormap,
            prefer_horizontal=prefer_horizontal,
            relative_scaling=0.5,
            min_font_size=10,
            random_state=42,
            font_path=_FONT_PATH
        ).generate_from_frequencies(reshaped_frequencies)

        # Get word frequencies back (optional, but requested by API)
        word_frequencies = wordcloud.words_

        # Convert to base64 image
        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('Nuage de mots', fontsize=14, pad=20, color='black')

        # Save to buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight', facecolor='white', dpi=100)
        buffer.seek(0)
        plt.close(fig)

        # Encode to base64
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        return image_base64, word_frequencies

    except Exception as e:
        print(f"Error creating wordcloud: {e}")
        return None, {}


def get_top_words(text: str, n: int = 10) -> list[tuple[str, float]]:
    """
    Get top N words from text with their frequencies.

    Returns:
        List of (word, frequency) tuples
    """
    _, word_frequencies = create_wordcloud(text)
    return sorted(word_frequencies.items(), key=lambda x: x[1], reverse=True)[:n]
