#!/usr/bin/env python3
"""Generate editable KiCad 9 schematics, placement, netlist and part metadata.

Run with /usr/bin/python3 (KiCad's pcbnew module must be installed).
The routed PCB is maintained separately: this script writes placement.kicad_pcb.
"""
import copy
import json
import os
from pathlib import Path
import uuid
from design import PARTS, PAGES
from sexp import loads, dumps, child, children, Sym

ROOT=Path(__file__).resolve().parents[1]
HW=ROOT/'hardware'
LIB=HW/'VoicePitcher.pretty'
NS=uuid.UUID('79ebdf07-dcd6-4aac-94c8-c19d38b640c6')
uid=lambda name: str(uuid.uuid5(NS,name))
q=lambda value: json.dumps(str(value),ensure_ascii=False)
LIB.mkdir(parents=True,exist_ok=True)

catalog={}
def symbol(lib_id):
    lib,name=lib_id.split(':')
    if lib_id=='VoicePitcher:TPS22918':
        pins=[]
        for num,pname,kind,x,y,angle in [(1,'VIN','power_in',-7.62,5.08,0),(2,'GND','power_in',0,-10.16,90),
                (3,'ON','input',-7.62,0,0),(4,'CT','passive',7.62,-5.08,180),(5,'QOD','passive',7.62,0,180),(6,'VOUT','power_out',7.62,5.08,180)]:
            pins.append(f'(pin {kind} line (at {x} {y} {angle}) (length 2.54) (name "{pname}" (effects (font (size 1.27 1.27)))) (number "{num}" (effects (font (size 1.27 1.27)))))')
        return loads('(symbol "TPS22918" (pin_names (offset 1.016)) (in_bom yes) (on_board yes) '
            '(property "Reference" "U" (at 0 10.16 0) (effects (font (size 1.27 1.27)))) '
            '(property "Value" "TPS22918" (at 0 12.7 0) (effects (font (size 1.27 1.27)))) '
            '(symbol "TPS22918_0_1" (rectangle (start -5.08 7.62) (end 5.08 -7.62) (stroke (width 0.254) (type default)) (fill (type background)))) '
            '(symbol "TPS22918_1_1" '+' '.join(pins)+'))')
    if lib not in catalog:
        data=loads(Path('/usr/share/kicad/symbols',lib+'.kicad_sym').read_text())
        catalog[lib]={x[1]:x for x in children(data,'symbol')}
    node=copy.deepcopy(catalog[lib][name])
    ext=child(node,'extends')
    if ext:
        parent=symbol(lib+':'+ext[1])
        properties={p[1] for p in children(node,'property')}
        inherited=[x for x in parent[2:] if not isinstance(x,list) or
                   x[0]!='property' or x[1] not in properties]
        node=[Sym('symbol'),name]+[x for x in node[2:] if x is not ext]+inherited
        for sub in children(node,'symbol'):
            suffix=sub[1].rsplit('_',2)[1:]
            sub[1]=name+'_'+'_'.join(suffix)
    return node

def pins_for(node,unit):
    pins=[]
    for sub in children(node,'symbol'):
        u=int(sub[1].rsplit('_',2)[1])
        if u in [0,unit]:
            pins+=children(sub,'pin')
    return pins

def units_for(node):
    return sorted({int(x[1].rsplit('_',2)[1]) for x in children(node,'symbol')} - {0}) or [1]

def fp_name(part):
    return part['footprint'].replace(':','__')

for p in PARTS:
    lib,name=p['footprint'].split(':')
    text=Path('/usr/share/kicad/footprints',lib+'.pretty',name+'.kicad_mod').read_text()
    fp=loads(text)
    fp[1]=fp_name(p)
    if p.get('pad_map'):
        for pad in children(fp,'pad'):
            if pad[1] in p['pad_map']:
                pad[1]=p['pad_map'][pad[1]]
    (LIB/(fp_name(p)+'.kicad_mod')).write_text(dumps(fp)+'\n')

def text_at(text,x,y,size=1.5):
    return f'(text {q(text)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left)) (uuid {q(uid(text+str(x)+str(y)))}))'

root_id=uid('root')
def sheet_header(name,paper='A2'):
    return f'''(kicad_sch (version 20250114) (generator "eeschema")
      (uuid "{uid(name)}") (paper "{paper}")
      (title_block (title "VOICE PITCHER — {name.upper()}") (date "2026-11-01") (rev "0.1-prototype")
       (company "Xenoah") (comment 1 "ENGINEERING PROTOTYPE — NOT VALIDATED ON HARDWARE"))'''

all_symbols={p['symbol']:symbol(p['symbol']) for p in PARTS}
all_symbols['power:PWR_FLAG']=symbol('power:PWR_FLAG')
# In hardware mode this multiplexed codec pin is DEMP, a digital input.
for pin in pins_for(all_symbols['Audio:PCM3060'],1):
    if child(pin,'number')[1]=='2':pin[1]=Sym('input')
# Vendor the exact resolved symbols so offline ERC compares against the same source.
(HW/'symbols').mkdir(exist_ok=True)
lib_groups={}
for lib_id,node in all_symbols.items():
    lib_groups.setdefault(lib_id.split(':')[0],[]).append(dumps(node))
for lib,nodes in lib_groups.items():
    (HW/'symbols'/(lib+'.kicad_sym')).write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(nodes)+')\n')
(HW/'sym-lib-table').write_text('(sym_lib_table (version 7)\n'+'\n'.join(
    f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/symbols/{lib}.kicad_sym") (options "") (descr "Vendored resolved symbols"))'
    for lib in lib_groups)+')\n')
errors=[]
for p in PARTS:
    valid={str(child(pin,'number')[1]) for u in units_for(all_symbols[p['symbol']]) for pin in pins_for(all_symbols[p['symbol']],u)}
    missing=set(p['pins'])-valid
    if missing:
        errors.append((p['ref'],missing))
assert not errors,errors

for page in PAGES:
    parts=[p for p in PARTS if p['page']==page]
    lib_ids={p['symbol'] for p in parts}
    if page=='power': lib_ids.add('power:PWR_FLAG')
    nodes=[]
    for lib_id in sorted(lib_ids):
        n=copy.deepcopy(all_symbols[lib_id]); n[1]=lib_id
        nodes.append(dumps(n))
    out=[sheet_header(page), '(lib_symbols '+'\n'.join(nodes)+')']
    out.append(text_at('All named nets are global. Unused pins are explicitly NC.',20,15))
    out.append(text_at('See docs/hardware.md for design assumptions and open validation items.',20,22))
    cells=[]
    for p in parts:
        for unit in units_for(all_symbols[p['symbol']]):
            cells.append((p,unit))
    small=0
    for p,unit in cells:
        if p['ref']=='U1':
            x,y=75,145
        elif p['ref']=='U2':
            x,y=80,110
        elif p['ref']=='J1':
            x,y=80,100
        else:
            # 7 columns on A2; large symbols reserve the first two columns.
            offset=2 if page in ['mcu','codec','usb'] else 0
            cols=7-offset
            x=45+(offset+small%cols)*75
            y=60+(small//cols)*63
            small+=1
        x,y=round(round(x/1.27)*1.27,4),round(round(y/1.27)*1.27,4)
        node=all_symbols[p['symbol']]
        inst_id=uid(p['ref']+'-unit-'+str(unit))
        path='/'+root_id+'/'+uid('sheet-'+page)
        footprint='VoicePitcher:'+fp_name(p)
        label_y=y+10 if p['ref'] not in ['U1','U2','J1'] else y-(80 if p['ref']=='U1' else 34)
        props=f'''(property "Reference" "{p['ref']}" (at {x} {label_y} 0) (effects (font (size 1.27 1.27))))
         (property "Value" {q(p['value'])} (at {x} {label_y+3} 0) (effects (font (size 1.27 1.27))))
         (property "Footprint" {q(footprint)} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
         (property "MPN" {q(p['mpn'])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
         (property "LCSC" {q(p['lcsc'])} (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))'''
        out.append(f'''(symbol (lib_id {q(p['symbol'])}) (at {x} {y} 0) (unit {unit})
          (in_bom yes) (on_board yes) (dnp no) (uuid {q(inst_id)}) {props}
          (instances (project "voice_pitcher" (path {q(path)} (reference "{p['ref']}") (unit {unit})))))''')
        done=set()
        for pin in pins_for(node,unit):
            num=str(child(pin,'number')[1]); at=child(pin,'at'); px=x+at[1]; py=y-at[2]
            net=p['pins'].get(num)
            key=(px,py,net)
            if key in done:continue
            done.add(key)
            if net:
                angle=at[3]
                # Label at wire end; one grid step outward from the pin.
                dx,dy={0:(-2.54,0),180:(2.54,0),90:(0,2.54),270:(0,-2.54)}[angle]
                ex,ey=round(px+dx,4),round(py+dy,4)
                out.append(f'(wire (pts (xy {px} {py}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid "{uid(inst_id+num+"w")}"))')
                out.append(f'''(global_label {q(net)} (shape input) (at {ex} {ey} {angle})
                  (effects (font (size 1 1)) (justify left)) (uuid "{uid(inst_id+num+'l')}")
                  (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {ex} {ey} {angle}) (effects (font (size 1 1)) (hide yes))))''')
            else:
                out.append(f'(no_connect (at {px} {py}) (uuid "{uid(inst_id+num+"nc")}"))')
    if page=='power':
        for i,net in enumerate(['VBUS','+5V_RAW','+5VA','+3V3A','GND']):
            x,y=round(round((50+75*i)/1.27)*1.27,4),335.28
            ref='#FLG0'+str(i+1)
            out.append(f'''(symbol (lib_id "power:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no)
             (uuid "{uid(ref)}") (property "Reference" "{ref}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes)))
             (property "Value" "PWR_FLAG" (at {x} {y-4} 0) (effects (font (size 1 1))))
             (instances (project "voice_pitcher" (path "/{root_id}/{uid('sheet-'+page)}" (reference "{ref}") (unit 1)))))
             (global_label {q(net)} (shape input) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+'l')}")
               (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x} {y} 0) (effects (font (size 1 1)) (hide yes))))''')
    out.append(')')
    (HW/(page+'.kicad_sch')).write_text('\n'.join(out)+'\n')

out=[sheet_header('root','A4'),'(lib_symbols)',text_at('VOICE PITCHER / 98 x 98 mm / TOP ASSEMBLY',20,20,2.2),
     text_at('STM32H743 + PCM3060 / stereo line I/O / USB-C device / SSD1306',20,29),
     text_at('0.1 engineering prototype. Targets are not measured specifications.',20,37)]
for i,page in enumerate(PAGES):
    x=25+(i%3)*85;y=55+(i//3)*55
    out.append(f'''(sheet (at {x} {y}) (size 70 32) (stroke (width 0.1524) (type default))
      (fill (color 0 0 0 0)) (uuid "{uid('sheet-'+page)}")
      (property "Sheetname" {q(page.upper())} (at {x} {y-2} 0) (effects (font (size 1.5 1.5)) (justify left bottom)))
      (property "Sheetfile" "{page}.kicad_sch" (at {x} {y+34} 0) (effects (font (size 1.27 1.27)) (justify left top)))
      (instances (project "voice_pitcher" (path "/{root_id}" (page "{i+2}")))))''')
out+=['(sheet_instances (path "/" (page "1")))',')']
(HW/'voice_pitcher.kicad_sch').write_text('\n'.join(out)+'\n')
(HW/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "VoicePitcher") (type "KiCad") (uri "${KIPRJMOD}/VoicePitcher.pretty") (options "") (descr "Vendored KiCad 9 footprints; CUI jack pad names mapped to S/T/R")))\n')
(HW/'parts.json').write_text(json.dumps(PARTS,indent=2)+'\n')

os.environ.setdefault('XDG_CACHE_HOME',str(ROOT/'.tools/cache'))
os.environ.setdefault('XDG_CONFIG_HOME',str(ROOT/'.tools/config'))
os.environ.setdefault('XDG_DATA_HOME',str(ROOT/'.tools/data'))
import pcbnew as pcb
board=pcb.BOARD();board.SetCopperLayerCount(4)
ds=board.GetDesignSettings()
ds.SetCopperLayerCount(4)
ds.m_TrackMinWidth=pcb.FromMM(.15)
ds.m_MinClearance=pcb.FromMM(.15)
ds.m_ViasMinSize=pcb.FromMM(.6)
ds.m_MinThroughDrill=pcb.FromMM(.3)
ds.m_CopperEdgeClearance=pcb.FromMM(.3)
ds.SetAuxOrigin(pcb.VECTOR2I(pcb.FromMM(50),pcb.FromMM(148)))
nets={}
for n in sorted({v for p in PARTS for v in p['pins'].values()}):
    net=pcb.NETINFO_ITEM(board,n);board.Add(net);nets[n]=net
for p in PARTS:
    fp=pcb.FootprintLoad(str(LIB),fp_name(p))
    assert fp,p['footprint']
    fp.SetReference(p['ref']);fp.SetValue(p['value'])
    fp.SetPosition(pcb.VECTOR2I(pcb.FromMM(p['x']),pcb.FromMM(p['y'])))
    fp.SetOrientationDegrees(p['rotation'])
    fp.SetPath(pcb.KIID_PATH('/'+root_id+'/'+uid('sheet-'+p['page'])+'/'+uid(p['ref']+'-unit-1')))
    fp.Value().SetVisible(False)
    fp.Reference().SetLayer(pcb.F_Fab)
    fp.Reference().SetTextSize(pcb.VECTOR2I(pcb.FromMM(.8),pcb.FromMM(.8)))
    fp.Reference().SetTextThickness(pcb.FromMM(.12))
    if p['assembly']=='MECHANICAL':
        fp.SetAttributes(pcb.FP_EXCLUDE_FROM_BOM|pcb.FP_EXCLUDE_FROM_POS_FILES)
    elif p['assembly']=='HAND':fp.SetAttributes(pcb.FP_THROUGH_HOLE)
    for pad in fp.Pads():
        if pad.GetNumber() in p['pins']:
            pad.SetNet(nets[p['pins'][pad.GetNumber()]])
    for graphic in fp.GraphicalItems():
        if graphic.GetLayer()==pcb.F_SilkS:
            bb=graphic.GetBoundingBox()
            if min(bb.GetLeft(),bb.GetTop()) < pcb.FromMM(50.35) or max(bb.GetRight(),bb.GetBottom()) > pcb.FromMM(147.65):
                graphic.SetLayer(pcb.F_Fab)
    board.Add(fp)
for a,b in [((50,50),(148,50)),((148,50),(148,148)),((148,148),(50,148)),((50,148),(50,50))]:
    line=pcb.PCB_SHAPE();line.SetShape(pcb.SHAPE_T_SEGMENT);line.SetLayer(pcb.Edge_Cuts)
    line.SetStart(pcb.VECTOR2I(pcb.FromMM(a[0]),pcb.FromMM(a[1])));line.SetEnd(pcb.VECTOR2I(pcb.FromMM(b[0]),pcb.FromMM(b[1])))
    line.SetWidth(pcb.FromMM(.05));board.Add(line)
def board_text(t,x,y,size=1):
    obj=pcb.PCB_TEXT(board);obj.SetText(t);obj.SetPosition(pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y)))
    obj.SetTextSize(pcb.VECTOR2I(pcb.FromMM(size),pcb.FromMM(size)));obj.SetTextThickness(pcb.FromMM(.15));obj.SetLayer(pcb.F_SilkS);board.Add(obj)
board_text('VOICE PITCHER',99,53,1.8)
board_text('REV 0.1 / PROTOTYPE',100,81,1)
board_text('USB-C',123,65,1)
board_text('IN',58,78,1.2);board_text('OUT',58,105,1.2)
for name,x in [('MODE',83),('DOWN',98),('UP',113),('I/O',128)]:board_text(name,x,144,1)
board_text('OLED  GND 3V3 SCL SDA',98,66,.9)
# OLED body reservation: generic 0.96 inch module, 28 x 28 mm. No copper restriction.
for a,b in [((84,57),(112,57)),((112,57),(112,78)),((112,78),(84,78)),((84,78),(84,57))]:
    line=pcb.PCB_SHAPE();line.SetShape(pcb.SHAPE_T_SEGMENT);line.SetLayer(pcb.Dwgs_User)
    line.SetStart(pcb.VECTOR2I(pcb.FromMM(a[0]),pcb.FromMM(a[1])));line.SetEnd(pcb.VECTOR2I(pcb.FromMM(b[0]),pcb.FromMM(b[1])))
    line.SetWidth(pcb.FromMM(.15));board.Add(line)
pcb.SaveBoard(str(HW/'placement.kicad_pcb'),board)
project={"meta":{"filename":"voice_pitcher.kicad_pro","version":1},
 "board":{"design_settings":{"rules":{"min_clearance":.15,"min_track_width":.15,"min_via_diameter":.6,"min_through_hole_diameter":.3,"min_copper_edge_clearance":.3},
 "defaults":{"copper_line_width":.2,"copper_text_size_h":1,"copper_text_size_v":1,"copper_text_thickness":.15}}},
 "net_settings":{"version":4,"classes":[{"name":"Default","clearance":.15,"track_width":.2,"via_diameter":.6,"via_drill":.3,"diff_pair_width":.2,"diff_pair_gap":.18,"diff_pair_via_gap":.25}]}}
(HW/'voice_pitcher.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
(HW/'placement.kicad_pro').write_text(json.dumps(project,indent=2)+'\n')
print(f'Generated {len(PARTS)} parts, {len(nets)} nets, 7 schematic sheets and 98 x 98 mm placement.')
