#!/usr/bin/env python3
"""Independent KiCad ERC/DRC, XML-netlist/PCB parity, dimensions and assembly checks."""
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from design import PARTS

ROOT=Path(__file__).resolve().parents[1]
for key,folder in [('XDG_CACHE_HOME','cache'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data')]:
    os.environ.setdefault(key,str(ROOT/'.tools'/folder))
import pcbnew as pcb

def main():
    os.chdir(ROOT)
    dest=ROOT/'build/checks';dest.mkdir(parents=True,exist_ok=True)
    for kind,source in [('drc','pcb'),('erc','sch')]:
        suffix='pcb' if source=='pcb' else 'sch'
        subprocess.run(['kicad-cli',source,kind,f'hardware/voice_pitcher.kicad_{suffix}',
                        '--format','json','-o',str(dest/f'final-{kind}.json')],check=True)
    drc=json.loads((dest/'final-drc.json').read_text())
    erc=json.loads((dest/'final-erc.json').read_text())
    assert not drc['violations'] and not drc['unconnected_items'], 'DRC failed'
    assert not drc.get('schematic_parity'), 'KiCad parity failed'
    assert not any(s['violations'] for s in erc['sheets']), 'ERC failed'
    subprocess.run(['kicad-cli','sch','export','netlist','hardware/voice_pitcher.kicad_sch',
                    '--format','kicadxml','-o','build/voice_pitcher.xml'],check=True)
    tree=ET.parse('build/voice_pitcher.xml'); schematic={}
    for net in tree.findall('./nets/net'):
        name=net.get('name')
        for node in net.findall('node'):
            ref=node.get('ref')
            if not ref.startswith('#'):schematic[(ref,node.get('pin'))]='' if name.startswith('unconnected-') else name
    b=pcb.LoadBoard('hardware/voice_pitcher.kicad_pcb')
    board_parts={fp.GetReference():fp for fp in b.GetFootprints()}
    assert set(board_parts)=={p['ref'] for p in PARTS}
    expected={(p['ref'],pin):net for p in PARTS for pin,net in p['pins'].items()}
    assert {k:v for k,v in schematic.items() if v}==expected, 'Generated schematic does not match design source'
    checked=set()
    for ref,fp in board_parts.items():
        assert fp.GetLayer()==pcb.F_Cu,(ref,'bottom assembly')
        p=next(p for p in PARTS if p['ref']==ref)
        assert abs(pcb.ToMM(fp.GetPosition().x)-p['x'])<.001
        assert abs(pcb.ToMM(fp.GetPosition().y)-p['y'])<.001
        for pad in fp.Pads():
            if not pad.GetNumber():continue  # mechanical shield holes / NPTH
            key=(ref,pad.GetNumber());actual=pad.GetNetname()
            assert actual==expected.get(key,''),(key,'design/PCB mismatch',actual,expected.get(key))
            if key in schematic:assert actual==schematic[key],(key,'schematic/PCB mismatch')
            checked.add(key)
    assert set(expected)<=checked
    edges=[o for o in b.GetDrawings() if o.GetLayer()==pcb.Edge_Cuts]
    xs=[pcb.ToMM(p.x) for o in edges for p in [o.GetStart(),o.GetEnd()]]
    ys=[pcb.ToMM(p.y) for o in edges for p in [o.GetStart(),o.GetEnd()]]
    width,height=max(xs)-min(xs),max(ys)-min(ys)
    assert width==98 and height==98 and b.GetCopperLayerCount()==4
    lengths={}
    for net in ['USB_DP','USB_DM','MCU_USB_DP','MCU_USB_DM','SAI_MCLK','I2S_MCLK','SAI_BCLK','I2S_BCLK']:
        tracks=[t for t in b.GetTracks() if t.GetNetname()==net]
        lengths[net]={'copper_length_mm':round(sum(pcb.ToMM(t.GetLength()) for t in tracks if t.GetClass()=='PCB_TRACK'),4),
                      'vias':sum(t.GetClass()=='PCB_VIA' for t in tracks)}
    report={'status':'CAD_CHECKS_PASS_HARDWARE_UNTESTED','kicad':drc['kicad_version'],
            'erc_violations':0,'drc_violations':0,'unconnected_items':0,
            'netlist_to_pcb_checked_pads':len(checked),'outline_mm':[width,height],
            'copper_layers':4,'assembly_side':'TOP','components':len(PARTS),
            'assembly_counts':dict(Counter(p['assembly'] for p in PARTS)),
            'sourcing_counts':dict(Counter(p['sourcing_status'] for p in PARTS)),
            'track_totals_not_impedance_verification':lengths,
            'production_release':False,'bench_validation':False}
    (dest/'hardware.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
