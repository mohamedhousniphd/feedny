"""PDF Generation Service for Feedny Analysis Export."""

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
from PIL import Image as PILImage


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
    # Create PDF buffer
    buffer = io.BytesIO()
    
    # Use landscape A4
    page_width, page_height = landscape(A4)
    
    # Create document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1*cm,
        bottomMargin=1*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.gray,
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    context_style = ParagraphStyle(
        'ContextStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.darkgray,
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica-Oblique'
    )
    
    analysis_style = ParagraphStyle(
        'AnalysisStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        alignment=TA_JUSTIFY,
        leading=14,
        spaceBefore=5,
        spaceAfter=5
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.black,
        spaceBefore=10,
        spaceAfter=5
    )
    
    # Build content
    story = []
    
    # Title
    story.append(Paragraph(title, title_style))
    
    # Date
    date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
    story.append(Paragraph(f"Généré le {date_str}", date_style))
    
    # Context if provided
    if context:
        story.append(Paragraph(f"Contexte : {context}", context_style))
    
    story.append(Spacer(1, 10))
    
    # Process wordcloud image
    wordcloud_img = None
    if wordcloud_image_base64:
        try:
            img_data = base64.b64decode(wordcloud_image_base64)
            img_buffer = io.BytesIO(img_data)
            
            # Get image dimensions
            pil_img = PILImage.open(img_buffer)
            img_width, img_height = pil_img.size
            
            # Calculate scaling to fit nicely centered
            # Let's make it a sensible size (not taking whole page)
            max_img_width = page_width - 4*cm
            max_img_height = (page_height - 10*cm) / 2 # Take about half height at most
            
            scale_w = max_img_width / img_width
            scale_h = max_img_height / img_height
            scale = min(scale_w, scale_h, 1.0) # Don't upscale
            
            final_width = img_width * scale
            final_height = img_height * scale
            
            img_buffer.seek(0)
            wordcloud_img = Image(img_buffer, width=final_width, height=final_height)
            wordcloud_img.hAlign = 'CENTER'
        except Exception as e:
            print(f"Error processing wordcloud image: {e}")

    # Add Wordcloud section
    story.append(Paragraph("☁️ Nuage de Mots", section_heading))
    if wordcloud_img:
        story.append(wordcloud_img)
    else:
        story.append(Paragraph("(Image non disponible)", analysis_style))
    
    story.append(Spacer(1, 20))
    
    # Analysis Section
    story.append(Paragraph("📊 Analyse IA", section_heading))
    
    # Format analysis text - split by sections
    for line in analysis_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Check if it's a heading
        if any(line.startswith(f"{i}.") for i in range(1, 10)) or \
           any(keyword in line.lower() for keyword in ['résumé', 'points positifs', 'points à améliorer', 'recommandations']):
            story.append(Paragraph(line, section_heading))
        else:
            # Clean up markdown formatting
            line = line.replace('**', '').replace('*', '')
            story.append(Paragraph(line, analysis_style))

    
    # Build PDF
    doc.build(story)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
