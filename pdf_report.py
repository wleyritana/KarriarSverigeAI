
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from io import BytesIO
from datetime import datetime

def build_pdf_report(data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    elements = []

    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    normal_style = styles["BodyText"]

    elements.append(Paragraph("AI Job Hunt Executive Report", title_style))
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    for key, value in data.items():
        elements.append(Paragraph(f"<b>{key}</b>", styles["Heading2"]))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph(value.replace("\n", "<br/>"), normal_style))
        elements.append(Spacer(1, 0.4 * inch))

    doc.build(elements)
    buffer.seek(0)
    return buffer
