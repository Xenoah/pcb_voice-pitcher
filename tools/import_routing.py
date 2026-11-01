#!/usr/bin/env python3
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for key in ['CACHE','CONFIG','DATA']:
    os.environ.setdefault('XDG_'+key+'_HOME',str(ROOT/'.tools'/key.lower()))
import pcbnew as p
board=p.LoadBoard(str(ROOT/'hardware/voice_pitcher.kicad_pcb'))
if not p.ImportSpecctraSES(board,str(ROOT/'build/voice_pitcher.ses')):
    raise SystemExit('SES import failed')
board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones())
p.SaveBoard(str(ROOT/'hardware/voice_pitcher.kicad_pcb'),board)
print('Imported routes and refilled planes.')
