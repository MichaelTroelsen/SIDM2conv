"""Does the emitted Deenen SF2 actually PLAY the percussion? (audio check)

Why this exists
---------------
`bin/deenen_validate.py` scores the DECODER (onset+pitch vs siddump). It is
structurally BLIND to what `bin/deenen_to_sf2.py` emits -- so the wave/
percussion rows added for the $1723 engine (see `DeenenModule.wave_program`)
were shipped decoded and emitted but NEVER audio-verified. This closes that
gap: build the SF2, wrap it as a PSID probe, siddump it, and check the real
SID output.

It deliberately compares PER-FRAME FREQUENCY, not note onsets. The percussion
is a within-note sweep (instr 1: semitones 69,37,26,23,18,11,68 across
consecutive frames, then hold) -- an onset-only comparison, like
`bin/mon_sf2_validate.py` does, cannot see it AT ALL and would report success
without testing anything.

The check is deliberately one-directional and cheap: it asks whether the
drum's characteristic absolute pitches actually COME OUT of the built SF2.
That is falsifiable (broken wave rows -> the pitches never appear) without
needing to solve Driver 11 boot-offset alignment for a fair whole-song diff.
It is NOT a fidelity percentage and must not be quoted as one.

  py -3 bin/deenen_sf2_validate.py                     # Constant_Runner
  py -3 bin/deenen_sf2_validate.py SID/deenen/After_the_War.sid
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bin'))

from sidm2.deenen_parser import load_sid, DeenenModule          # noqa: E402
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo    # noqa: E402
from sidm2.fidelity_common import (                             # noqa: E402
    psid_wrap, siddump_freq_track, freq_to_semi)
from sidm2.galway_to_driver11 import GalwayDriver11Song         # noqa: E402
from sidm2.galway_driver11_emitter import (                     # noqa: E402
    emit_driver11_sf2, segment_track)
import deenen_to_sf2 as B                                       # noqa: E402


def build_probe(path, subtune=0):
    """Build the SF2 exactly as deenen_to_sf2.main() does, wrapped as a PSID."""
    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune, h)
    used = B.used_instruments(m)
    instr_rows, wave_table, pulse_table, idx_map = B.build_instruments(m, used)
    seq_index, sequences, orderlists = {}, [], [[], [], []]
    for v in range(3):
        for pk in segment_track(B.voice_rows(m, v, idx_map)):
            i = seq_index.get(pk)
            if i is None:
                i = len(sequences)
                seq_index[pk] = i
                sequences.append(pk)
            orderlists[v].append(i)
    song = GalwayDriver11Song(
        instruments=instr_rows, wave_table=wave_table, pulse_table=pulse_table,
        tracks=[], tempo=1, pitch_base=0, subtune=subtune)
    sf2 = emit_driver11_sf2(song, sequences=sequences, orderlists=orderlists)
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    return m, wave_table, psid_wrap(sf2[2:], sla, 0x1000, 0x1006)


def expected_percussion(m):
    """{instr -> [absolute semitone, ...]} for every RAW (percussion) stream.

    Only USED instruments: build_instruments emits wave rows for those alone,
    so an unused record's stream is never in the SF2 and asking whether the
    SF2 plays it is a question about nothing. (Scanning all 32 records also
    walks unused slots whose arp index runs off into unrelated bytes -- e.g.
    Constant_Runner's record 21 decodes to 64 unterminated steps including a
    semitone of -1, i.e. silence. That is garbage, not a defect to report.)
    """
    out = {}
    for i in B.used_instruments(m):
        wp = m.wave_program(i)
        if not wp or not wp['raw']:
            continue
        semis = [freq_to_semi((v << 8) | v)
                 for k, v in wp['steps'] if k == 'raw']
        if semis:
            out[i] = semis
    return out


def main():
    os.chdir(ROOT)
    path = (sys.argv[1] if len(sys.argv) > 1
            else os.path.join('SID', 'deenen', 'Constant_Runner.sid'))
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    name = os.path.splitext(os.path.basename(path))[0]

    m, wave_table, psid = build_probe(path)
    perc = expected_percussion(m)
    if not perc:
        print(f'{name}: no RAW/percussion streams -- nothing for this tool to check')
        return 0

    os.makedirs('out', exist_ok=True)
    probe = os.path.join('out', '_deenen_sf2_probe.sid')
    with open(probe, 'wb') as f:
        f.write(psid)

    # every semitone the built SF2 actually emits, across all 3 voices
    heard = set()
    for v in range(3):
        for fr, fq in siddump_freq_track(probe, [f'-t{secs}'], v).items():
            s = freq_to_semi(fq)
            if s >= 0:
                heard.add(s)

    print(f'{name}: percussion instruments {sorted(perc)}   '
          f'SF2 probe = {len(psid)} bytes, {secs}s')
    print()
    ok = True
    for i, semis in sorted(perc.items()):
        want = sorted(set(semis))
        miss = [s for s in want if s not in heard]
        # the LAST step is the sustain the $FE holds on -- the most audible one
        verdict = 'OK  every pitch heard' if not miss else f'MISSING {miss}'
        if miss:
            ok = False
        print(f'  instr {i:2d}  steps={semis}')
        print(f'            -> {verdict}')
    print()
    if ok:
        print('PASS: every percussion pitch the decoder expects is present in the '
              'built SF2\'s real SID output.')
        print('NOTE: this proves the wave rows FIRE and produce the right pitches. '
              'It is NOT a fidelity %, and it does not check timing/ordering.')
    else:
        print('FAIL: the built SF2 never emits some decoded percussion pitches -- '
              'the wave rows are not doing what the decode says.')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
