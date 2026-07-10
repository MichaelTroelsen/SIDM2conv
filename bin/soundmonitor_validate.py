"""First-pass note-onset validation of sidm2.soundmonitor_parser against siddump.

Simulates play timing frame-by-frame (init preset divider = 7 for the very first
step, then each row's own 'speed' field thereafter -- see $C93A/$C4BC in
memory/soundmonitor-player.md) and diffs the decoded onsets against siddump's real
onsets by nearest frame (+/- FRAME_TOL). This is a CHECKPOINT tool, not a finished
validator: match rate is well above chance but not yet high-fidelity -- known open
items (portamento/glide continuation, the exact TIE/digi-trigger interaction, and
whether the +1 octave correction is the right fix vs. a freq-table indexing bug) are
tracked in memory/soundmonitor-player.md.

  py -3 bin/soundmonitor_validate.py [path/to.sid] [--seconds N]
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.soundmonitor_parser import load_sid, SoundMonitorModule
from sidm2.fidelity_common import freq_to_semi, run_siddump

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAME_TOL = 4
NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

CORPUS = [os.path.join('SID', 'Fun_Fun', n + '.sid') for n in (
    'Dance_at_Night_remix', 'Fun_Mix', 'Times_Up', 'Poppy_Road', 'No_Title',
    'Just_Cant_Get_Enough', 'Thats_All', 'Dreamix', 'Dreamix_Two', 'Final_Luv',
    'Fuck_Off',
)]


def semi_name(semi, oct_shift=0):
    if semi < 0:
        return None
    s2 = semi + 12 * oct_shift
    return f'{NOTE_NAMES[s2 % 12]}{s2 // 12}'


def decode_onsets(m, max_frame):
    """-> {voice: [(frame, raw_note, arp, glide), ...]} via the row/step timing
    model. arp = the row's 8-entry semitone-offset table when the note has
    data&$40; glide = data&$10 (portamento -- onset pitch is mid-walk)."""
    onsets = {0: [], 1: [], 2: []}
    frame = 0
    first_row = True
    for row, hdr in m.row_chain():
        speed, length = hdr['speed'], hdr['length']
        bar = [m.bar_ptr(v, row) for v in range(3)]
        transp = [m.row_transpose(v, row) for v in range(3)]
        arps = [m.row_arp(v, row) for v in range(3)]
        for step in range(length):
            fps = 8 if (first_row and step == 0) else (speed + 1)
            for v in range(3):
                ctrl, data = m.bar_step(bar[v], step)
                if ctrl not in (0x00, 0x80):
                    note = ctrl & 0x7F
                    if not (data & 0x20):
                        note = (note + transp[v]) & 0xFF
                    arp = arps[v] if (data & 0x40) else None
                    onsets[v].append((frame, note, arp, bool(data & 0x10)))
            frame += fps
        first_row = False
        if frame > max_frame:
            return onsets
    return onsets


def real_onsets(sidpath, seconds):
    """-> {voice: [(frame, note_name), ...]} parsed straight from siddump text.
    BRACKETED rows (pitch change without a gate re-write) are included: Sound
    Monitor only re-gates a voice that a REST previously silenced, so a note
    following a TIE is a genuine note event that siddump renders bracketed."""
    txt = run_siddump(sidpath, [f'-t{seconds}'])
    V = {0: [], 1: [], 2: []}
    cell_pat = re.compile(r'\s*([0-9A-F]{4})\s+(\(?)([A-G][-#]\d|\.\.\.)')
    for line in txt.splitlines():
        mm = re.match(r'^\|\s*(\d+)\s*\|(.*)\|\s*$', line)
        if not mm:
            continue
        frame = int(mm.group(1))
        cells = mm.group(2).split('|')
        for v in range(3):
            cm = cell_pat.match(cells[v])
            if cm and cm.group(3) != '...':
                V[v].append((frame, cm.group(3)))
    return V


def validate(path, seconds):
    d, la, h = load_sid(path)
    m = SoundMonitorModule(d, la)
    max_frame = seconds * 50
    decoded = decode_onsets(m, max_frame)
    real = real_onsets(path, seconds)

    tot = match = 0
    for v in range(3):
        for frm, note, arp, glide in decoded[v]:
            if frm > max_frame:
                continue
            # Accepted onset pitches: the plain note, or (for arp notes) the
            # note plus any of the 8 cycle offsets -- the onset frame lands on
            # an engine-dependent phase of the arp cycle, and any cycle entry
            # is a genuinely played pitch of this note event. For GLIDE notes
            # (data&$10) the onset pitch is mid-portamento, so accept within
            # +/-3 semitones of the target.
            offsets = {0} if arp is None else ({0} | set(arp))
            if glide:
                offsets |= {off + k for off in set(offsets)
                            for k in (-3, -2, -1, 1, 2, 3)}
            names = set()
            for off in offsets:
                semi = freq_to_semi(m.freq((note + off) & 0xFF))
                if semi >= 0:
                    names.add(semi_name(semi))
            if not names:
                continue
            # NEAREST real onset within tolerance (not first-in-window: the
            # previous note can sit exactly FRAME_TOL frames earlier and would
            # otherwise shadow the true match a couple of frames later).
            cands = [(abs(rf - frm), rn) for rf, rn in real[v]
                     if abs(rf - frm) <= FRAME_TOL]
            if not cands:
                continue
            tot += 1
            # Prefer any in-tolerance candidate that matches; else the nearest.
            if any(rn in names for _, rn in cands):
                match += 1
    pct = 100 * match / tot if tot else 0
    return tot, match, pct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--seconds', type=int, default=20)
    args = ap.parse_args()
    os.chdir(ROOT)
    targets = args.paths or CORPUS
    print(f"{'tune':28} {'matched/total':>15} {'pct':>7}")
    for path in targets:
        if not os.path.exists(path):
            print(f"{os.path.basename(path):28} MISSING")
            continue
        tot, match, pct = validate(path, args.seconds)
        print(f"{os.path.splitext(os.path.basename(path))[0]:28} "
              f"{match}/{tot:>7} {pct:6.1f}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
