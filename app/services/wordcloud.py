import io
import base64
from typing import Optional
from stopwordsiso import stopwords
from wordcloud import WordCloud
import matplotlib
import matplotlib.pyplot as plt


# Set backend to Agg to avoid display issues
matplotlib.use('Agg')


def get_french_stopwords() -> set[str]:
    """Get French stopwords for filtering."""
    try:
        return set(stopwords('fr'))
    except Exception:
        # Fallback to hardcoded list if stopwordsiso fails
        return set([
            # Articles
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'au', 'aux',
            # Pronouns
            'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles', 'je', 'tu',
            # Prepositions & Conjunctions
            'et', 'ou', 'or', 'mais', 'où', 'dont', 'que', 'qui', 'qu\'',
            'l\'', 'd\'', 'n\'', 's\'', 'j\'', 'c\'', 't\'', 'm\'',
            'en', 'pour', 'avec', 'sur', 'dans', 'par', 'chez', 'sans',
            # Auxiliary verbs
            'être', 'avoir', 'ai', 'as', 'a', 'avons', 'avez', 'ont',
            'suis', 'es', 'est', 'sommes', 'êtes', 'sont', 'été',
            # Common verbs
            'faire', 'dire', 'aller', 'voir', 'savoir', 'pouvoir', 'vouloir',
            # Demonstratives
            'ce', 'cet', 'cette', 'ces', 'cela', 'ça',
            # Possessives
            'son', 'sa', 'ses', 'mon', 'ma', 'mes', 'notre', 'nos',
            'votre', 'vos', 'leur', 'leurs',
            # Others
            'très', 'plus', 'moins', 'bien', 'mal', 'non', 'oui', 'si',
            'tout', 'tous', 'toute', 'toutes', 'aucun', 'aucune',
            'autre', 'autres', 'même', 'mémes', 'tel', 'tels', 'telle', 'telles',
            'chaque', 'certains', 'certaines', 'quelque', 'quelques'
        ])


def create_wordcloud(
    text: str,
    width: int = 800,
    height: int = 400,
    max_words: int = 100,
    prefer_horizontal: float = 0.9,
    colormap: str = 'tab20'
) -> tuple[Optional[str], dict]:
    """
    Create a wordcloud from text.

    Returns:
        Tuple of (base64_encoded_image, word_frequencies_dict)
    """
    if not text or not text.strip():
        return None, {}

    try:
        # Get French stopwords
        french_stopwords = get_french_stopwords()

        # Create wordcloud
        wordcloud = WordCloud(
            width=width,
            height=height,
            background_color='white',  # Light theme
            stopwords=french_stopwords,
            colormap=colormap,
            max_words=max_words,
            prefer_horizontal=prefer_horizontal,
            relative_scaling=0.5,
            min_font_size=10,
            random_state=42
        ).generate(text)

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
