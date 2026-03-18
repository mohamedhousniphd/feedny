import os
import io
import base64
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

import arabic_reshaper
from bidi.algorithm import get_display
# --- Font Handling ---

def find_multilingual_font_path() -> Optional[str]:
    """Find the bundled Tajawal font or fallback to system fonts."""
    # 1. Primary: Bundled font
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bundled_font = os.path.join(base_dir, "static", "fonts", "Tajawal-Regular.ttf")
    if os.path.exists(bundled_font):
        return bundled_font

    # 2. Secondary: Search common font directories
    font_dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        "/System/Library/Fonts",
        "/Library/Fonts",
        os.path.expanduser("~/Library/Fonts"),
        "/app/data/fonts"
    ]
    target_fonts = ["tajawal", "cairo"]
    for target in target_fonts:
        for font_dir in font_dirs:
            if not os.path.isdir(font_dir): continue
            for root, _, files in os.walk(font_dir):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf')) and target in f.lower():
                        return os.path.join(root, f)
    return None

# Register font if found
_FONT_PATH = find_multilingual_font_path()
_FONT_NAME = "Helvetica" # Default fallback
if _FONT_PATH:
    try:
        pdfmetrics.registerFont(TTFont('Multilingual', _FONT_PATH))
        _FONT_NAME = 'Multilingual'
    except Exception as e:
        print(f"Error registering font: {e}")

def process_multilingual_text(text: str) -> str:
    """Shape Arabic text while preserving Latin text for ReportLab."""
    if not text: return ""
    
    # Check if contains Arabic
    if not any('\u0600' <= c <= '\u06FF' for c in text):
        return text
        
    reshaper_config = {
        'delete_harakat': False,
        'support_ligatures': True,
    }
    reshaper = arabic_reshaper.ArabicReshaper(configuration=reshaper_config)
    
    # Process line by line to preserve layout
    lines = text.split('\n')
    processed_lines = []
    for line in lines:
        if not line.strip():
            processed_lines.append(line)
            continue
        reshaped = reshaper.reshape(line)
        bidi_text = get_display(reshaped)
        processed_lines.append(bidi_text)
        
    return '\n'.join(processed_lines)

# --- PDF Generation Helpers ---

def _get_pdf_styles(font_name: str) -> dict:
    """Return a dictionary of standard PDF styles."""
    styles = getSampleStyleSheet()
    return {
        'title': ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=10,
            fontName=font_name
        ),
        'date': ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.gray,
            alignment=TA_CENTER,
            spaceAfter=5,
            fontName=font_name
        ),
        'context': ParagraphStyle(
            'ContextStyle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.darkgray,
            alignment=TA_CENTER,
            spaceAfter=15,
            fontName=font_name
        ),
        'analysis': ParagraphStyle(
            'AnalysisStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            alignment=TA_JUSTIFY,
            leading=14,
            spaceBefore=5,
            spaceAfter=5,
            fontName=font_name
        ),
        'section_heading': ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.black,
            spaceBefore=10,
            spaceAfter=5,
            fontName=font_name
        )
    }

def _create_wordcloud_image(image_base64: str, max_width: float, max_height: float) -> Optional[Image]:
    """Create a scaled ReportLab Image object from a base64 encoded string."""
    if not image_base64:
        return None

    try:
        img_data = base64.b64decode(image_base64)
        img_buffer = io.BytesIO(img_data)

        pil_img = PILImage.open(img_buffer)
        img_width, img_height = pil_img.size

        scale_w = max_width / img_width
        scale_h = max_height / img_height
        scale = min(scale_w, scale_h, 1.0)

        final_width = img_width * scale
        final_height = img_height * scale

        img_buffer.seek(0)
        wordcloud_img = Image(img_buffer, width=final_width, height=final_height)
        wordcloud_img.hAlign = 'CENTER'
        return wordcloud_img
    except Exception as e:
        print(f"Error processing wordcloud image: {e}")
        return None

def _create_analysis_elements(analysis_text: str, analysis_style: ParagraphStyle, section_heading: ParagraphStyle) -> list:
    """Parse analysis text and return a list of ReportLab Paragraph elements."""
    elements = []
    for line in analysis_text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if any(line.startswith(f"{i}.") for i in range(1, 10)) or \
           any(keyword in line.lower() for keyword in ['résumé', 'points positifs', 'points à améliorer', 'recommandations']):
            elements.append(Paragraph(process_multilingual_text(line), section_heading))
        else:
            line = line.replace('**', '').replace('*', '')
            elements.append(Paragraph(process_multilingual_text(line), analysis_style))

    return elements

# --- PDF Generation ---

def create_analysis_pdf(
    wordcloud_image_base64: str,
    analysis_text: str,
    context: str = "",
    title: str = "Feedny - Analyse des Feedbacks"
) -> bytes:
    """
    Create a PDF slide with wordcloud on left and analysis on right.
    
    Args:
        wordcloud_image_base64: Base64 encoded wordcloud image
        analysis_text: AI analysis text
        context: Optional context provided by teacher
        title: Document title
    
    Returns:
        PDF file as bytes
    """
    buffer = io.BytesIO()
    page_width, page_height = landscape(A4)
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    pdf_styles = _get_pdf_styles(_FONT_NAME)
    story = []
    
    # Title & Date
    story.append(Paragraph(process_multilingual_text(title), pdf_styles['title']))
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    story.append(Paragraph(process_multilingual_text(f"Généré le {date_str}"), pdf_styles['date']))
    
    if context:
        story.append(Paragraph(process_multilingual_text(f"Contexte : {context}"), pdf_styles['context']))
    
    story.append(Spacer(1, 10))
    
    # Wordcloud Section
    max_img_width = page_width - 4*cm
    max_img_height = (page_height - 10*cm) / 2
    wordcloud_img = _create_wordcloud_image(wordcloud_image_base64, max_img_width, max_img_height)

    story.append(Paragraph("☁️ Nuage de Mots", pdf_styles['section_heading']))
    if wordcloud_img:
        story.append(wordcloud_img)
    else:
        story.append(Paragraph("(Image non disponible)", pdf_styles['analysis']))
    
    story.append(Spacer(1, 20))
    
    # Analysis Section
    story.append(Paragraph(process_multilingual_text("📊 Analyse IA"), pdf_styles['section_heading']))
    story.extend(_create_analysis_elements(analysis_text, pdf_styles['analysis'], pdf_styles['section_heading']))
    
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
