#!/usr/bin/env python3
"""Test the actual streaming DSP, including its incremental pitch detector."""
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
BUILD.mkdir(exist_ok=True)
subprocess.run(['cc','-std=c11','-O3','-Wall','-Wextra','-Werror','-Ifirmware',
                'tests/dsp_test.c','firmware/dsp.c','-lm','-o',str(BUILD/'dsp_test')],cwd=ROOT,check=True)
results=[]
for mode,source,expected in [('12',440,880),('-12',440,220),('7',440,440*2**(7/12)),
                             ('-5',440,440*2**(-5/12)),('tune',450,440),('tune',215,220)]:
    path=BUILD/f'audio-{mode}-{source}.f32'
    subprocess.run([str(BUILD/'dsp_test'),mode,str(path),str(source)],check=True,cwd=ROOT)
    data=np.fromfile(path,dtype=np.float32).reshape(-1,2)[48000:]
    assert np.all(np.isfinite(data)) and np.max(np.abs(data))<=1
    assert np.array_equal(data[:,0],data[:,1]), 'stereo coherence'
    assert .1<float(np.sqrt(np.mean(data**2)))<.7, 'unexpected output level'
    x=data[:,0]; fft=np.abs(np.fft.rfft(x*np.hanning(len(x))))
    k=int(np.argmax(fft[1:])+1)
    logs=np.log(np.maximum(fft[k-1:k+2],1e-20))
    delta=.5*(logs[0]-logs[2])/(logs[0]-2*logs[1]+logs[2])
    measured=(k+delta)*48000/len(x)
    cents=float(1200*np.log2(measured/expected))
    assert abs(cents)<15,(mode,source,expected,measured,cents)
    results.append(dict(mode=mode,input_hz=source,target_hz=expected,measured_hz=measured,error_cents=cents))
report={'scope':'Host synthetic tones only; not measured on STM32 or the analog hardware.',
        'tolerance_cents':15,'tests':results}
(BUILD/'checks').mkdir(exist_ok=True)
(BUILD/'checks/dsp-spectral.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
