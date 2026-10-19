"""Render the editable academic report. Requires reportlab; no Flask dependency."""
from pathlib import Path
from html import escape
import re
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'output/pdf/Informe_Tecnico_Juridico_CrossData.pdf'
DEST.parent.mkdir(parents=True, exist_ok=True)
NAVY = colors.HexColor('#15334d')
BLUE = colors.HexColor('#236c9b')
MUTED = colors.HexColor('#566878')
styles = {
    'body': ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14,textColor=NAVY,spaceAfter=10),
    'title': ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=23,leading=28,textColor=NAVY,spaceAfter=19),
    'sub': ParagraphStyle('sub',fontName='Helvetica-Bold',fontSize=15,leading=20,textColor=BLUE,spaceAfter=16),
    'h3': ParagraphStyle('h3',fontName='Helvetica-Bold',fontSize=11.5,leading=16,textColor=BLUE,spaceBefore=10,spaceAfter=7,keepWithNext=True),
    'cell': ParagraphStyle('cell',fontName='Helvetica',fontSize=9,leading=12,textColor=NAVY),
    'head': ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=colors.white),
    'url': ParagraphStyle('url',fontName='Helvetica',fontSize=8,leading=10,textColor=BLUE,spaceAfter=9,splitLongWords=True),
}

def para(text, style='body'):
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    return Paragraph(text,styles[style])

def decoration(canvas,doc):
    w,h=A4
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0,h-14,w,14,fill=1,stroke=0)
    canvas.setFont('Helvetica-Bold',9)
    canvas.drawString(42,h-36,'CROSSDATA / COMPLIANCE')
    canvas.setFont('Helvetica',8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(w-42,h-36,'CASO 7 · INFORME ACADÉMICO')
    canvas.setStrokeColor(colors.HexColor('#d7e2e9'))
    canvas.line(42,40,w-42,40)
    canvas.setFont('Helvetica',8)
    canvas.drawString(42,27,'AndeClass · Datos ficticios · 18 octubre 2026')
    canvas.drawRightString(w-42,27,str(doc.page))
    canvas.restoreState()

story=[]
lines=(ROOT/'docs/INFORME_ACADEMICO.md').read_text(encoding='utf-8').splitlines()
i=0
while i<len(lines):
    line=lines[i].strip()
    if not line:
        i+=1; continue
    if line=='---': story.append(PageBreak())
    elif line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            cells=[v.strip() for v in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r'[:\- ]+',v) for v in cells):
                rows.append([para(v,'head' if not rows else 'cell') for v in cells])
            i+=1
        width=A4[0]-84
        widths=[width*.25,width*.38,width*.37] if len(rows[0])==3 else [width*.35,width*.65]
        table=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f0f5f8'),colors.white]),
            ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d7e2e9')),
            ('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),
            ('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]))
        story.extend([table,Spacer(1,10)]); continue
    elif line.startswith('### '): story.append(para(line[4:],'h3'))
    elif line.startswith('## '): story.append(para(line[3:],'sub'))
    elif line.startswith('# '): story.append(para(line[2:],'title'))
    elif line.startswith('https://'):
        url=escape(line,quote=True)
        story.append(Paragraph(f'<link href="{url}" color="#236c9b">{url}</link>',styles['url']))
    elif line.startswith('[') and i+1<len(lines) and lines[i+1].startswith('https://'):
        url=escape(lines[i+1],quote=True)
        story.append(KeepTogether([para(line),Paragraph(f'<link href="{url}" color="#236c9b">Abrir fuente oficial</link>',styles['url'])]))
        i+=1
    else: story.append(para(line))
    i+=1

doc=SimpleDocTemplate(str(DEST),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=62,bottomMargin=56,
    title='CrossData Compliance - Informe técnico-jurídico',author='Proyecto académico AndeClass',pageCompression=1)
doc.build(story,onFirstPage=decoration,onLaterPages=decoration)
print(DEST)
