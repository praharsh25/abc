"""PDF export of a question paper with an optional answer key."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

LETTERS = "ABCD"


def build_pdf(items, title="Question Paper", include_answers=True) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=56, rightMargin=56, topMargin=56, bottomMargin=56, title=title)
    ss = getSampleStyleSheet()
    q = ParagraphStyle("q", parent=ss["BodyText"], fontSize=11.5, leading=16, spaceBefore=10)
    opt = ParagraphStyle("o", parent=q, leftIndent=22, spaceBefore=2)
    story = [Paragraph(escape(title), ss["Title"])]
    for i, it in enumerate(items, 1):
        prefix = "True or false: " if it.get("type") == "tf" else ""
        story.append(Paragraph(f"{i}. {prefix}{escape(it['question'])}", q))
        for j, o in enumerate(it.get("options") or []):
            story.append(Paragraph(f"{LETTERS[j]}. {escape(o)}", opt))
    if include_answers:
        story += [PageBreak(), Paragraph("Answer key", ss["Title"])]
        for i, it in enumerate(items, 1):
            a = str(it.get("answer", ""))
            if it.get("options") and it.get("correct_index") is not None:
                a = f"{LETTERS[it['correct_index']]}. {a}"
            story.append(Paragraph(f"{i}. {escape(a)}", q))
    doc.build(story)
    return buf.getvalue()
