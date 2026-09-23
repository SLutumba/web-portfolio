"""Rebuild the one-page CV from confirmed portfolio facts."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'static' / 'assets' / 'Shekinah-Lutumba-CV.pdf'
WIDTH, HEIGHT = A4
INK, MUTED, BLUE, LINE = map(HexColor, ['#172735','#536574','#426e8b','#d8e5ef'])
pdf = canvas.Canvas(str(OUTPUT), pagesize=A4)
pdf.setTitle('Shekinah Lutumba - Software Engineer')
pdf.setAuthor('Shekinah Lutumba')
pdf.setSubject('Software engineering experience, project work and education')
left, content_width = 46, WIDTH - 92
y = HEIGHT - 52
pdf.setFillColor(INK)
pdf.setFont('Helvetica-Bold', 25)
pdf.drawString(left, y, 'Shekinah Lutumba')
y -= 25
pdf.setFont('Helvetica', 12)
pdf.setFillColor(BLUE)
pdf.drawString(left, y, 'Software Engineer')
y -= 22

styles = {
    'body': ParagraphStyle('body', fontName='Helvetica', fontSize=9.5, leading=14.5, textColor=MUTED),
    'small': ParagraphStyle('small', fontName='Helvetica', fontSize=8.5, leading=13, textColor=MUTED),
    'bullet': ParagraphStyle('bullet', fontName='Helvetica', fontSize=9.5, leading=14.5, textColor=MUTED, leftIndent=9, firstLineIndent=-9),
}

def paragraph(text, kind='body', gap=7):
    global y
    p = Paragraph(text, styles[kind])
    _, height = p.wrap(content_width, 700)
    p.drawOn(pdf, left, y-height)
    y -= height + gap

def heading(text):
    global y
    y -= 13
    pdf.setFillColor(BLUE)
    pdf.setFont('Helvetica-Bold', 9)
    pdf.drawString(left, y, text.upper())
    pdf.setStrokeColor(LINE)
    pdf.line(left, y-8, WIDTH-left, y-8)
    y -= 23

def title(text, right=''):
    global y
    pdf.setFillColor(INK)
    pdf.setFont('Helvetica-Bold', 10.5)
    pdf.drawString(left, y, text)
    if right:
        pdf.setFont('Helvetica', 8.5)
        pdf.setFillColor(MUTED)
        pdf.drawRightString(WIDTH-left, y, right)
    y -= 18

paragraph('Pretoria, South Africa | <link href="mailto:s.lutumba15@gmail.com" color="#426e8b">s.lutumba15@gmail.com</link>', 'small', 4)
paragraph('<link href="https://www.linkedin.com/in/shekinahlutumba15" color="#426e8b">linkedin.com/in/shekinahlutumba15</link> | <link href="https://github.com/SLutumba" color="#426e8b">github.com/SLutumba</link>', 'small', 9)
paragraph('Early-career software engineer with commercial experience in enterprise financial systems and independent Python backend projects. Curious about how systems work, deliberate about learning, and dependable when collaborating on technical problems. Now working in MIP\'s Mobile Apps team after completing Flutter training.')

heading('Professional experience')
title('Junior Software Engineer - MIP Holdings', 'Aug 2025 - Present')
for text in [
    'Develop and maintain financial-software features across backend services and web interfaces using Progress ABL/OpenEdge, Warp5 and JavaScript.',
    'Translate business requirements into database operations, business rules, validation and defect fixes, working through code review, manual testing, QA and production release.',
    'Contributed to payment configuration, bank and branch maintenance, and fixes to reconciliation workflows.',
    'Completed Dart and Flutter training and transitioned into the Mobile Apps team.',
]: paragraph('- ' + text, 'bullet', 5)

heading('Selected project')
title('Task Management REST API', 'Python / Flask')
paragraph('<link href="https://github.com/SLutumba/task-management-api" color="#426e8b">github.com/SLutumba/task-management-api</link>', 'small', 7)
for text in [
    'Built authenticated task workflows with Flask, SQLAlchemy and SQLite, including registration, login, JWT protection and user-scoped ownership checks.',
    'Implemented Pydantic validation, partial updates, password hashing and separated routes, services, models and serialization helpers.',
    'Repository includes 98 integration test cases covering authentication, ownership isolation, validation, updates, date persistence and password boundaries.',
]: paragraph('- ' + text, 'bullet', 5)

heading('Technical toolkit')
paragraph('<b>Professional:</b> Progress ABL, OpenEdge, Warp5, JavaScript.<br/><b>Projects:</b> Python, Flask, SQLAlchemy, SQLite, Pydantic, REST APIs, JWT, pytest, Git/GitHub, HTML/CSS.<br/><b>Mobile:</b> Dart and Flutter (training completed; now working in the Mobile Apps team).<br/><b>Developing:</b> BLoC and Cubit.', gap=3)

heading('Education')
title('Diploma in Computer Systems Engineering', 'In progress')
paragraph('Tshwane University of Technology<br/>Academic foundation in programming, object-oriented programming, networking, computer systems and electronics.', gap=4)

if y < 38:
    raise RuntimeError(f'CV content exceeds one page: {y=}')
pdf.save()
print(f'Created {OUTPUT.name}; bottom of content at {y:.1f} pt')
