from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import io

try:
    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    body_font = 'Arial'
except (KeyError, ValueError, OSError):
    body_font = 'Helvetica'


def create_pdf(ingredients):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName=body_font,
        fontSize=24,
        textColor=colors.darkblue,
        alignment=1,
        spaceAfter=20
    )
    title = Paragraph("Список покупок", title_style)

    data = [["Ингредиенты", "Ед. изм.", "Кол-во"]]
    for ingredient in ingredients:
        data.append([ingredient["name"], ingredient["measurement_unit"], str(ingredient["total_amount"])])

    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), body_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table = Table(data, colWidths=[200, 100, 100])
    table.setStyle(table_style)

    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=body_font,
        fontSize=10,
        textColor=colors.gray,
        alignment=1
    )
    footer = Paragraph('ООО "Foodgram Corporation" 2024г', footer_style)

    elements = [title, Spacer(1, 12), table, Spacer(1, 20), footer]

    doc.build(elements)
    pdf_buffer.seek(0)

    return pdf_buffer
