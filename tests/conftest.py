import sys
from unittest.mock import Mock

# Pre-emptively mock missing dependencies before any app code is imported
mock_modules = [
    'wordcloud', 'matplotlib', 'matplotlib.pyplot',
    'stopwordsiso', 'pandas', 'httpx', 'reportlab', 'reportlab.pdfgen', 'reportlab.lib',
    'reportlab.lib.pagesizes', 'reportlab.pdfbase', 'reportlab.pdfbase.ttfonts',
    'Pillow', 'resend', 'arabic_reshaper', 'bidi', 'bidi.algorithm'
]

for mod in mock_modules:
    sys.modules[mod] = Mock()
