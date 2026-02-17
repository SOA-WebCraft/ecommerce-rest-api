from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

def generate_invoice(order):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    elements = []

    # Header
    elements.append(Paragraph(f"<b>Invoice #{order.id}</b>", styles['Title']))
    elements.append(Paragraph(f"User: {order.user.username}", styles['Normal']))
    elements.append(Paragraph(f"Date: {order.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    elements.append(Paragraph("<br/><br/>", styles['Normal']))

    # Table Data
    data = [["Item", "Qty", "Price", "Total"]]
    for item in order.items.all():
        data.append([
            item.product.name,
            str(item.quantity),
            f"${item.price:.2f}",
            f"${item.price * item.quantity:.2f}"
        ])

    # Footer row: Grand Total
    data.append(["", "", "<b>Grand Total</b>", f"<b>${order.total_price:.2f}</b>"])

    table = Table(data, colWidths=[200, 60, 80, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
    ]))
    
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer