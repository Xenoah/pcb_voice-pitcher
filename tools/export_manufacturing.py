#!/usr/bin/env python3
"""Export from the checked routed PCB; never substitute the placement-only PCB."""
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile
from collections import defaultdict
from design import PARTS

ROOT=Path(__file__).resolve().parents[1]
for key,folder in [('XDG_CACHE_HOME','cache'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data')]:
    os.environ.setdefault(key,str(ROOT/'.tools'/folder))
import pcbnew as pcb
os.chdir(ROOT)
OUT=ROOT/'downloads';OUT.mkdir(exist_ok=True)
FAB=OUT/'fabrication';FAB.mkdir(exist_ok=True)
REPORT=OUT/'reports';REPORT.mkdir(exist_ok=True)
board=ROOT/'hardware/voice_pitcher.kicad_pcb'
report=json.loads((ROOT/'build/checks/hardware.json').read_text())
assert report['status']=='CAD_CHECKS_PASS_HARDWARE_UNTESTED'

def run(*args):subprocess.run(list(map(str,args)),check=True)
def csvfile(path,headers,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)
def refsort(ref):return re.sub(r'\d+',lambda m:m.group().zfill(5),ref)

run('kicad-cli','pcb','export','gerbers',board,'-o',str(FAB)+'/',
    '--layers','F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,F.Paste,Edge.Cuts',
    '--use-drill-file-origin','--subtract-soldermask')
run('kicad-cli','pcb','export','drill',board,'-o',str(FAB)+'/',
    '--drill-origin','plot','--excellon-separate-th','--generate-map','--map-format','pdf')
run('kicad-cli','sch','export','pdf',ROOT/'hardware/voice_pitcher.kicad_sch',
    '-o',OUT/'schematic.pdf','--no-background-color')
for name,layers in [('assembly-top','F.Fab,F.Silkscreen,F.Paste,Dwgs.User,Edge.Cuts'),
                    ('board-top','F.Cu,F.Fab,F.Silkscreen,Edge.Cuts'),
                    ('board-bottom','B.Cu,Edge.Cuts')]:
    run('kicad-cli','pcb','export','svg',board,'-o',OUT/(name+'.svg'),
        '--layers',layers,'--mode-single','--exclude-drawing-sheet','--fit-page-to-board')
run('inkscape',OUT/'assembly-top.svg','--export-type=pdf','-o',OUT/'assembly-top.pdf')
run('inkscape',OUT/'board-top.svg','-o',OUT/'board-top.png','-w','1400')

groups=defaultdict(list)
for p in PARTS:
    if p['assembly']=='SMT':groups[(p['mpn'],p['footprint'],p['lcsc'])].append(p)
rows=[]
for (mpn,fp,lcsc),items in sorted(groups.items()):
    rows.append([items[0]['value']+' / '+mpn,','.join(sorted((p['ref'] for p in items),key=refsort)),fp,lcsc])
csvfile(OUT/'jlc_bom.csv',['Comment','Designator','Footprint','LCSC Part #'],rows)
fields=['ref','value','mpn','lcsc','footprint','assembly','sourcing_status','source_url']
csvfile(OUT/'bom_master.csv',fields,[[p[f] for f in fields] for p in sorted(PARTS,key=lambda p:refsort(p['ref']))])
b=pcb.LoadBoard(str(board));smt={p['ref'] for p in PARTS if p['assembly']=='SMT'}
positions=[]
for fp in sorted(b.GetFootprints(),key=lambda fp:refsort(fp.GetReference())):
    if fp.GetReference() not in smt:continue
    assert fp.GetLayer()==pcb.F_Cu
    positions.append([fp.GetReference(),f'{pcb.ToMM(fp.GetPosition().x)-50:.4f}mm',
                      f'{148-pcb.ToMM(fp.GetPosition().y):.4f}mm','Top',f'{fp.GetOrientationDegrees()%360:.4f}'])
csvfile(OUT/'jlc_cpl.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],positions)
assert {p[0] for p in positions}=={ref for row in rows for ref in row[1].split(',')}
csvfile(OUT/'additional_parts.csv',['Item','Quantity','Specification','Assembly'],[
 ['OLED1',1,'SSD1306 128x64 I2C 0x3C; 3.3V; GND,VCC,SCL,SDA; verify module dimensions','HAND'],
 ['USB cable',1,'USB-C data cable for host use; C-C for Type-C Rp standalone adapter','EXTERNAL'],
 ['Standalone supply',1,'5V Type-C source advertising >=1.5A; no PD voltage negotiation','EXTERNAL'],
 ['6.35mm adapters',2,'Optional stereo TRS 3.5mm to 6.35mm; mono TS requires appropriate channel wiring','EXTERNAL'],
 ['Standoffs',4,'M3 nonconductive or insulated; check clearance','HAND']])
for file in (ROOT/'build/checks').glob('*.json'):
    if file.name in ['hardware.json','dsp-spectral.json','final-erc.json','final-drc.json']:
        shutil.copy2(file,REPORT/file.name)
with zipfile.ZipFile(OUT/'voice_pitcher_gerbers.zip','w',zipfile.ZIP_DEFLATED) as z:
    for file in sorted(FAB.iterdir()):z.write(file,file.name)
print(f'Exported {len(positions)} top SMT positions and {len(rows)} BOM groups.')
