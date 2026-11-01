#!/usr/bin/env python3
"""Render actual KiCad/PDF artifacts and build contact sheets for documentation.

Requires KiCad 9, Inkscape, poppler-utils, reportlab and Pillow. This produces
CAD views, not photographs of assembled or tested hardware. Missing official
3D models are recorded rather than replaced by invented component geometry.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
import zipfile
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'downloads/screenshots';BUILD=ROOT/'build/gallery'
OUT.mkdir(parents=True,exist_ok=True);BUILD.mkdir(parents=True,exist_ok=True)
for key in ['CACHE','CONFIG','DATA']:
    os.environ.setdefault('XDG_'+key+'_HOME',str(ROOT/'.tools'/key.lower()))
parser=argparse.ArgumentParser();parser.add_argument('--fetch-models',action='store_true')
args=parser.parse_args()
MODELROOT=ROOT/'.tools/kicad-3d'
os.environ['KICAD9_3DMODEL_DIR']=str(MODELROOT)
board=ROOT/'hardware/voice_pitcher.kicad_pcb'
models=sorted(set(re.findall(r'\(model "\$\{KICAD9_3DMODEL_DIR\}/([^"]+)"',board.read_text())))
base='https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/9.0.2/'
if args.fetch_models:
    def download(path):
        dest=MODELROOT/path
        if dest.exists():return
        try:
            with urllib.request.urlopen(base+path,timeout=30) as response:data=response.read()
            if not data.startswith(b'ISO-10303-21'):raise ValueError('not a STEP model')
            dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        except Exception as error:print('Unavailable official 3D model:',path,str(error),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(download,models))
missing=[p for p in models if not (MODELROOT/p).exists()]

def run(name,command):
    with (BUILD/(name+'.log')).open('w') as log:
        result=subprocess.run(list(map(str,command)),stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:raise RuntimeError(f'{name}: see {BUILD/name}.log')
    print(name,flush=True)

renders=[]
for name,side,rotation,zoom in [('01-pcb-3d-angle','top','335,0,25','.68'),
                                ('02-pcb-3d-top','top','0,0,0','.82'),
                                ('03-pcb-3d-bottom','bottom','0,0,0','.82')]:
    renders.append((name,['kicad-cli','pcb','render',board,'-o',OUT/(name+'.png'),
                         '--width','1800','--height','1600','--side',side,'--rotate',rotation,
                         '--zoom',zoom,'--background','opaque','--quality','high','--floor']))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(lambda item:run(*item),renders))

for name,layers,mirror in [
    ('04-pcb-top-routing','F.Cu,F.Fab,F.Silkscreen,Edge.Cuts',False),
    ('05-pcb-bottom-routing','B.Cu,Edge.Cuts',True),
    ('06-pcb-inner-ground','In1.Cu,Edge.Cuts',False),
    ('07-pcb-inner-3v3','In2.Cu,Edge.Cuts',False),
    ('08-assembly-top','F.Fab,F.Paste,F.Silkscreen,Dwgs.User,Edge.Cuts',False)]:
    svg=BUILD/(name+'.svg')
    command=['kicad-cli','pcb','export','svg',board,'-o',svg,'--layers',layers,
             '--mode-single','--exclude-drawing-sheet','--fit-page-to-board']
    if mirror:command.append('--mirror')
    run(name+'-svg',command)
    run(name,['inkscape',svg,'-o',OUT/(name+'.png'),'-w','2000'])

for page,name in enumerate(['09-schematic-overview','10-schematic-mcu','11-schematic-power',
                           '12-schematic-usb','13-schematic-codec','14-schematic-analog','15-schematic-ui'],1):
    run(name,['pdftoppm','-f',page,'-singlefile','-scale-to','3600','-png',ROOT/'downloads/schematic.pdf',OUT/name])
run('16-manual',['pdftoppm','-f','1','-singlefile','-scale-to','2000','-png',
                 ROOT/'downloads/voice_pitcher_manual_ja.pdf',OUT/'16-manual'])

def contact(name,title,subtitle,tiles,columns=2):
    # Compose lossless artifact thumbnails with captions; full-size PNGs remain
    # separate. The underlying PCB/schematic content is not retouched.
    width=1200;gap=20;cellw=(width-60-(columns-1)*gap)/columns
    cellh=440 if name=='00-board-overview' else 295
    rows=(len(tiles)+columns-1)//columns;height=112+rows*(cellh+gap)+30
    pdf=BUILD/(name+'.pdf');c=canvas.Canvas(str(pdf),pagesize=(width,height))
    c.setFillColorRGB(.95,.965,.975);c.rect(0,0,width,height,fill=1,stroke=0)
    c.setFillColorRGB(.06,.17,.23);c.setFont('Helvetica-Bold',27);c.drawString(30,height-44,title)
    c.setFont('Helvetica',12);c.drawString(30,height-69,subtitle)
    for index,(filename,label) in enumerate(tiles):
        col=index%columns;row=index//columns;x=30+col*(cellw+gap);y=height-104-(row+1)*cellh-row*gap
        c.setFillColorRGB(1,1,1);c.roundRect(x,y,cellw,cellh,10,fill=1,stroke=0)
        c.setFillColorRGB(.06,.17,.23);c.setFont('Helvetica-Bold',12);c.drawString(x+14,y+cellh-24,label)
        imagepath=OUT/(filename+'.png')
        with Image.open(imagepath) as image:iw,ih=image.size
        boxw,boxh=cellw-24,cellh-52;scale=min(boxw/iw,boxh/ih)
        rw,rh=iw*scale,ih*scale
        c.drawImage(ImageReader(str(imagepath)),x+(cellw-rw)/2,y+12+(boxh-rh)/2,width=rw,height=rh)
    c.setFillColorRGB(.3,.36,.4);c.setFont('Helvetica',10)
    c.drawString(30,18,'REV 0.1 / CAD RENDERS / HARDWARE UNTESTED / Full-resolution images are included separately.')
    c.save()
    run(name,['pdftoppm','-singlefile','-scale-to','2600','-png',pdf,OUT/name])

contact('00-board-overview','VOICE PITCHER / BOARD VIEWS',
        '98 x 98 mm / four copper layers / top assembly / bottom views mirrored',[
        ('02-pcb-3d-top','3D / TOP - some models unavailable'),('03-pcb-3d-bottom','3D / BOTTOM'),
        ('04-pcb-top-routing','L1 / TOP ROUTING + COMPONENTS'),('05-pcb-bottom-routing','L4 / BOTTOM ROUTING'),
        ('06-pcb-inner-ground','L2 / GND PLANE'),('07-pcb-inner-3v3','L3 / 3.3 V PLANE')])
contact('00-schematic-overview','VOICE PITCHER / SCHEMATICS',
        'All seven schematic pages + Japanese manual preview / KiCad 9 source exports',[
        ('09-schematic-overview','1 / SYSTEM OVERVIEW'),('10-schematic-mcu','2 / MCU'),
        ('11-schematic-power','3 / POWER'),('12-schematic-usb','4 / USB-C'),
        ('13-schematic-codec','5 / PCM3060 CODEC'),('14-schematic-analog','6 / ANALOG I/O'),
        ('15-schematic-ui','7 / OLED + SWITCHES'),('16-manual','JAPANESE MANUAL / PAGE 1')])

manifest={'kind':'CAD/PDF renders, not assembled-hardware photographs','kicad':'9.0.2',
          'board_sha256':hashlib.sha256(board.read_bytes()).hexdigest(),
          'schematic_pdf_sha256':hashlib.sha256((ROOT/'downloads/schematic.pdf').read_bytes()).hexdigest(),
          'official_3d_model_source':base,'missing_3d_models':missing,
          'not_modeled':['External SSD1306 OLED module'],
          'png_files':sorted(p.name for p in OUT.glob('*.png'))}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(ROOT/'downloads/voice_pitcher_screenshots.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.iterdir()):z.write(p,p.name)
print('Gallery ready:',len(manifest['png_files']),'PNGs;',len(missing),'missing official 3D models.')
