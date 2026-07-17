"""Does the emitted Deenen SF2 play the percussion -- on the right voice, at the
right time, in the right order? (audio check)

Why this exists
---------------
`bin/deenen_validate.py` scores the DECODER (onset+pitch vs siddump). It is
structurally BLIND to what `bin/deenen_to_sf2.py` emits -- so the wave/
percussion rows for the $1723 engine (see `DeenenModule.wave_program`) shipped
decoded and emitted but never audio-verified. This closes that gap: build the
SF2 exactly as the builder ships it, wrap it as a PSID probe, siddump it, and
check the real SID output.

It compares PER-FRAME FREQUENCY, not note onsets. The percussion is a
within-note sweep (instr 1: semitones 69,37,26,23,18,11,68 across consecutive
frames, then hold) -- an onset-only comparison, like `bin/mon_sf2_validate.py`
does, cannot see it AT ALL and would report success without testing anything.

What the verdict means
----------------------
For every note the decoder says voice V plays with percussion instrument I, this
walks the frames THAT note occupies, on THAT voice, and compares the pitch run
the SF2 really produces against the run the original engine would produce. A
pitch coming out of some other voice, or some other note, cannot satisfy the
check.

That is the whole point of the rewrite. The first version of this tool pooled
every semitone from all 3 voices across the entire window into ONE set and asked
only "does this pitch appear ANYWHERE?" -- so an unrelated note supplied the
evidence and a PASS meant almost nothing. It reported PASS on Constant_Runner
while that SF2 was missing its entire voice 2 and playing 1.5x too fast. A check
that pools its evidence proves only that the pitch exists in the universe.

Still NOT a fidelity percentage: it audits the percussion streams only, not
pitch/timing of the song as a whole. Quote it as what it is.

  py -3 bin/deenen_sf2_validate.py                     # Constant_Runner
  py -3 bin/deenen_sf2_validate.py SID/deenen/After_the_War.sid 120
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bin'))

from sidm2.deenen_parser import load_sid, DeenenModule          # noqa: E402
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo    # noqa: E402
from sidm2.fidelity_common import (                             # noqa: E402
    fmt_pct, psid_wrap, score_pct, siddump_freq_track, freq_to_semi)
from sidm2.galway_driver11_emitter import emit_driver11_sf2     # noqa: E402
import deenen_to_sf2 as B                                       # noqa: E402

MAX_OFFSET = 24          # driver boot lag, in frames: small and bounded by design


def build_probe(path, subtune=0):
    """Build the SF2 via the BUILDER'S OWN build_song() and wrap it as a PSID.

    Deliberately not a local copy of the assembly: this tool exists to audit the
    file users actually get, and a private rebuild can only drift away from it.
    """
    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune, h)
    song, sequences, orderlists, idx_map = B.build_song(m, subtune)
    drop = B.dropped_orderlist(sequences, orderlists)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return (m, song, idx_map, drop,
            psid_wrap(sf2[2:], sla, 0x1000, 0x1006))


def row_frames(song, nrows):
    """[first real frame of row r] for r in 0..nrows, before the boot offset.

    Driver 11 plays `tempo_value + 1` frames per row (measured -- see
    `GalwayDriver11Song.tempo`), and a tempo CHAIN cycles its values row by row,
    which is how a fractional average speed is expressed. One global tempo
    counter drives all 3 voices, so this mapping is voice-independent.
    """
    chain = (list(song.tempo) if isinstance(song.tempo, (list, tuple))
             else [song.tempo])
    out, f = [0], 0
    for r in range(nrows):
        f += chain[r % len(chain)] + 1
        out.append(f)
    return out


def voice_schedule(m):
    """{voice -> [(row, deenen_instr, dur_rows, note)]} for every note the SF2 plays.

    Mirrors `deenen_to_sf2.voice_rows` row-for-row (same events, same
    stop_on_loop, same rest/sustain row counts) -- it IS the row index the
    builder emitted that note at.
    """
    sched = {}
    for v in range(3):
        ev, ri = [], 0
        for e in m.decode_voice(v, stop_on_loop=True):
            if e['kind'] == 'rest':
                ri += max(1, e['frames'])
                continue
            ev.append((ri, e['instr'], max(1, e['frames']), e['note']))
            ri += 1 + max(0, e['frames'] - 1)
        sched[v] = ev
    return sched


def expected_run(m, di, root_semi, nframes):
    """Per-frame semitones the ORIGINAL engine emits for a note on `di`.

    The engine plays the note's own pitch for exactly ONE frame before the
    stream takes over (observed live on voice1, and independently the same shape
    Future Composer's drums have -- see fc_to_sf2), then one stream step every
    `speed` frames; `$FE` holds the last step forever, `$FF` loops back.
    """
    wp = m.wave_program(di)
    if wp is None or not wp['steps']:
        return None
    out = [root_semi]
    si, guard = 0, 0
    while len(out) < nframes and guard < 4096:
        guard += 1
        if si >= len(wp['steps']):
            out.append(out[-1])                      # ran off the end -> hold
            continue
        kind, val = wp['steps'][si]
        if kind == 'hold':
            out.append(out[-1])
            continue
        if kind == 'loop':
            if val >= si:                            # never advances -> hold
                out.append(out[-1])
                continue
            si = val
            continue
        if kind == 'raw':
            s = freq_to_semi((val << 8) | val)
            if s < 0:                                    # sub-audio = silent frame
                # The builder emits silence as a waveform-off row, which leaves
                # the FREQUENCY register untouched -- so siddump_freq_track (which
                # reads freq, fill-forward) sees the PRIOR pitch carry through,
                # not a drop. Silence is transparent to a freq-based probe: model
                # it as "the previous pitch continues", which is exactly what the
                # register reads. (The original writes freq 0 instead; audibly the
                # same, but not observable the same way -- so we don't pretend to.)
                out.extend([out[-1]] * wp['speed'])
                si += 1
                continue
            semi = max(0, min(95, s))
        else:
            raw_semi = (val & 0x7F) if val >= 0x7F else (root_semi + val) & 0x7F
            semi = max(0, min(95, raw_semi))
        out.extend([semi] * wp['speed'])
        si += 1
    return out[:nframes]


def collapse(seq):
    """[a,a,b,b,b,c] -> [a,b,c]: the pitch RUN, independent of step boundaries."""
    out = []
    for s in seq:
        if not out or out[-1] != s:
            out.append(s)
    return out


def prefix_agrees(got, want, minlen=2):
    """Does the SF2's pitch run agree with the engine's on their common prefix?

    NOT whole-run equality. A percussion note is cut short whenever the next
    note arrives -- musically correct, and verified directly: a full-length note
    reproduces the entire sweep [12,69,37,26,23,18,11,68] while a 2-row note
    stops partway and the very next frame is the following note's pitch. So the
    SF2's run is a PREFIX of the engine's, shortened by the note's real length
    (plus ~1 frame of boot jitter the global offset can't remove per-note). The
    honest question is "do the pitches that DO play match, in order?" -- a wrong
    pitch diverges the prefix and fails; truncation does not.

    `minlen` guards against a vacuous pass: the agreement must reach at least the
    root + the first drum hit (index 1), so "it played the root note and nothing
    else" is NOT counted as reproducing the percussion.
    """
    n = min(len(got), len(want))
    return n >= minlen and got[:n] == want[:n]


def main():
    os.chdir(ROOT)
    path = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit()
            else os.path.join('SID', 'deenen', 'Constant_Runner.sid'))
    args = [a for a in sys.argv[1:] if a.isdigit()]
    secs = int(args[0]) if args else 30
    name = os.path.splitext(os.path.basename(path))[0]

    m, song, idx_map, drop, psid = build_probe(path)
    if not m.plausible() and '--force' not in sys.argv:
        print(f'{name}: the builder REFUSES this file (plausible()=False -- a '
              f'degenerate/filler decode). Its SF2 is not shipped, so auditing '
              f'its percussion audio tests nothing real. Pass --force to probe '
              f'it anyway (informational only).')
        return 0
    perc = {i: m.wave_program(i) for i in B.used_instruments(m)}
    perc = {i: wp for i, wp in perc.items() if wp and wp['raw'] and wp['steps']}
    if not perc:
        print(f'{name}: no RAW/percussion streams -- nothing for this tool to check')
        return 0
    if any(drop):
        print(f'{name}: WARNING orderlist entries dropped by the sequence cap: '
              f'{drop} -- a dropped voice is SILENT and cannot be audited')

    os.makedirs('out', exist_ok=True)
    probe = os.path.join('out', '_deenen_sf2_probe.sid')
    with open(probe, 'wb') as f:
        f.write(psid)

    sched = voice_schedule(m)
    nrows = max((ev[-1][0] + ev[-1][2]) if ev else 0 for ev in sched.values())
    rf = row_frames(song, nrows + 2)
    track = {v: siddump_freq_track(probe, [f'-t{secs}'], v) for v in range(3)}
    last_frame = max(max(t) if t else 0 for t in track.values())

    # Every occurrence of a percussion instrument, per voice, in row space.
    occ = {i: [] for i in perc}
    for v in range(3):
        for (r, di, dur, note) in sched[v]:
            if di in occ:
                occ[di].append((v, r, dur, B._semi(m, note)))

    def check(off):
        """-> per instrument (matched, tested, outside_window, unmeasurable, bad).

        A note where only the root note sounds before it ends -- because the drum
        is silence-led, or the HR gate-off 2 frames before the next note cut it
        off, or a neighbour's drum tail spilled across the row boundary (verified:
        After_the_War's dur-1 note at row 102 reads [37], the prior instr-0 note's
        6th sweep value overrunning its 5-frame note) -- is counted UNMEASURABLE,
        not tested. One such note can't confirm OR deny the drum; abstaining on it
        is the same discipline as score_pct returning None on no evidence. The
        broken-vs-truncated call is made per INSTRUMENT: a genuinely dead drum
        fires on NO occurrence, so tested stays 0 and the NO EVIDENCE branch fails.
        """
        res = {}
        for i, wp in perc.items():
            ok = tested = outside = unmeas = 0
            first_bad = None
            for (v, r, dur, root) in occ[i]:
                f0, f1 = rf[r] + off, rf[min(r + dur, nrows)] + off
                if f1 > last_frame:
                    outside += 1
                    continue
                want = collapse(expected_run(m, i, root, f1 - f0))
                got = collapse([freq_to_semi(track[v].get(f, 0))
                                for f in range(f0, f1)])
                if len(want) < 2 or len(got) < 2:
                    # Only the root note sounded before this note ended -- the
                    # drum got no audible frame here (either structurally, or the
                    # HR gate-off 2 frames before the next note cut it off). One
                    # such note can't confirm OR deny the drum, so abstain. If the
                    # drum is genuinely broken it fires on NO occurrence, every
                    # one is root-only, tested stays 0, and the NO EVIDENCE branch
                    # FAILs -- the broken/truncated distinction is made per
                    # INSTRUMENT, not per note.
                    unmeas += 1
                    continue
                tested += 1
                if prefix_agrees(got, want):
                    ok += 1
                elif first_bad is None:
                    first_bad = (v, r, want, got)
            res[i] = (ok, tested, outside, unmeas, first_bad)
        return res

    # The boot lag is ONE unknown constant for the whole file; fit it, report it.
    best, best_res = None, None
    for off in range(MAX_OFFSET + 1):
        res = check(off)
        tot = sum(r[0] for r in res.values())
        if best is None or tot > best[0]:
            best, best_res = (tot, off), res
    off = best[1]

    print(f'{name}: percussion instruments {sorted(perc)}   tempo={song.tempo} '
          f'(R={m.groove_rate()})   SF2 probe = {len(psid)} bytes, {secs}s '
          f'(to frame {last_frame})')
    print(f'  boot offset fitted to {off} frame(s); each occurrence is checked on '
          f'ITS OWN voice, over ITS OWN frames.')
    print()
    ok_all = True
    t_ok = t_tested = t_out = t_unmeas = 0
    for i in sorted(best_res):
        ok, tested, outside, unmeas, bad = best_res[i]
        t_ok += ok
        t_tested += tested
        t_out += outside
        t_unmeas += unmeas
        semis = collapse([freq_to_semi((v << 8) | v)
                          for k, v in perc[i]['steps'] if k == 'raw'])
        pct = score_pct(ok, tested)
        print(f'  instr {i:2d}  sweep={semis}')
        print(f'            {ok}/{tested} occurrences reproduced ({fmt_pct(pct)}%)'
              f'   {outside} past window, {unmeas} root-only (unmeasurable)')
        if tested == 0 and (outside or unmeas):
            ok_all = False
            first = min((o[1] for o in occ[i]), default=None)
            print(f'            NO EVIDENCE: no resolvable occurrence in range '
                  f'-- widen the window (first plays at frame '
                  f'{rf[first] + off if first is not None else "n/a"})')
        elif bad:
            ok_all = False
            v, r, want, got = bad
            print(f'            MISMATCH e.g. voice {v} row {r} @ frame '
                  f'{rf[r] + off}: want {want}, got {got}')
    print()
    if t_out or t_unmeas:
        print(f'NOTE: {t_out} occurrence(s) past the {secs}s window (widen it to '
              f'reach them) and {t_unmeas} root-only, too short for the drum to '
              f'sound (unmeasurable). Neither is evidence either way; only the '
              f'{t_tested} tested occurrences count.')
    if ok_all and t_tested:
        print(f'PASS: {t_ok}/{t_tested} percussion notes play the decoded sweep on '
              f'the correct voice, over that note\'s own frames.')
    else:
        print(f'FAIL: {t_ok}/{t_tested} percussion notes reproduced. The SF2 does '
              f'not play what the decode says, or there was nothing to test.')
    return 0 if (ok_all and t_tested) else 1


if __name__ == '__main__':
    sys.exit(main())
