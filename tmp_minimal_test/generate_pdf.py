from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
c = canvas.Canvas('test_smoke.pdf', pagesize=letter)
c.setFont('Helvetica', 12)
c.drawString(72, 720, 'Hello from SnappyTrace OCR smoke test')
c.showPage()
c.save()
print('wrote test_smoke.pdf')
