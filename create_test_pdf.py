"""
Quick test: Create a simple text file for end-to-end pipeline test
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Create a simple PDF with a few paragraphs
pdf_path = "test_simple.pdf"
c = canvas.Canvas(pdf_path, pagesize=letter)

# Add text
c.setFont("Helvetica", 12)
y = 750  # Start near top

paragraphs = [
    "The Master said, 'Learning without thought is labor lost.",
    "Thought without learning is perilous.'",
    "",
    "Confucius taught that a person should always strive to learn.",
    "He believed that education was the foundation of a virtuous life.",
    "",
    "The path to wisdom requires both study and reflection.",
]

for para in paragraphs:
    if para:
        c.drawString(50, y, para)
    y -= 20

c.save()
print(f"Created test PDF: {pdf_path}")
