#!/usr/bin/env python3
"""Complete MCU power fanouts that the plane-aware router leaves open."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for key in ['CACHE','CONFIG','DATA']:os.environ.setdefault('XDG_'+key+'_HOME',str(ROOT/'.tools'/key.lower()))
import pcbnew as p
def finish(b):
    fp=next(f for f in b.GetFootprints() if f.GetReference()=='U1')
    routes={'10':[(100.4,101.5),(100.9,101.2)],'11':[(100.7,102),(101.3,102.3)],
            '27':[(101.5,109.2)],'49':[(112.5,109.2)],'74':[(113.2,97.5)],'99':[(101.5,96.8)]}
    for number,points in routes.items():
        pad=next(x for x in fp.Pads() if x.GetNumber()==number);start=pad.GetPosition()
        for x,y in points:
            end=p.VECTOR2I(p.FromMM(x),p.FromMM(y));t=p.PCB_TRACK(b);t.SetStart(start);t.SetEnd(end);t.SetLayer(p.F_Cu);t.SetWidth(p.FromMM(.2));t.SetNet(pad.GetNet());b.Add(t);start=end
        via=p.PCB_VIA(b);via.SetPosition(start);via.SetWidth(p.F_Cu,p.FromMM(.6));via.SetDrill(p.FromMM(.3));via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetViaType(p.VIATYPE_THROUGH);via.SetNet(pad.GetNet());b.Add(via)
