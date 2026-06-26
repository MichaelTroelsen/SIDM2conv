"""Build a FULL-LENGTH Galway digi tune (vs build_galway_digi_songs.py's clean short
builds). A full multi-minute song's digi can't fit the 20KB bank at full sweep fidelity,
so this uses RLE-compressed records + a flat-capped body (full sweep only for the first
SWEEP_INTRO frames) + an auto-fit drum bank. Tradeoff: the body is lossier and the
per-frame $D418 volume anchor (needed so the SID voices stay audible under the lossy
digi) leaves a faint percussion blip. The clean, no-blip deliverable is the short build
from build_galway_digi_songs.py (its faithful full-sweep digi needs no anchor).
See docs/players/GALWAY.md.

Usage: py -3 bin/build_galway_digi_full.py <sid-stem> <out-stem> <seconds>
       e.g. py -3 bin/build_galway_digi_full.py Arkanoid_alternative_drums Arkanoid_full 145
"""
import os, sys, subprocess, shutil
src=sys.argv[1]; stem=sys.argv[2]; secs=sys.argv[3]; frames=str(int(secs)*50)
common=dict(GALWAY_DIGI_SWEEP='1', GALWAY_DIGI_HYBRID='1', GALWAY_DIGI_RLE='1',
            GALWAY_SWEEP_CAP='1', GALWAY_SWEEP_INTRO='150', GALWAY_NCO_BUDGET='15000', GALWAY_DRUM_DIFFTOL='0.7')
env=dict(os.environ); env.update(common)
r=subprocess.run([sys.executable,'bin/build_galway_digi.py',src,secs,'1'],env=env,capture_output=True,text=True)
print('DIGI:', '\n'.join(l for l in r.stdout.splitlines() if 'sweep' in l or 'drums' in l or 'wrote' in l or 'WARNING' in l) if r.returncode==0 else r.stderr[-900:])
if r.returncode: sys.exit(1)
env2=dict(os.environ); env2.update(common); env2['GALWAY_DIGI_SPIKE']='1'
r=subprocess.run([sys.executable,'bin/build_galway_trace_song.py','SID/Galway_Martin/%s.sid'%src,frames],env=env2,capture_output=True,text=True)
print('SONG:', '\n'.join(l for l in r.stdout.splitlines() if 'FAITHFUL' in l or 'CHECK' in l or 'blob' in l) if r.returncode==0 else r.stderr[-1200:])
if r.returncode: sys.exit(1)
for ext in ('.sf2','.sid'): shutil.copy('out/galway_trace_song'+ext,'out/%s%s'%(stem,ext))
print('-> out/%s.sf2'%stem)
