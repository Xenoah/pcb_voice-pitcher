#!/usr/bin/env python3
"""Build a Japanese manual, firmware downloads and a source/manufacturing bundle."""
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
from pathlib import Path
import zipfile
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'downloads'
status=json.loads((OUT/'reports/hardware.json').read_text())
assert status['status']=='CAD_CHECKS_PASS_HARDWARE_UNTESTED'
assert (OUT/'reports/dsp-spectral.json').exists()
(OUT/'firmware').mkdir(exist_ok=True)
for extension in ['elf','bin','hex']:
    shutil.copy2(ROOT/f'build/firmware/voice_pitcher.{extension}',OUT/f'firmware/voice_pitcher.{extension}')
size_output=subprocess.check_output(['size',str(OUT/'firmware/voice_pitcher.elf')],text=True).splitlines()[-1].split()
firmware_report={'target':'STM32H743VIT6 Cortex-M7 hard-float','flash_address':'0x08000000',
    'text_bytes':int(size_output[0]),'data_bytes':int(size_output[1]),'bss_bytes':int(size_output[2]),
    'bin_sha256':hashlib.sha256((OUT/'firmware/voice_pitcher.bin').read_bytes()).hexdigest(),
    'compile_and_link':'PASS','hardware_boot_test':'NOT_RUN',
    'linker_notes':'newlib nosys stubs warn that filesystem I/O is not implemented; no filesystem or standard I/O service is provided'}
(OUT/'reports/firmware-build.json').write_text(json.dumps(firmware_report,indent=2)+'\n')

pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
base=ParagraphStyle('base',fontName='HeiseiKakuGo-W5',fontSize=9,leading=15,spaceAfter=7,wordWrap='CJK')
styles={'p':base,'h1':ParagraphStyle('h1',parent=base,fontSize=19,leading=26,spaceAfter=16,keepWithNext=True,textColor=colors.HexColor('#10455b')),
        'h2':ParagraphStyle('h2',parent=base,fontSize=13,leading=19,spaceBefore=12,spaceAfter=10,keepWithNext=True,textColor=colors.HexColor('#10455b')),
        'cell':ParagraphStyle('cell',parent=base,fontSize=8,leading=12,spaceAfter=0),
        'code':ParagraphStyle('code',parent=base,fontSize=7,leading=10,backColor=colors.HexColor('#f0f4f6'),borderPadding=6)}
def inline(text):
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1',text)
    text=html.escape(text)
    text=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',text)
    return re.sub(r'`([^`]+)`',r'\1',text)
story=[]
for docname in ['hardware','firmware','manufacturing','validation','sources']:
    if story:story.append(PageBreak())
    lines=(ROOT/'docs'/f'{docname}.md').read_text().splitlines();i=0
    while i<len(lines):
        line=lines[i];i+=1
        if not line.strip():continue
        if line.startswith('```'):
            code=[]
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            i+=1;story.append(Preformatted('\n'.join(code),styles['code'],maxLineLength=88));story.append(Spacer(1,8));continue
        if line.startswith('|'):
            rows=[line]
            while i<len(lines) and lines[i].startswith('|'):rows.append(lines[i]);i+=1
            data=[[Paragraph(inline(cell.strip()),styles['cell']) for cell in row.strip('|').split('|')]
                  for row in rows if not re.fullmatch(r'[| :\-]+',row)]
            cols=len(data[0]);table=Table(data,colWidths=[(A4[0]-84)/cols]*cols,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dceaf0')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b8c6cc')),
                ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
                ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,10)]);continue
        key='h1' if line.startswith('# ') else 'h2' if line.startswith('## ') else 'p'
        text=re.sub(r'^#{1,6} ','',line)
        if text.startswith('- '):text='• '+text[2:]
        story.append(Paragraph(inline(text),styles[key]))
def footer(canvas,doc):
    canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#52636b'))
    canvas.drawString(42,25,'VOICE PITCHER 0.1 / ENGINEERING PROTOTYPE / HARDWARE UNTESTED')
    canvas.drawRightString(A4[0]-42,25,str(doc.page))
SimpleDocTemplate(str(OUT/'voice_pitcher_manual_ja.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,
                  topMargin=38,bottomMargin=44,title='Voice Pitcher Rev 0.1 日本語説明書',author='Xenoah').build(story,onFirstPage=footer,onLaterPages=footer)

# Verify the delivered CSV pair independently of the exporter.
with (OUT/'jlc_bom.csv').open() as f:bom=list(csv.DictReader(f))
with (OUT/'jlc_cpl.csv').open() as f:cpl=list(csv.DictReader(f))
bomrefs=[r.strip() for group in bom for r in group['Designator'].split(',')]
cplrefs=[r['Designator'] for r in cpl]
assert len(bomrefs)==len(set(bomrefs))==len(cplrefs)==len(set(cplrefs))==100
assert set(bomrefs)==set(cplrefs) and all(r['Layer']=='Top' for r in cpl)
for r in cpl:
    assert 0<=float(r['Mid X'].removesuffix('mm'))<=98
    assert 0<=float(r['Mid Y'].removesuffix('mm'))<=98
    assert 0<=float(r['Rotation'])<360

(OUT/'READ_BEFORE_ORDERING.txt').write_text(
    'VOICE PITCHER REV 0.1 — ENGINEERING PROTOTYPE\n'
    'CAD checks pass. Hardware has NOT been built or bench-tested.\n'
    'Read docs/manufacturing.md and docs/validation.md before ordering.\n'
    '37 SMT parts have unverified JLC sourcing; the codec has LCSC-only confirmation.\n'
    'CPL rotations require JLC assembly-preview review. All parts are TOP.\n'
    'USB impedance, power/thermal, audio quality, latency and USB compatibility remain unvalidated.\n'
    'This is a USB DEVICE and stereo LINE interface, not a USB host or microphone/headphone interface.\n'
    'Zero-loss/zero-latency pitch shifting is not physically achievable.\n')

archive=OUT/'voice_pitcher_rev0.1_prototype.zip'
def wanted(p):
    return p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.kicad_prl'] and not p.name.endswith('.lck')
sources=[]
for folder in ['hardware','firmware','tools','tests','docs','LICENSES','.github']:
    sources.extend(p for p in (ROOT/folder).rglob('*') if wanted(p))
sources.extend(ROOT/name for name in ['README.md','LICENSE','Makefile','.gitignore','.gitattributes'])
payload=[p for p in OUT.rglob('*') if wanted(p) and p not in [archive,OUT/'SHA256SUMS.txt']]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(sources+payload):z.write(path,Path('voice_pitcher_rev0.1')/path.relative_to(ROOT))
checksums=[]
for path in sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'):
    checksums.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(OUT)))
(OUT/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
print(f'Packaged {archive.name}: {archive.stat().st_size:,} bytes. All 100 BOM/CPL references agree.')
