#!/usr/bin/env python3
"""Add solid reference planes and short power fanouts before signal routing."""
import os,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for key in ['CACHE','CONFIG','DATA','STATE']:
    os.environ.setdefault('XDG_'+key+'_HOME',str(ROOT/'.tools'/key.lower()))
import pcbnew as p
board=p.LoadBoard(str(ROOT/'hardware/placement.kicad_pcb'))
mm=p.FromMM
point=lambda x,y:p.VECTOR2I(mm(x),mm(y))
for netname,layer in [('GND',p.In1_Cu),('+3V3',p.In2_Cu)]:
    zone=p.ZONE(board);zone.SetLayer(layer);zone.SetNet(board.FindNet(netname))
    zone.SetLocalClearance(mm(.2));zone.SetThermalReliefGap(mm(.3));zone.SetThermalReliefSpokeWidth(mm(.3))
    zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
    poly=zone.Outline();poly.NewOutline()
    for x,y in [(50.5,50.5),(147.5,50.5),(147.5,147.5),(50.5,147.5)]:poly.Append(mm(x),mm(y))
    board.Add(zone)
pads=[pad for fp in board.GetFootprints() for pad in fp.Pads()]
vias=[];segments=[];missed=[];used=set()
def point_segment(px,py,ax,ay,bx,by):
    dx,dy=bx-ax,by-ay
    t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(px-ax-t*dx,py-ay-t*dy)
def within_rect(x,y,rect,margin):
    return rect[0]-margin <= x <= rect[2]+margin and rect[1]-margin <= y <= rect[3]+margin
bounds=[]
for pad in pads:
    bb=pad.GetBoundingBox()
    bounds.append((pad,(p.ToMM(bb.GetLeft()),p.ToMM(bb.GetTop()),p.ToMM(bb.GetRight()),p.ToMM(bb.GetBottom()))))
for pad in pads:
    if pad.GetNetname() not in ['GND','+3V3'] or pad.GetAttribute()!=p.PAD_ATTRIB_SMD:continue
    x,y=p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y)
    if (x,y,pad.GetNetname()) in used:continue
    used.add((x,y,pad.GetNetname()))
    fp=pad.GetParentFootprint();cx,cy=p.ToMM(fp.GetPosition().x),p.ToMM(fp.GetPosition().y)
    angle=math.atan2(y-cy,x-cx)
    found=None
    for distance in [.9,1.2,1.5,1.8,2.1,2.5,3]:
        for step in [0,1,-1,2,-2,3,-3,4,5,-5,6,-6,7,-7,8]:
            a=angle+step*math.pi/8
            vx,vy=round(x+distance*math.cos(a),3),round(y+distance*math.sin(a),3)
            if not (51<vx<147 and 51<vy<147):continue
            if any(within_rect(vx,vy,b,.5) for other,b in bounds):continue
            if any((vx-ox)**2+(vy-oy)**2<.85**2 for ox,oy,_ in vias):continue
            if any(net!=pad.GetNetname() and (point_segment(vx,vy,ax,ay,bx,by)<.51 or
                any(point_segment(x+(vx-x)*t/24,y+(vy-y)*t/24,ax,ay,bx,by)<.41 for t in range(25)))
                for ax,ay,bx,by,net in segments):continue
            if any(net!=pad.GetNetname() and point_segment(ox,oy,x,y,vx,vy)<.51 for ox,oy,net in vias):continue
            safe=True
            for other,b in bounds:
                if other.GetNetname()==pad.GetNetname():continue
                # Conservative pad AABB with track-halfwidth + clearance.
                if any(within_rect(x+(vx-x)*t/24,y+(vy-y)*t/24,b,.26) for t in range(25)):
                    safe=False;break
            if safe:
                found=(vx,vy);break
        if found:break
    if not found:
        missed.append((fp.GetReference(),pad.GetNumber(),pad.GetNetname()));continue
    vx,vy=found
    via=p.PCB_VIA(board);via.SetPosition(point(vx,vy));via.SetWidth(p.F_Cu,mm(.6));via.SetDrill(mm(.3))
    via.SetViaType(p.VIATYPE_THROUGH);via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(pad.GetNet());board.Add(via)
    trace=p.PCB_TRACK(board);trace.SetStart(pad.GetPosition());trace.SetEnd(point(vx,vy))
    trace.SetWidth(mm(.2));trace.SetLayer(p.F_Cu);trace.SetNet(pad.GetNet());board.Add(trace)
    vias.append((vx,vy,pad.GetNetname()))
    segments.append((x,y,vx,vy,pad.GetNetname()))
from finish_board import finish
finish(board)
board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones())
p.SaveBoard(str(ROOT/'hardware/voice_pitcher.kicad_pcb'),board)
assert p.ExportSpecctraDSN(board,str(ROOT/'build/voice_pitcher.dsn'))
dsn=ROOT/'build/voice_pitcher.dsn'
text=dsn.read_text()
for layer in ['In1.Cu','In2.Cu']:
    text=text.replace('(layer '+layer+'\n      (type signal)', '(layer '+layer+'\n      (type power)')
dsn.write_text(text)
print('Power fanouts:',len(vias),'remaining:',missed)
