import io
import base64
import re
from typing import Optional
from stopwordsiso import stopwords
from wordcloud import WordCloud
import matplotlib
import matplotlib.pyplot as plt


# Set backend to Agg to avoid display issues
matplotlib.use('Agg')


def detect_has_arabic(text: str) -> bool:
    """Check if text contains Arabic characters."""
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
    return bool(arabic_pattern.search(text))


def wrap_arabic_words(text: str) -> str:
    """
    Wrap Arabic words with Unicode RTL control characters for proper display.
    Uses Right-to-Left Isolate (U+2067) and Pop Directional Isolate (U+2069).
    """
    arabic_pattern = re.compile(r'([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+)')
    # Use chr() to safely embed unicode control characters
    return arabic_pattern.sub(f"{chr(0x2067)}\\1{chr(0x2069)}", text)


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
    """Find a font that supports Arabic + Latin characters."""
    import subprocess
    
    # Priority list of fonts that support Arabic
    font_names = [
        "NotoSansArabic",
        "NotoSans-Regular",
        "Noto Sans",
        "DejaVu Sans",
    ]
    
    # Search common font directories
    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/System/Library/Fonts",           # macOS
        "/Library/Fonts",                   # macOS
        os.path.expanduser("~/Library/Fonts"),  # macOS user
    ]
    
    for font_dir in font_dirs:
        if not os.path.isdir(font_dir):
            continue
        for root, dirs, files in os.walk(font_dir):
            for f in files:
                if f.endswith(('.ttf', '.otf')):
                    f_lower = f.lower()
                    # Prefer Noto Sans Arabic specifically
                    if 'notosansarabic' in f_lower and 'regular' in f_lower:
                        return os.path.join(root, f)
    
    # Fallback: any Noto Sans font
    for font_dir in font_dirs:
        if not os.path.isdir(font_dir):
            continue
        for root, dirs, files in os.walk(font_dir):
            for f in files:
                if f.endswith(('.ttf', '.otf')):
                    f_lower = f.lower()
                    if 'notosans' in f_lower and 'regular' in f_lower:
                        return os.path.join(root, f)
    
    # Final fallback: DejaVu Sans (partial Arabic support)
    for font_dir in font_dirs:
        if not os.path.isdir(font_dir):
            continue
        for root, dirs, files in os.walk(font_dir):
            for f in files:
                if f.endswith('.ttf') and 'dejavu' in f.lower() and 'sans' in f.lower():
                    return os.path.join(root, f)
    
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
        
        # Process Arabic text for RTL display
        processed_text = text
        if detect_has_arabic(text):
            processed_text = wrap_arabic_words(text)

        # Construct regex dynamically to avoid source encoding issues
        # Arabic range: 0600-06FF, 0750-077F, 08A0-08FF
        arabic_range = f"{chr(0x0600)}-{chr(0x06FF)}{chr(0x0750)}-{chr(0x077F)}{chr(0x08A0)}-{chr(0x08FF)}"
        regex_pattern = f"[\\w{arabic_range}']+"

        # Create wordcloud with multi-language support
        wordcloud = WordCloud(
            width=width,
            height=height,
            background_color='white',
            max_words=max_words,
            stopwords=stopwords_set,
            colormap=colormap,
            prefer_horizontal=prefer_horizontal,
            relative_scaling=0.5,
            min_font_size=10,
            random_state=42,
            font_path=_FONT_PATH,
            regexp=regex_pattern
        ).generate(processed_text)

        # Get word frequencies
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
