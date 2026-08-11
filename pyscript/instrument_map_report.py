#!/usr/bin/env python3
"""Instrument map: which SF2 instrument is sounding on each siddump frame.

    py -3 pyscript/instrument_map_report.py orig.sid [converted.sf2] [options]

Reads note onsets out of a register trace of the ORIGINAL, keys them by ADSR
($D405/$D406 — in many players a verbatim per-instrument copy), locates the
converted SF2's instrument table BY SEARCH against those values, and reports
what each side actually sounds per instrument.

The first section is the only one that is always printed: whether ADSR
identifies an instrument in this file at all. When it does not, no table is
emitted — see sidm2/instrument_map.py for the three ways that happens and the
files that produced each.

See docs/plans/INSTRUMENT_MAP_PLAN.md.
"""
import argparse
import json
import os
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')      # em-dashes survive redirection
    except (AttributeError, ValueError):
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (                          # noqa: E402
    psid_wrap, run_siddump, siddump_frames_full)
from sidm2.instrument_map import (                           # noqa: E402
    COLUMN_MAJOR, PROFILE_FRAMES, ROW_MAJOR, Layout, annotate_dump, build_map,
    check_declared, frame_labels, instrument_labels, key_reliability,
    locate_instrument_table, note_profiles, onsets_with_registers, wave_name)


def _trace_sf2(path, secs, init, play):
    """siddump frames for an .sf2/.prg, wrapped as a PSID so the tracer can
    drive it. Returns (frames, tmp_path) — the caller unlinks."""
    data = open(path, 'rb').read()
    if path.lower().endswith('.sid'):
        return siddump_frames_full(path, ['-t%d' % secs]), None
    load = data[0] | (data[1] << 8)
    fd, tmp = tempfile.mkstemp(suffix='.sid')
    os.close(fd)
    with open(tmp, 'wb') as f:
        f.write(psid_wrap(data[2:], load, init, play))
    return siddump_frames_full(tmp, ['-t%d' % secs]), tmp


def _hex(a):
    return "$%04X" % a


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('original', help='the original .sid')
    ap.add_argument('converted', nargs='?', help='our .sf2 (or .sid/.prg)')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('--init', default='0x1000', help='converted driver init (default 0x1000)')
    ap.add_argument('--play', default='0x1003', help='converted driver play (default 0x1003)')
    ap.add_argument('--declared', help='skip the search: instrument table address, e.g. 0x1A6B')
    ap.add_argument('--shape', choices=[ROW_MAJOR, COLUMN_MAJOR], default=ROW_MAJOR,
                    help='table shape for --declared (default row-major)')
    ap.add_argument('--step', type=int, default=8,
                    help='record stride (row-major) or column delta (column-major) for --declared')
    ap.add_argument('--count', type=int, default=32, help='records to read (default 32)')
    ap.add_argument('--settle-max', type=int, default=4)
    ap.add_argument('--min-onsets', type=int, default=30)
    ap.add_argument('--annotate', metavar='FILE',
                    help='write siddump with Ins1/Ins2/Ins3 columns appended here')
    ap.add_argument('--json', action='store_true', help='emit the raw result object')
    ap.add_argument('-o', '--out', help='write the Markdown here instead of stdout')
    a = ap.parse_args(argv)

    frames = siddump_frames_full(a.original, ['-t%d' % a.seconds])
    onsets = onsets_with_registers(frames, a.settle_max)
    verdict = key_reliability(onsets, frames, a.min_onsets)
    observed = sorted({o.adsr for o in onsets})

    L, layout_verdict, layout_detail, cands = None, 'unverifiable', {}, []
    declared, rows, orphans = {}, [], []
    ours_onsets = None
    tmp = None
    if a.converted and verdict.usable:
        data = open(a.converted, 'rb').read()
        load = data[0] | (data[1] << 8)
        if a.declared:
            base = int(a.declared, 0) - load + 2
            L = Layout(a.shape, base, a.step, a.count, 0, len(observed), 0)
        else:
            cands = locate_instrument_table(data, observed)
            L = cands[0] if cands else None
        layout_verdict, layout_detail = check_declared(data, L, observed, a.count)
        if L is not None:
            declared = L.read(data, a.count)
        try:
            uf, tmp = _trace_sf2(a.converted, a.seconds, int(a.init, 0), int(a.play, 0))
            ours_onsets = onsets_with_registers(uf, a.settle_max)
        except Exception as e:                                # noqa: BLE001
            print("warning: could not trace %s (%s)" % (a.converted, e),
                  file=sys.stderr)
        rows, orphans = build_map(declared, onsets, ours_onsets)

    profiles = note_profiles(frames, onsets) if verdict.usable else {}

    if a.json:
        out = {
            'original': a.original, 'converted': a.converted,
            'seconds': a.seconds, 'frames': len(frames),
            'key': {'verdict': verdict.verdict, 'why': verdict.why,
                    'onsets': verdict.onsets, 'distinct': verdict.distinct,
                    'modulated': verdict.modulated, 'unsettled': verdict.unsettled,
                    'ratio': verdict.ratio, 'mod_ratio': verdict.mod_ratio,
                    'settle_delays': verdict.settle_delays},
            'layout': (None if L is None else
                       {'shape': L.shape, 'base': L.base, 'step': L.step,
                        'hits': L.hits, 'total': L.total, 'span': L.span}),
            'layout_verdict': layout_verdict,
            'layout_detail': {k: v for k, v in layout_detail.items()
                              if k in ('why',)} | {
                'missing': ["$%04X" % m for m in layout_detail.get('missing', [])]},
            'map': [{'records': list(r.records), 'adsr': "$%04X" % r.adsr,
                     'orig_wave': wave_name(r.orig_wave), 'orig_notes': r.orig_notes,
                     'ours_wave': wave_name(r.ours_wave), 'ours_notes': r.ours_notes,
                     'verdict': r.verdict} for r in rows],
            'orphans': [{'adsr': "$%04X" % x, 'wave': wave_name(w), 'notes': n}
                        for x, w, n in orphans],
        }
        text = json.dumps(out, indent=2)
    else:
        text = "\n".join(_markdown(a, frames, onsets, verdict, observed, L, cands,
                                   layout_verdict, layout_detail, declared, rows,
                                   orphans, profiles, ours_onsets))

    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text + "\n")
        print("wrote %s" % a.out)
    else:
        print(text)

    if a.annotate and verdict.usable:
        labels = instrument_labels(declared, onsets)
        cols, of = frame_labels(onsets, labels, len(frames))
        dump = run_siddump(a.original, ['-t%d' % a.seconds])
        open(a.annotate, 'w', encoding='utf-8').write(annotate_dump(dump, cols, of))
        print("wrote %s" % a.annotate, file=sys.stderr)

    if tmp:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    return 0


def _runs(idx):
    """[0,1,2,5,7,8] -> '0-2, 5, 7-8'."""
    out, i = [], 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and idx[j + 1] == idx[j] + 1:
            j += 1
        out.append(str(idx[i]) if j == i else "%d-%d" % (idx[i], idx[j]))
        i = j + 1
    return ", ".join(out)


def _table(rows, head):
    if not rows:
        return ["_(none)_", ""]
    out = ["| " + " | ".join(head) + " |",
           "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    out.append("")
    return out


def _markdown(a, frames, onsets, verdict, observed, L, cands, layout_verdict,
              layout_detail, declared, rows, orphans, profiles, ours_onsets):
    out = ["# %s — instrument map" % os.path.basename(a.original), "",
           "%d frames (%ds), %d note onsets. Registers are read on the first "
           "*settled* frame within %d of each gate edge, not on the edge itself: "
           "the edge can still hold a hard restart, which is the player's "
           "transition and not any instrument."
           % (len(frames), a.seconds, len(onsets), a.settle_max), ""]

    out += ["## Is ADSR an instrument key in this file?", "",
            "**`%s`** — %s" % (verdict.verdict, verdict.why), "",
            "sampled at: %s (onset+N, %s)" % (
                ", ".join("+%s x%d" % (k, v) for k, v in
                          sorted(verdict.settle_delays.items())) or "n/a",
                "a delay above +1 is that player's hard-restart length"), ""]
    if not verdict.usable:
        out += ["No mapping table is emitted. That is the result, not a failure "
                "to produce one — see `sidm2/instrument_map.py` for the files "
                "each verdict was calibrated against.", ""]
        return out

    if a.converted:
        out += ["## Where the instrument table is", ""]
        if a.declared:
            out.append("Declared: `%s`, %s, step %d." % (a.declared, a.shape, a.step))
        elif cands:
            out.append("Located by search against the %d observed envelopes — "
                       "no address was supplied. `span` is the record-index "
                       "spread of the matches; a real grid is tight, and "
                       "`$00`/`$0F` line up by luck across a whole payload."
                       % len(observed))
            out.append("")
            data = open(a.converted, 'rb').read()
            load = data[0] | (data[1] << 8)
            out += _table([[i + 1, c.shape, "$%04X" % c.address(load), c.step,
                            "%d/%d" % (c.hits, c.total), c.span]
                           for i, c in enumerate(cands[:5])],
                          ["#", "shape", "address", "step", "hits", "span"])
        else:
            out.append("**No candidate layout explains 2 or more of the "
                       "observed envelopes.** Either this file's instrument "
                       "records do not carry ADSR verbatim, or the table is "
                       "computed rather than stored.")
        if len(cands) > 1 and cands[1].hits == cands[0].hits:
            # A tie on hits is a real ambiguity, and whether it MATTERS is a
            # different question from whether it exists: two candidates that
            # assign the same records to the same envelopes give the same map,
            # and the reader should be told which case this is rather than left
            # to compare five addresses by eye. SF2/Beast.sf2 is the benign
            # kind -- $1B3D (the driver's 8-byte Laxity records) and $25B0 (a
            # 6-byte editor-side copy) list the same envelopes in the same
            # order, so the mapping is identical either way.
            data = open(a.converted, 'rb').read()
            m0 = {k: v for k, v in cands[0].read(data, a.count).items()
                  if k in set(observed)}
            m1 = {k: v for k, v in cands[1].read(data, a.count).items()
                  if k in set(observed)}
            out += ["", "Candidates 1 and 2 both explain %d of %d. The mapping "
                    "below uses candidate 1; under candidate 2 the record "
                    "assignment is **%s**."
                    % (cands[0].hits, cands[0].total,
                       "identical" if m0 == m1 else "DIFFERENT, so the "
                       "instrument numbers below are not settled by the trace "
                       "alone"), ""]
        out += ["", "Verdict: **`%s`** — %s" % (layout_verdict,
                                                layout_detail.get('why', '')), ""]
        if layout_detail.get('missing'):
            out += ["Sounded by the original, absent from the table: %s"
                    % ", ".join(_hex(m) for m in layout_detail['missing']), ""]

        out += ["## Mapping", ""]
        if ours_onsets is None:
            out += ["_The converted file was not traced, so the `ours` columns "
                    "are absent rather than zero — \"we never played it\" and "
                    "\"we never looked\" are different claims._", ""]
        live = [r for r in rows if r.orig_notes or r.ours_notes]
        dead = [r for r in rows if not (r.orig_notes or r.ours_notes)]
        live.sort(key=lambda r: r.records[0])
        out += _table([[r.label, _hex(r.adsr), wave_name(r.orig_wave),
                        r.orig_notes, wave_name(r.ours_wave), r.ours_notes,
                        r.verdict] for r in live],
                      ["instr", "ADSR", "orig wave", "orig notes", "our wave",
                       "our notes", "verdict"])
        if dead:
            # Never listed row by row. Reading `--count` records past the real
            # end of a table manufactures dozens of "unused both sides" rows out
            # of whatever follows it, and a reader cannot tell those from a
            # genuinely unused instrument slot.
            idx = sorted(i for r in dead for i in r.records)
            out += ["%d of the %d records read are sounded by neither side "
                    "(%s). Some of those are real unused slots and some are "
                    "whatever follows the table — `--count` is a read length, "
                    "not a detected instrument count."
                    % (len(idx), a.count, _runs(idx)), ""]

        if orphans:
            ours_n = {}
            if ours_onsets is not None:
                for o in ours_onsets:
                    ours_n[o.adsr] = ours_n.get(o.adsr, 0) + 1
            both = [x for x, _, n in orphans if ours_n.get(x, 0) == n]
            out += ["### Envelopes nothing in the table declares", "",
                    "Sounded by the original under an ADSR no record carries. "
                    "The `ours` column is what separates a **conversion gap** "
                    "from a **blind spot in the key**: an envelope both sides "
                    "sound the same number of times is not something we failed "
                    "to convert, it is something the player writes from outside "
                    "its instrument records — a sequence command, or a constant "
                    "in the driver.", ""]
            out += _table([[_hex(x), wave_name(w), n,
                            (ours_n.get(x, 0) if ours_onsets is not None else "—")]
                           for x, w, n in orphans],
                          ["ADSR", "waveform", "orig notes", "our notes"])
            if both and len(both) == len(orphans):
                out += ["%s sounded identically by both sides, so %s a "
                        "conversion defect."
                        % ("Both are" if len(both) == 2 else
                           ("It is" if len(both) == 1 else "All %d are" % len(both)),
                           "it is not" if len(both) == 1 else "none of them is"),
                        ""]

    out += ["## What the original does, per instrument", "",
            "One row per sounded envelope, over the first %d frames of each note. "
            "*pulse at onset* is the band those frames cover; *over the note* is "
            "the band between one note and the next — a sweep that restarts with "
            "the note sits on one onset value however far it travels, so an "
            "onset-only reading calls a working sweep static." % PROFILE_FRAMES, ""]
    prows = []
    label = {}
    for adsr, recs in declared.items():
        label[adsr] = "/".join(str(r) for r in recs)
    for adsr in sorted(profiles, key=lambda k: -profiles[k]['notes']):
        p = profiles[adsr]
        seq = " ".join(wave_name(w) if w else "-" for w in p['waves'])
        po = ("$%03X-$%03X" % p['pulse_onset'] if p['pulse_onset'] and
              p['pulse_onset'][0] != p['pulse_onset'][1]
              else ("$%03X" % p['pulse_onset'][0] if p['pulse_onset'] else "—"))
        pn = ("$%03X-$%03X" % p['pulse_note'] if p['pulse_note'] and
              p['pulse_note'][0] != p['pulse_note'][1]
              else ("$%03X" % p['pulse_note'][0] if p['pulse_note'] else "—"))
        prows.append([label.get(adsr, "—"), _hex(adsr), p['notes'], seq, po, pn,
                      p['pitch_fall'],
                      p['gate_off'] if p['gate_off'] is not None else "held"])
    out += _table(prows, ["instr", "ADSR", "notes", "waveform per frame",
                          "pulse at onset", "over the note", "pitch fall",
                          "gate off after"])

    out += ["---", "",
            "This is a register comparison, not a sound comparison: it sees a "
            "wrong sustain or an invented hard restart, and cannot see an "
            "envelope that is right but arrives three frames late. A register "
            "trace localises; it does not adjudicate.", ""]
    return out


if __name__ == '__main__':
    sys.exit(main())
