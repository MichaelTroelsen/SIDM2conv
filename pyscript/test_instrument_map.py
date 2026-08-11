"""Tests for sidm2.instrument_map.

Every case here is one of the ways this technique produces a confidently wrong
answer. The hard-restart and the alias cases in particular are not hypothetical:
the first faked four stable "instruments" on Stinsen's Last_Night.sid in
sid-reference-project, and the second renumbered every instrument of
SF2/Angular.sf2 by +20 during this module's own development.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.instrument_map import (                            # noqa: E402
    COLUMN_MAJOR, ROW_MAJOR, Layout, annotate_dump, build_map, check_declared,
    frame_labels, frames_by_instrument, instrument_labels, key_reliability,
    locate_instrument_table, note_profiles, onsets_with_registers,
    strip_annotation)

GATE = 0x01
TRI = 0x10
NOISE = 0x80


def blank():
    return ({v: {'freq': None, 'wf': None, 'pul': None, 'adsr': None}
             for v in range(3)},
            {'cutoff': None, 'filtctl': None, 'volmode': None})


def frames(n, writes):
    """Build siddump_frames_full()-shaped frames with fill-forward semantics.

    `writes` is {(frame, voice): {reg: value}} — the registers the playroutine
    wrote on that frame. Everything else carries forward, exactly as siddump's
    '....' cells mean "unchanged".
    """
    out = []
    st = [{'freq': None, 'wf': None, 'pul': None, 'adsr': None} for _ in range(3)]
    for f in range(n):
        for v in range(3):
            st[v].update(writes.get((f, v), {}))
        out.append(({v: dict(st[v]) for v in range(3)},
                    {'cutoff': None, 'filtctl': None, 'volmode': None}))
    return out


def note(f, v, adsr, wf=TRI, freq=0x1000, pul=0x800, length=6):
    """One gated note: gate on at f, off at f+length."""
    return {(f, v): {'wf': wf | GATE, 'adsr': adsr, 'freq': freq, 'pul': pul},
            (f + length, v): {'wf': wf}}


def many_notes(count, adsrs, voice=0, step=10, **kw):
    w = {}
    for i in range(count):
        w.update(note(1 + i * step, voice, adsrs[i % len(adsrs)], **kw))
    return w, 1 + count * step + 10


class TestOnsets(unittest.TestCase):

    def test_gate_edge_is_an_onset(self):
        w, n = many_notes(3, [0x1234])
        on = onsets_with_registers(frames(n, w))
        self.assertEqual([o.frame for o in on], [1, 11, 21])
        self.assertTrue(all(o.adsr == 0x1234 for o in on))
        self.assertTrue(all(o.settled for o in on))

    def test_frame0_force_display_is_not_a_gate_edge(self):
        """siddump prints every register on frame 0 whether the playroutine
        wrote it or not, so frame 0 is bus state. A gated waveform sitting there
        must not be counted as a note, and must not hide the real first note."""
        w = {(0, 0): {'wf': TRI | GATE, 'adsr': 0x0F0F, 'freq': 0x1000, 'pul': 0},
             (2, 0): {'wf': TRI}}                    # gate off, still frame 0's
        w.update(note(5, 0, 0x1234))
        on = onsets_with_registers(frames(30, w))
        self.assertEqual([o.frame for o in on], [5])
        self.assertNotIn(0x0F0F, {o.adsr for o in on})

    def test_settle_skips_a_hard_restart(self):
        """Frequency on a sentinel and no waveform selected is the player's
        restart, not the instrument. The sample must walk past it."""
        w = {(1, 0): {'wf': GATE, 'adsr': 0xF00F, 'freq': 0xFFFF, 'pul': 0},
             (2, 0): {'wf': GATE, 'freq': 0xFFFF},
             (3, 0): {'wf': TRI | GATE, 'adsr': 0x2345, 'freq': 0x1000},
             (9, 0): {'wf': TRI}}
        on = onsets_with_registers(frames(20, w))
        self.assertEqual(len(on), 1)
        self.assertEqual(on[0].sample_frame, 3)
        self.assertEqual(on[0].settle_delay, 2)
        self.assertEqual(on[0].adsr, 0x2345)
        self.assertTrue(on[0].settled)


class TestReliability(unittest.TestCase):

    def test_hard_restart_that_never_settles_is_unusable(self):
        """The Last_Night case: a restart that lasts past settle_max gives a
        small, tidy, perfectly stable value set — exactly what the
        distinct-value tests reward — so the unsettled test must run first."""
        w = {}
        for i in range(40):
            f = 1 + i * 10
            w[(f, 0)] = {'wf': GATE, 'adsr': 0xF00F, 'freq': 0xFFFF, 'pul': 0}
            for k in range(1, 9):
                w[(f + k, 0)] = {'wf': GATE, 'freq': 0xFFFF}
            w[(f + 9, 0)] = {'wf': 0x00}
        fr = frames(420, w)
        on = onsets_with_registers(fr)
        v = key_reliability(on, fr)
        self.assertEqual(v.verdict, 'unusable')
        self.assertEqual(v.unsettled, len(on))
        self.assertIn('hard restart', v.why)

    def test_one_adsr_over_every_note_is_degenerate_not_reliable(self):
        w, n = many_notes(40, [0x0A0B])
        fr = frames(n, w)
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'degenerate')
        self.assertFalse(v.verdict == 'reliable')
        self.assertTrue(v.usable)              # usable but uninformative

    def test_too_few_onsets_is_insufficient_data(self):
        w, n = many_notes(9, [0x1111, 0x2222, 0x3333])
        fr = frames(n, w)
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'insufficient-data')
        self.assertFalse(v.usable)

    def test_a_distinct_adsr_per_note_is_unusable(self):
        w, n = many_notes(40, [0x1000 + i for i in range(40)])
        fr = frames(n, w)
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'unusable')
        self.assertIn('computed per note', v.why)

    def test_modulated_envelope_is_unusable(self):
        w = {}
        for i in range(40):
            f = 1 + i * 10
            w.update(note(f, 0, 0x1111 + (i % 3)))
            w[(f + 3, 0)] = {'adsr': 0x9999}        # changed with gate still on
        fr = frames(420, w)
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'unusable')
        self.assertIn('modulates', v.why)

    def test_empty_trace_is_no_trace_not_insufficient_data(self):
        """0 onsets is ambiguous, and the ambiguity matters: a digi player that
        never gates and a file the tracer could not drive look identical from
        the count alone. Pooling them is the empty==empty bug one layer up."""
        fr = frames(200, {})
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'no-trace')
        self.assertFalse(v.measured)

    def test_a_tune_that_gates_but_rarely_is_insufficient_data(self):
        w, n = many_notes(4, [0x1111])
        fr = frames(n, w)
        v = key_reliability(onsets_with_registers(fr), fr)
        self.assertEqual(v.verdict, 'insufficient-data')
        self.assertTrue(v.measured)


class TestLocate(unittest.TestCase):

    OBS = [0x03F8, 0x04F8, 0x02A8, 0x0694, 0x0188, 0x0198]

    def row_major_image(self, base, stride=8, pad=b'\x00'):
        buf = bytearray(pad * 4096)
        for i, a in enumerate(self.OBS):
            buf[base + i * stride] = a >> 8
            buf[base + i * stride + 1] = a & 0xFF
        return bytes(buf)

    def column_major_image(self, base, rows=32, pad=b'\x00'):
        buf = bytearray(pad * 4096)
        for i, a in enumerate(self.OBS):
            buf[base + i] = a >> 8
            buf[base + rows + i] = a & 0xFF
        return bytes(buf)

    def test_row_major_is_found(self):
        c = locate_instrument_table(self.row_major_image(0x300), self.OBS)[0]
        self.assertEqual(c.shape, ROW_MAJOR)
        self.assertEqual(c.base, 0x300)
        self.assertEqual(c.step, 8)
        self.assertEqual(c.hits, len(self.OBS))

    def test_column_major_is_found(self):
        c = locate_instrument_table(self.column_major_image(0x300), self.OBS)[0]
        self.assertEqual(c.shape, COLUMN_MAJOR)
        self.assertEqual(c.base, 0x300)
        self.assertEqual(c.step, 32)
        self.assertEqual(c.hits, len(self.OBS))

    def test_aliases_are_collapsed_not_ranked(self):
        """A stride-N grid explains the same bytes from every base N*k earlier.
        Those are one table, not N candidates, and the survivor is the one whose
        first SOUNDED record is record 0 — an assumption the report states."""
        cands = locate_instrument_table(self.row_major_image(0x300), self.OBS)
        same = [c for c in cands if c.shape == ROW_MAJOR and c.step == 8
                and c.hits == len(self.OBS)]
        self.assertEqual(len(same), 1)
        self.assertEqual(same[0].base, 0x300)

    def test_zero_padding_does_not_manufacture_a_table(self):
        """$00 and $0F line up by luck across a whole payload. An all-$00 image
        must yield nothing at all for observed values that are not $0000."""
        self.assertEqual(locate_instrument_table(bytes(4096), self.OBS), [])

    def test_nothing_found_returns_empty_not_a_guess(self):
        self.assertEqual(
            locate_instrument_table(bytes(b'\xAB' * 4096), self.OBS), [])


class TestCheckDeclared(unittest.TestCase):

    OBS = TestLocate.OBS

    def setUp(self):
        self.data = TestLocate().row_major_image(0x300)
        self.L = Layout(ROW_MAJOR, 0x300, 8, 6, 6, 6, 6)

    def test_all_found_is_confirmed(self):
        v, d = check_declared(self.data, self.L, self.OBS, count=8)
        self.assertEqual(v, 'confirmed')
        self.assertEqual(d['missing'], [])

    def test_a_big_table_matching_a_few_values_is_only_weak(self):
        """One value landing somewhere in a 32-record table says nothing."""
        v, _ = check_declared(self.data, self.L, self.OBS[:2], count=8)
        self.assertEqual(v, 'confirmed-weakly')

    def test_a_minority_miss_is_incomplete_not_layout_wrong(self):
        """9 of 10 does not falsify an address 9 values independently confirm —
        SF2/Angular.sf2, where $0028 is sounded 50 times and declared by neither
        the conversion nor the original."""
        v, d = check_declared(self.data, self.L, self.OBS + [0xDEAD], count=8)
        self.assertEqual(v, 'incomplete')
        self.assertEqual(d['missing'], [0xDEAD])

    def test_a_majority_miss_is_layout_wrong(self):
        v, _ = check_declared(self.data, self.L,
                              self.OBS[:1] + [0xDEAD, 0xBEEF, 0xF00D], count=8)
        self.assertEqual(v, 'layout-wrong')

    def test_base_outside_the_image_is_out_of_range(self):
        v, _ = check_declared(self.data, Layout(ROW_MAJOR, 999999, 8, 6, 6, 6, 6),
                              self.OBS)
        self.assertEqual(v, 'out-of-range')


class TestMap(unittest.TestCase):

    def test_a_shared_envelope_names_every_record_it_matches(self):
        """ADSR is not injective: SF2/Angular.sf2 declares $0694 four times.
        Collapsing that to one index would be a lie."""
        declared = {0x0694: [3, 4, 5, 6], 0x0188: [7]}
        w, n = many_notes(4, [0x0694])
        on = onsets_with_registers(frames(n, w))
        rows, orphans = build_map(declared, on, on)
        row = next(r for r in rows if r.adsr == 0x0694)
        self.assertEqual(row.records, (3, 4, 5, 6))
        self.assertEqual(row.label, '3/4/5/6')
        self.assertEqual(orphans, [])

    def test_an_undeclared_envelope_becomes_an_orphan(self):
        w, n = many_notes(4, [0xABCD])
        on = onsets_with_registers(frames(n, w))
        rows, orphans = build_map({0x0188: [0]}, on, on)
        self.assertEqual([o[0] for o in orphans], [0xABCD])
        self.assertEqual(orphans[0][2], 4)

    def test_untraced_side_is_absent_not_zero(self):
        """'we never played it' and 'we never looked' are different claims."""
        w, n = many_notes(4, [0x0188])
        on = onsets_with_registers(frames(n, w))
        rows, _ = build_map({0x0188: [0]}, on, None)
        self.assertNotIn('we do not', rows[0].verdict)
        self.assertTrue(rows[0].verdict.startswith('sounded'))

    def test_only_the_original_plays_it(self):
        w, n = many_notes(4, [0x0188])
        on = onsets_with_registers(frames(n, w))
        rows, _ = build_map({0x0188: [0]}, on, [])
        self.assertIn('the original plays it, we do not', rows[0].verdict)

    def test_unclaimed_envelopes_get_letters(self):
        w, n = many_notes(4, [0x0188, 0xABCD])
        on = onsets_with_registers(frames(n, w))
        lab = instrument_labels({0x0188: [7]}, on)
        self.assertEqual(lab[0x0188], '7')
        self.assertEqual(lab[0xABCD], 'a')


class TestAnnotate(unittest.TestCase):

    DUMP = ("Load address: $1000\r\n"
            "\r\n"
            "| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul |"
            " Freq Note/Abs WF ADSR Pul | FCut RC Typ V |\r\n"
            "+-------+---------------------------+---------------------------+"
            "---------------------------+---------------+\r\n"
            "|     0 | 1000  C-4 .. 11 1234 800 | .... ... .. .. .... ... |"
            " .... ... .. .. .... ... | 0000 00 Off 0 |\r\n"
            "|     1 | .... ... .. .. .... ... | .... ... .. .. .... ... |"
            " .... ... .. .. .... ... | .... .. ... . |\r\n")

    def test_round_trip_is_byte_exact(self):
        """Stage 4's acceptance: stripping the appended columns returns the
        input byte for byte, CRLF included — `splitlines()` would eat the \\r
        and the test would still pass on a str comparison it had silently
        normalised."""
        w, n = many_notes(2, [0x1234], step=1, length=1)
        on = onsets_with_registers(frames(max(n, 3), w))
        cols, of = frame_labels(on, {0x1234: '7'}, 3)
        annotated = annotate_dump(self.DUMP, cols, of)
        self.assertNotEqual(annotated, self.DUMP)
        self.assertEqual(strip_annotation(annotated), self.DUMP)
        self.assertIn('\r\n', annotated)

    def test_onset_frames_are_starred(self):
        w = dict(note(1, 0, 0x1234, length=1))
        on = onsets_with_registers(frames(4, w))
        cols, of = frame_labels(on, {0x1234: '7'}, 3)
        annotated = annotate_dump(self.DUMP, cols, of).split('\n')
        row1 = next(x for x in annotated if x.startswith('|     1 '))
        self.assertIn('*7', row1)


class TestPerInstrument(unittest.TestCase):

    def test_frames_are_attributed_to_the_sounding_instrument(self):
        w = {}
        w.update(note(1, 0, 0x1111, length=5))
        w.update(note(11, 0, 0x2222, length=5))
        fr = frames(30, w)
        on = onsets_with_registers(fr)
        by = frames_by_instrument(on, {0x1111: '0', 0x2222: '1'}, 30)
        self.assertEqual(min(by[(0, '0')]), 1)
        self.assertEqual(min(by[(0, '1')]), 11)
        self.assertEqual(max(by[(0, '0')]), 10)   # held to the next onset
        self.assertFalse(set(by[(0, '0')]) & set(by[(0, '1')]))

    def test_the_split_sums_back_to_the_whole(self):
        """A split that does not sum back is measuring a different population
        than the headline it sits under."""
        from sidm2.instrument_map import InstrumentScores
        w = {}
        w.update(note(1, 0, 0x1111, length=5))
        w.update(note(11, 0, 0x2222, length=5))
        fr = frames(30, w)
        on = onsets_with_registers(fr)
        cols, _ = frame_labels(on, {0x1111: '0', 0x2222: '1'}, 30)
        sc = InstrumentScores(cols)
        for f in range(30):
            sc.add(0, f, f % 2 == 0)
        self.assertEqual(sc.totals()[0][1], 30)
        self.assertEqual(sum(r[4] for r in sc.rows() if r[0] == 0), 30)
        self.assertIn(InstrumentScores.UNATTRIBUTED,
                      [r[1] for r in sc.rows()])     # frames before note 1

    def test_corrupting_one_instrument_moves_exactly_one_row(self):
        """Stage 5's acceptance: attribution has to be sharp enough that a
        defect confined to one record shows up in one record's number."""
        from sidm2.instrument_map import InstrumentScores
        w = {}
        w.update(note(1, 0, 0x1111, length=5))
        w.update(note(11, 0, 0x2222, length=5))
        w.update(note(21, 0, 0x3333, length=5))
        fr = frames(31, w)
        on = onsets_with_registers(fr)
        cols, _ = frame_labels(on, {0x1111: '0', 0x2222: '1', 0x3333: '2'}, 31)

        def run(broken):
            sc = InstrumentScores(cols)
            for f in range(1, 31):
                sc.add(0, f, cols[0][f] != broken)
            return {r[1]: r[2] for r in sc.rows()}

        clean, dirty = run(None), run('1')
        moved = [k for k in clean if clean[k] != dirty.get(k)]
        self.assertEqual(moved, ['1'])
        self.assertEqual(dirty['1'], 0.0)
        self.assertEqual(dirty['0'], 100.0)

    def test_profiles_separate_the_onset_window_from_the_whole_note(self):
        """A sweep that restarts with the note sits on one onset value however
        far it travels, so an onset-only reading calls a working sweep static."""
        w = dict(note(1, 0, 0x1111, pul=0x100, length=20))
        for k in range(1, 20):
            w[(1 + k, 0)] = {'pul': 0x100 + k * 0x40}
        fr = frames(40, w)
        on = onsets_with_registers(fr)
        p = note_profiles(fr, on)[0x1111]
        self.assertLess(p['pulse_onset'][1] - p['pulse_onset'][0],
                        p['pulse_note'][1] - p['pulse_note'][0])


if __name__ == '__main__':
    unittest.main()
