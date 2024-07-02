import io
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, 'fonts', 'dejavusans.ttf')

pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))


def create_pdf(ingredients):
    """Создать pdf file."""
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName='DejaVuSans',
        fontSize=24,
        textColor=colors.black,
        alignment=1,
        spaceAfter=20
    )
    title = Paragraph("Список покупок", title_style)

    normal_dejavusans_style = ParagraphStyle(
        'NormalDejaVuSans',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=12,
        textColor=colors.black
    )

    ingredients_list = []
    for ingredient in ingredients:
        line = (f"{ingredient['name']} - "
                f"{ingredient['measurement_unit']} - "
                f"{ingredient['total_amount']}")
        ingredients_list.append(Paragraph(line, normal_dejavusans_style))

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=10,
        textColor=colors.gray,
        alignment=1,
        spaceBefore=20
    )
    footer = Paragraph('ООО "Foodgram Corporation" 2024г', footer_style)

    elements = [title, Spacer(1, 12)] + ingredients_list + [Spacer(1, 20), footer]

    doc.build(elements)
    pdf_buffer.seek(0)

    return pdf_buffer
