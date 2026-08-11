"""Instrument attribution: joining a player's instrument records to the trace.

Every other instrument-level fact in this repo comes from the player's own
instrument table — bytes located by a disassembly or by a constant, then argued
about. This reads the other end: what `$D400-$D418` actually holds on the frame
each note begins, grouped by ADSR.

The technique is h2g's (`python/instrmap.py`, Rob Hubbard -> GoatTracker), by way
of `sid-reference-project`'s `scripts/dev/instrument-map.js` which generalised it
across 61 HVSC player families. It rests on one property: in many players
`$D405`/`$D406` is a **verbatim per-instrument copy** of the instrument record,
so it identifies an instrument where waveform cannot (several instruments share
one) and pulse cannot (a swept width has no single value). h2g measured that at
"0 of 1635 corpus records differ" — **on one player family**.

That property is not a general law, which is why `key_reliability` runs before
anything else and can refuse to emit a map at all. Three hazards it exists for,
all of which produced confidently wrong output somewhere before being caught:

  H1  A multi-frame hard restart (Laxity/JCH NewPlayer drives frequency to
      $FFFF, clears the waveform and writes a restart envelope) makes a fixed
      onset+1 sample read the RESTART on every note. On Stinsen's Last_Night.sid
      that produced four tidy, perfectly stable "instruments" whose ADSR values
      appear nowhere in the payload. Hence `settled`, and hence the
      unsettled-ratio test running BEFORE the distinct-value tests — a hard
      restart is exactly the small tidy value set those tests reward.

  H2  siddump force-displays every register on frame 0 whatever the playroutine
      did, so frame 0 is bus state, not a write. Frame 0 is never an onset here;
      it is only ever the `previous` half of an edge. See `score_pct` /
      `exercised` in `fidelity_common` for the same trap one layer down.

  H3  The key does not always exist. Across a 27-file spread in
      sid-reference-project: 12 reliable, 5 degenerate, 3 suspect, 7
      insufficient-data. A digi player never gates at all.

No player knowledge lives here, and no table address is assumed: the instrument
table is LOCATED BY SEARCH against the observed values, because this repo has
already shipped the other bug (commit 80b5a72, "Driver 11 orderlists came from a
hardcoded Laxity file offset") and because reading SF2/Angular.sf2 at Driver 11's
documented $1A03 matches 0 of 10 observed envelopes — that file uses the Laxity
driver, whose table is at $1A6B.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# The frame after the onset is where h2g samples. Anything past this and a short
# note's release starts leaking into the sample; anything less and a player with
# a hard restart is sampled mid-restart. 4 covers every restart length seen in
# this repo's corpus (Laxity settles at +1 on 347 of 347 Angular onsets; the
# figure is reported per file in `sampled at` because it is a fact worth having).
SETTLE_MAX = 4

# A frequency the player is using as a sentinel rather than a pitch. Both ends of
# the range because the hard restarts in this corpus use both.
FREQ_SENTINELS = frozenset((0x0000, 0xFFFF))

# Pulse widths are swept, so an exact value would split one instrument into
# dozens. A 12-bit register in sixteenths is coarse enough to be stable and fine
# enough to tell a narrow pulse from a square.
PULSE_BUCKET = 0x100

# Frames of each note to profile. Long enough to cover a two-frame noise tick and
# a short drum sweep; deliberately NOT long enough to characterise a slow pulse
# program, which is why `note_profiles` also reports the whole-note band.
PROFILE_FRAMES = 8

# Below this, no verdict is a judgement — too few onsets to tell a per-instrument
# constant from a coincidence.
MIN_ONSETS = 30

WAVE_BITS = ((0x80, "noise"), (0x40, "pulse"), (0x20, "saw"), (0x10, "tri"))

ROW_MAJOR = "row-major"
COLUMN_MAJOR = "column-major"


def wave_name(w):
    """$D404's top nibble as a readable class, or '$XX' if it is nothing."""
    if w is None:
        return "-"
    names = [n for bit, n in WAVE_BITS if w & bit]
    return "+".join(names) if names else "$%02X" % w


# ---------------------------------------------------------------------------
# 1. Onsets, sampled where the player has settled
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Onset:
    """One note start, with the registers as they stand once the player settles.

    `frame` is the gate edge; `sample_frame` is where the registers were read.
    `settled` is False when no frame within `settle_max` satisfied all three
    settle conditions — the sample is then a fallback at frame+1 and is very
    probably the player's transition rather than any instrument (H1).
    """
    voice: int
    frame: int
    sample_frame: int
    settled: bool
    adsr: int
    wave_class: int
    pulse_bucket: int
    freq: int

    @property
    def settle_delay(self):
        return self.sample_frame - self.frame


def onsets_with_registers(frames, settle_max=SETTLE_MAX):
    """Gate 0->1 edges, each carrying the registers of its first settled frame.

    `frames` is `fidelity_common.siddump_frames_full()`'s output.

    A frame is settled when the gate is still on, a real waveform is selected,
    and the frequency is off the sentinels. The first such frame within
    `settle_max` of the edge is the sample; failing that the sample falls back to
    edge+1 and `settled` is False, which `key_reliability` counts (H1).

    The scan starts at frame 1, so frame 0's forced display can never be an onset
    on its own (H2) — it is only ever the `previous` half of an edge.
    """
    out = []
    n = len(frames)
    for v in range(3):
        for f in range(1, n):
            cur = frames[f][0][v]
            if cur['wf'] is None:
                continue
            # A voice with no $D404 value yet is not gated. Requiring a non-None
            # previous instead would drop the FIRST note of a voice whose gate-on
            # is its own first write -- which siddump's frame-0 force display
            # hides on real input and a synthetic frame list does not.
            prev = frames[f - 1][0][v]['wf'] or 0
            if (prev & 1) or not (cur['wf'] & 1):
                continue
            at, settled = min(f + 1, n - 1), False
            for k in range(1, settle_max + 1):
                if f + k >= n:
                    break
                s = frames[f + k][0][v]
                if s['wf'] is None or not (s['wf'] & 1):
                    break                                # gate released: over
                if (s['wf'] & 0xF0) == 0:
                    continue                             # no waveform yet
                if s['freq'] in FREQ_SENTINELS:
                    continue                             # still in the restart
                at, settled = f + k, True
                break
            s = frames[at][0][v]
            pul = s['pul']
            out.append(Onset(
                voice=v, frame=f, sample_frame=at, settled=settled,
                adsr=s['adsr'] if s['adsr'] is not None else 0,
                wave_class=(s['wf'] or 0) & 0xF0,
                pulse_bucket=(pul // PULSE_BUCKET) if pul is not None else -1,
                freq=s['freq'] if s['freq'] is not None else 0,
            ))
    out.sort(key=lambda o: (o.frame, o.voice))
    return out


# ---------------------------------------------------------------------------
# 2. Does ADSR identify an instrument in this file at all?
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    verdict: str
    why: str
    onsets: int
    distinct: int
    modulated: int
    unsettled: int
    ratio: float
    mod_ratio: float
    unsettled_ratio: float
    settle_delays: dict = field(default_factory=dict)

    @property
    def usable(self):
        """Is a mapping table meaningful for this file?

        `degenerate` is deliberately usable-but-uninformative rather than
        unusable: one ADSR over every note is a perfectly stable key that
        separates nothing, and the caller should say so, not refuse.
        """
        return self.verdict in ("reliable", "suspect", "degenerate")

    @property
    def measured(self):
        """False when there is nothing to grade — an empty trace, not a result."""
        return self.verdict != "no-trace"


def _any_voice_activity(frames):
    """Did any voice ever select a real waveform? Distinguishes an empty trace
    from a tune that genuinely never gates."""
    for v in frames:
        for i in range(3):
            wf = v[0][i]['wf']
            if wf is not None and (wf & 0xF0):
                return True
    return False


def key_reliability(onsets, frames, min_onsets=MIN_ONSETS):
    """Grade the ADSR key: reliable / degenerate / suspect / insufficient-data /
    unusable.

    Two ways the key fails, each with its own number:
      - a distinct value per note: the player computes the envelope, it is not a
        per-instrument constant;
      - the value changes DURING a note: the player modulates it, so the value at
        onset names no stable record.

    And one way the MEASUREMENT fails, checked first (H1): the sample never
    leaves the hard restart.
    """
    n = len(onsets)
    nf = len(frames)
    distinct = {o.adsr for o in onsets}
    modulated = 0
    for o in onsets:
        for f in range(o.sample_frame + 1, nf):
            s = frames[f][0][o.voice]
            if s['wf'] is None or not (s['wf'] & 1):
                break                                    # gate released
            if s['adsr'] is not None and s['adsr'] != o.adsr:
                modulated += 1
                break
    unsettled = sum(1 for o in onsets if not o.settled)
    ratio = (len(distinct) / n) if n else 0.0
    mod_ratio = (modulated / n) if n else 0.0
    uns_ratio = (unsettled / n) if n else 0.0
    delays = dict(Counter(o.settle_delay for o in onsets))

    def pct(x):
        return "%d%%" % round(x * 100)

    if n == 0 and not _any_voice_activity(frames):
        # 0 onsets is ambiguous and the ambiguity matters: a digi player that
        # never gates and a file the tracer could not drive at all look
        # identical from the onset count alone. The same empty==empty confusion
        # certified 64 zero bytes as a byte-exact match in v3.21.0 (see
        # `score_pct`), so the two are separated here rather than pooled.
        v = "no-trace"
        why = ("no voice ever selects a waveform across %d frames — this is an "
               "empty trace, not a tune without notes. Check the init/play "
               "addresses and the window before reading anything into it." % nf)
        return Verdict(v, why, 0, 0, 0, 0, 0.0, 0.0, 0.0, {})
    if n >= min_onsets and uns_ratio > 0.5:
        v = "unusable"
        why = ("%d of %d notes (%s) never reach a settled frame within %d of the "
               "onset — the sample is stuck in the player's hard restart, so "
               "these are the restart's registers, not any instrument's."
               % (unsettled, n, pct(uns_ratio), SETTLE_MAX))
    elif n < min_onsets:
        v = "insufficient-data"
        why = ("%d onsets is below the %d-onset floor — too few to tell a "
               "per-instrument constant from a coincidence." % (n, min_onsets))
    elif ratio > 0.75:
        v = "unusable"
        why = ("%d distinct ADSR values over %d onsets (%s) — near one per note, "
               "so ADSR is computed per note here, not copied per instrument."
               % (len(distinct), n, pct(ratio)))
    elif mod_ratio > 0.25:
        v = "unusable"
        why = ("%d of %d notes (%s) change ADSR while the gate is still on — the "
               "player modulates the envelope, so the onset value names no "
               "stable record." % (modulated, n, pct(mod_ratio)))
    elif len(distinct) == 1:
        v = "degenerate"
        why = ("a single ADSR value ($%04X) covers all %d onsets — the key is "
               "stable but carries no information, so a mapping table separates "
               "nothing. This file's instruments, if it has several, differ "
               "somewhere ADSR does not reach."
               % (next(iter(distinct)), n))
    elif ratio > 0.4 or mod_ratio > 0.05:
        v = "suspect"
        why = ("%d distinct over %d onsets (%s), %d modulated mid-note (%s) — "
               "usable, but treat any instrument seen once or twice as "
               "unconfirmed." % (len(distinct), n, pct(ratio), modulated,
                                 pct(mod_ratio)))
    else:
        v = "reliable"
        why = ("%d distinct ADSR values over %d onsets (%s), %d modulated "
               "mid-note — stable enough to key on."
               % (len(distinct), n, pct(ratio), modulated))
    return Verdict(v, why, n, len(distinct), modulated, unsettled,
                   ratio, mod_ratio, uns_ratio, delays)


# ---------------------------------------------------------------------------
# 3. Where is the instrument table? (searched, never assumed)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Layout:
    """A candidate instrument-table layout, in file-offset terms.

    row-major     record i's AD at base + i*step, SR at base + i*step + 1
    column-major  record i's AD at base + i,      SR at base + step + i

    `step` is the record stride in the first case and the column delta in the
    second, which is why one field carries both — the two shapes are the same
    search with the roles of stride and delta swapped.
    """
    shape: str
    base: int             # file offset
    step: int
    records: int          # highest record index used by a matched value, + 1
    hits: int             # distinct observed ADSR values found
    total: int            # distinct observed ADSR values looked for
    span: int             # record-index spread of the matches (tightness)
    first: int = 0        # lowest record index used by a matched value
    positions: tuple = () # the byte offsets that matched (aliases share these)

    def address(self, load):
        return self.base - 2 + load

    def read(self, data, count=None):
        """{adsr: [record index, ...]} for this layout, in record order."""
        out = defaultdict(list)
        n = count if count is not None else self.records
        for i in range(n):
            if self.shape == ROW_MAJOR:
                a, s = self.base + i * self.step, self.base + i * self.step + 1
            else:
                a, s = self.base + i, self.base + self.step + i
            if a >= len(data) or s >= len(data):
                break
            out[(data[a] << 8) | data[s]].append(i)
        return dict(out)


def locate_instrument_table(data, observed, max_records=32, strides=None,
                            deltas=None, min_hits=2):
    """Rank candidate instrument-table layouts by how many observed ADSRs they
    explain.

    Both shapes this repo's drivers actually use are searched:

      row-major     Laxity's 8-byte record ([0]=AD, [1]=SR), HardTrack's
                    per-file patched tables, most native players.
      column-major  SF2 Driver 11: 32 AD bytes at $0A03 then 32 SR at $0A23.

    `observed` is the set of ADSR values seen at note onsets. Candidates are
    ranked by hits, then by tightness (`span`) — a real column or record grid is
    tight, and $00/$0F line up by luck across a whole payload, which is exactly
    what `span` is there to expose.

    Returns [] rather than a bad guess when nothing reaches `min_hits`.
    """
    obs = sorted(set(observed))
    if not obs or len(data) < 4:
        return []
    obs_set = set(obs)
    cands = []

    def tally(pairs, shape, step):
        """pairs = {adsr: [position, ...]}; position is record 0's base when the
        value sits in record i and we subtract i*unit."""
        unit = step if shape == ROW_MAJOR else 1
        bases = defaultdict(dict)
        for a, positions in pairs.items():
            for p in positions:
                for i in range(max_records):
                    b = p - i * unit
                    if b < 0:
                        break
                    bases[b].setdefault(a, i)
        for b, found in bases.items():
            if len(found) < min_hits:
                continue
            idx = sorted(found.values())
            pos = tuple(sorted(b + i * unit for i in found.values()))
            cands.append(Layout(shape, b, step, idx[-1] + 1, len(found),
                                len(obs), idx[-1] - idx[0] + 1, idx[0], pos))

    # row-major: AD and SR adjacent, records at a constant stride
    adjacent = defaultdict(list)
    for p in range(len(data) - 1):
        v = (data[p] << 8) | data[p + 1]
        if v in obs_set:
            adjacent[v].append(p)
    for stride in (strides if strides is not None else range(2, 33)):
        tally(adjacent, ROW_MAJOR, stride)

    # column-major: AD and SR in parallel arrays a constant delta apart
    for delta in (deltas if deltas is not None else range(1, 129)):
        pairs = defaultdict(list)
        for p in range(len(data) - delta):
            v = (data[p] << 8) | data[p + delta]
            if v in obs_set:
                pairs[v].append(p)
        if pairs:
            tally(pairs, COLUMN_MAJOR, delta)

    # A stride-N grid aliases to every base N*k earlier: same hits, same span,
    # same matched BYTES, every record index shifted by k. Ranking by base
    # picks the earliest shadow, which is how SF2/Angular.sf2 first resolved to
    # $19CB (= $1A6B - 20 records) and renumbered every instrument by +20.
    #
    # Aliases are collapsed to their HIGHEST base, i.e. the one where the first
    # SOUNDED record is record 0. That is an assumption, not a deduction, and
    # the caller is told so: the trace cannot see a leading run of slots the
    # tune never plays. SF2 Driver 11's own test tunes are exactly that case —
    # the true table is $1D3A and slot 0 is unused, so this search reports
    # $1D3B. One record out, and it says which direction the error runs.
    keep = {}
    for c in cands:
        k = (c.shape, c.step, c.positions)
        if k not in keep or c.base > keep[k].base:
            keep[k] = c
    out = sorted(keep.values(),
                 key=lambda c: (-c.hits, c.span, c.first, c.step, c.base))
    return out


def check_declared(data, layout, observed, count=None):
    """Grade a declared or located layout against what the tune actually sounds.

    confirmed         every observed value found, against a table not much
                      bigger than the observed set
    confirmed-weakly  every observed value found, but off too few values or
                      against a table large enough that the match is close to
                      free. One value landing somewhere in a 32-record table
                      says nothing at all.
    incomplete        most found, a minority missing. The address is not in
                      doubt — nine independent values do not agree by accident —
                      so what is missing is a record, or an envelope the player
                      writes from outside its instrument table. SF2/Angular.sf2
                      is this case: 9 of 10, with $0028 sounded 50 times and
                      declared by neither the conversion NOR the original.
    layout-wrong      most or all observed values appear nowhere in the table.
                      A real falsification of whichever side declared it — but
                      see `sid-reference-project`'s john-player case: a register
                      trace LOCALISES, it does not adjudicate.
    out-of-range      the declared base is outside this file's image. Usual for
                      a relocatable player, not an error in the claim.

    Returns (verdict, detail) where detail carries `missing` and `found`.
    """
    obs = sorted(set(observed))
    if not obs:
        return "unverifiable", {"why": "no observed ADSR values to check against",
                                "missing": [], "found": {}}
    if layout is None:
        return "unverifiable", {"why": "no layout declared or located",
                                "missing": obs, "found": {}}
    if layout.base < 0 or layout.base >= len(data):
        return "out-of-range", {"why": "base offset %d is outside a %d-byte image"
                                       % (layout.base, len(data)),
                                "missing": obs, "found": {}}
    table = layout.read(data, count)
    found = {a: table[a] for a in obs if a in table}
    missing = [a for a in obs if a not in table]
    if missing:
        # A minority miss does not falsify an address that the majority
        # independently confirms. Splitting these apart is the difference
        # between "we are reading the wrong bytes" and "the player sounds
        # something its own records do not declare" — two findings that need
        # two different investigations.
        v = ("incomplete" if len(found) >= 3 and len(found) >= 0.75 * len(obs)
             else "layout-wrong")
        return v, {
            "why": "%d of %d sounded envelopes appear nowhere in the table"
                   % (len(missing), len(obs)),
            "missing": missing, "found": found}
    declared = len(table)
    if len(obs) < 3:
        return "confirmed-weakly", {
            "why": "only %d distinct envelope(s) observed — too few for the "
                   "match to mean much" % len(obs),
            "missing": [], "found": found}
    if declared > 4 * len(obs):
        return "confirmed-weakly", {
            "why": "%d distinct declared values against %d observed — a table "
                   "this large matches close to free" % (declared, len(obs)),
            "missing": [], "found": found}
    return "confirmed", {
        "why": "all %d observed envelopes found among %d declared values"
               % (len(obs), declared),
        "missing": [], "found": found}


# ---------------------------------------------------------------------------
# 4. The map
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MapRow:
    """One declared instrument, against what each side actually sounds.

    `records` is a LIST because ADSR is not injective: SF2/Angular.sf2 declares
    $0694 four times (records 3-6) and $00A8 twice (11-12). Collapsing that to
    one index would be a lie, so it is carried as the set it is.
    """
    records: tuple
    adsr: int
    orig_wave: int
    orig_notes: int
    ours_wave: int
    ours_notes: int
    verdict: str

    @property
    def label(self):
        """Every record, never truncated. Only the fixed-width dump column
        abbreviates (see `instrument_labels`); a table has room for the truth."""
        return "/".join(str(r) for r in self.records)


def _by_adsr(onsets):
    out = defaultdict(Counter)
    for o in onsets:
        out[o.adsr][(o.wave_class, o.pulse_bucket)] += 1
    return out


def build_map(declared, orig_onsets, ours_onsets=None):
    """(rows, orphans) — one row per declared ADSR, plus what the original
    sounds that nothing declares.

    `declared` is `Layout.read()`'s {adsr: [record, ...]}. `ours_onsets` may be
    None when only the original was traced; the `ours` columns then read as
    not-measured rather than as zero, because "we never played it" and "we never
    looked" are different claims.
    """
    o_by = _by_adsr(orig_onsets)
    u_by = _by_adsr(ours_onsets) if ours_onsets is not None else None
    rows = []
    for adsr in sorted(declared):
        recs = tuple(declared[adsr])
        oh = o_by.get(adsr)
        uh = u_by.get(adsr) if u_by is not None else None
        o_n = sum(oh.values()) if oh else 0
        u_n = sum(uh.values()) if uh else 0
        o_w = oh.most_common(1)[0][0][0] if oh else None
        u_w = uh.most_common(1)[0][0][0] if uh else None
        if u_by is None:
            verdict = "sounded x%d" % o_n if oh else "never sounded"
        elif not oh and not uh:
            verdict = "unused both sides"
        elif not oh:
            verdict = "**we play it, the original does not**"
        elif not uh:
            verdict = "**the original plays it, we do not**"
        elif o_w != u_w:
            verdict = "**waveform: %s -> %s**" % (wave_name(o_w), wave_name(u_w))
        else:
            verdict = "ok"
        rows.append(MapRow(recs, adsr, o_w, o_n, u_w, u_n, verdict))
    orphans = [(a, o_by[a].most_common(1)[0][0][0], sum(o_by[a].values()))
               for a in sorted(o_by) if a not in declared]
    orphans.sort(key=lambda t: -t[2])
    return rows, orphans


# ---------------------------------------------------------------------------
# 5. What the original does, per instrument
# ---------------------------------------------------------------------------

def note_profiles(frames, onsets, profile_frames=PROFILE_FRAMES):
    """{adsr: profile} — the modal register behaviour of each keyed instrument.

    `pulse_onset` is the band the sample frames cover; `pulse_note` the band over
    the WHOLE note. They answer different questions and a pulse program only
    shows up in the second: a sweep that restarts with the note sits on one onset
    value however far it travels afterwards, so an onset-only reading calls a
    working sweep static.
    """
    nf = len(frames)
    nxt = {}
    per_voice = defaultdict(list)
    for o in onsets:
        per_voice[o.voice].append(o)
    for v, lst in per_voice.items():
        lst.sort(key=lambda o: o.frame)
        for i, o in enumerate(lst):
            nxt[(v, o.frame)] = lst[i + 1].frame if i + 1 < len(lst) else nf

    acc = defaultdict(lambda: {"waves": Counter(), "onset_p": [], "note_p": [],
                               "fall": [], "gate": Counter(), "notes": 0})
    for o in onsets:
        end = min(nxt[(o.voice, o.frame)], nf)
        start = o.sample_frame
        span = min(end, start + profile_frames)
        if span <= start:
            continue
        d = acc[o.adsr]
        d["notes"] += 1
        seq, pw, fq = [], [], []
        for f in range(start, span):
            s = frames[f][0][o.voice]
            seq.append((s['wf'] or 0) & 0xF0)
            if s['pul'] is not None:
                pw.append(s['pul'])
            if s['freq'] is not None:
                fq.append(s['freq'])
        d["waves"][tuple(seq)] += 1
        if pw:
            d["onset_p"].append((min(pw), max(pw)))
        whole = [frames[f][0][o.voice]['pul'] for f in range(start, end)
                 if frames[f][0][o.voice]['pul'] is not None]
        if whole:
            d["note_p"].append((min(whole), max(whole)))
        if fq:
            d["fall"].append(fq[0] - min(fq))
        g = next((f - o.frame for f in range(start, end)
                  if (frames[f][0][o.voice]['wf'] or 0) & 1 == 0), None)
        d["gate"][g] += 1

    out = {}
    for adsr, d in acc.items():
        if not d["waves"]:
            continue
        seq = d["waves"].most_common(1)[0][0]
        fall = sorted(d["fall"])[len(d["fall"]) // 2] if d["fall"] else 0
        out[adsr] = {
            "notes": d["notes"],
            "waves": seq,
            "pulse_onset": ((min(a for a, _ in d["onset_p"]),
                             max(b for _, b in d["onset_p"]))
                            if d["onset_p"] else None),
            "pulse_note": ((min(a for a, _ in d["note_p"]),
                            max(b for _, b in d["note_p"]))
                           if d["note_p"] else None),
            "pitch_fall": fall,
            "gate_off": d["gate"].most_common(1)[0][0],
        }
    return out


# ---------------------------------------------------------------------------
# 6. siddump, with the instrument named on every frame
# ---------------------------------------------------------------------------

_INS_W = 4


def frame_labels(onsets, labels, nframes):
    """(cols, onset_frames) — per voice, the label of the note sounding.

    The instrument is decided ONCE per note, at the settled sample frame, and
    held to the next onset. Deciding per frame instead would let the column
    disagree with the mapping table above it, which is the one thing an
    annotation must never do.
    """
    cols = [[""] * nframes for _ in range(3)]
    onset_frames = [set() for _ in range(3)]
    per_voice = defaultdict(list)
    for o in onsets:
        per_voice[o.voice].append(o)
    for v, lst in per_voice.items():
        lst.sort(key=lambda o: o.frame)
        for i, o in enumerate(lst):
            end = lst[i + 1].frame if i + 1 < len(lst) else nframes
            onset_frames[v].add(o.frame)
            lab = labels.get(o.adsr, "?")
            for f in range(o.frame, min(end, nframes)):
                cols[v][f] = lab
    return cols, onset_frames


def instrument_labels(declared, orig_onsets):
    """{adsr: label} — record index/indices, or a letter for an unclaimed ADSR.

    Unclaimed values get a..z in first-appearance order, matching h2g, so a
    reader can tell "instrument 7" from "an envelope nothing declares" at a
    glance instead of having to cross-check the table.
    """
    labels = {}
    for adsr, recs in declared.items():
        s = "/".join(str(r) for r in recs)
        labels[adsr] = s if len(s) <= _INS_W else "%d+" % recs[0]
    unclaimed = []
    for o in sorted(orig_onsets, key=lambda o: (o.frame, o.voice)):
        if o.adsr not in labels and o.adsr not in unclaimed:
            unclaimed.append(o.adsr)
    for i, adsr in enumerate(unclaimed):
        labels[adsr] = chr(ord('a') + i % 26) + ("" if i < 26 else str(i // 26 + 1))
    return labels


def annotate_dump(text, cols, onset_frames):
    """siddump's own table with three instrument columns appended.

    Structural rule: every table line gets exactly `len(cell) + 3` characters
    added and nothing else changes, so `strip_annotation` returns the input BYTE
    FOR BYTE. That is a unit test, not a hope — and the split is on "\n" alone
    with any trailing "\r" carried across the insertion, because siddump's output
    is CRLF and `splitlines()` eats the "\r" while still comparing equal to a
    str that never had one.
    """
    cell = "%*s %*s %*s" % (_INS_W, "Ins1", _INS_W, "Ins2", _INS_W, "Ins3")
    pad = len(cell) + 2
    nframes = len(cols[0])
    out = []
    for raw in text.split("\n"):
        cr = "\r" if raw.endswith("\r") else ""
        line = raw[:-1] if cr else raw
        if line.startswith("+") and line.endswith("+"):
            out.append(line + "-" * pad + "+" + cr)
            continue
        if not line.startswith("|"):
            out.append(raw)
            continue
        parts = line.split("|")
        try:
            frame = int(parts[1].strip())
        except (ValueError, IndexError):
            out.append(line + " " + cell + " |" + cr)     # header row
            continue
        if frame >= nframes:
            out.append(line + " " * pad + "|" + cr)
            continue
        cells = []
        for v in range(3):
            lab = cols[v][frame] or "."
            if frame in onset_frames[v]:
                lab = "*" + lab
            cells.append("%*s" % (_INS_W, lab))
        out.append(line + " " + " ".join(cells) + " |" + cr)
    return "\n".join(out)


def strip_annotation(text):
    """The exact inverse of `annotate_dump`."""
    cell = "%*s %*s %*s" % (_INS_W, "Ins1", _INS_W, "Ins2", _INS_W, "Ins3")
    pad = len(cell) + 3
    out = []
    for raw in text.split("\n"):
        cr = "\r" if raw.endswith("\r") else ""
        line = raw[:-1] if cr else raw
        if (line.startswith("+") and line.endswith("+")) or line.startswith("|"):
            out.append(line[:-pad] + cr)
        else:
            out.append(raw)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# 7. Per-instrument fidelity
# ---------------------------------------------------------------------------

class InstrumentScores:
    """Accumulate any per-frame agreement test, split by the sounding instrument.

    The whole payoff of this module. Every fidelity number in this repo is per
    voice and per register: "HardTrack Stage B ADSR 88-94%" cannot say WHICH
    record loses the frames, and "274 of 324 SDI files ship default instrument
    data" cannot say which of those slots is ever reached. Feed the same
    comparison through here and it becomes one number per record, with n.

    Two rules it enforces, both of which exist because their absence has shipped
    a wrong number in this repo before:

      * frames before the first onset, or on a voice that never gated, land in
        an explicit `unattributed` bucket rather than being dropped. The split
        must SUM BACK to the caller's own total, or the split is quietly
        measuring a different population than the headline.
      * every percentage goes through `score_pct`, so a record with no
        comparable frames reads `None`, never 100.0.
    """

    UNATTRIBUTED = "-"

    def __init__(self, cols):
        self.cols = cols
        self.ok = defaultdict(int)
        self.tot = defaultdict(int)

    def add(self, voice, frame, matched):
        lab = (self.cols[voice][frame] if 0 <= frame < len(self.cols[voice])
               else "") or self.UNATTRIBUTED
        k = (voice, lab)
        self.tot[k] += 1
        self.ok[k] += bool(matched)

    def rows(self):
        """[(voice, label, pct_or_None, ok, n)] ordered by voice then n."""
        from .fidelity_common import score_pct
        out = [(v, lab, score_pct(self.ok[(v, lab)], self.tot[(v, lab)]),
                self.ok[(v, lab)], self.tot[(v, lab)])
               for (v, lab) in self.tot]
        out.sort(key=lambda r: (r[0], -r[4], str(r[1])))
        return out

    def totals(self):
        """{voice: (ok, n)} — must equal the caller's own per-voice figures."""
        agg = defaultdict(lambda: [0, 0])
        for (v, lab), n in self.tot.items():
            agg[v][0] += self.ok[(v, lab)]
            agg[v][1] += n
        return {v: tuple(x) for v, x in agg.items()}


def frames_by_instrument(onsets, labels, nframes):
    """{(voice, label): [frame, ...]} — the frames each instrument owns.

    The join that turns any existing per-frame comparison into a per-instrument
    one: group the frames a register was compared on by the instrument sounding
    there, and a whole-file percentage becomes one number per record, with n.
    """
    cols, _ = frame_labels(onsets, labels, nframes)
    out = defaultdict(list)
    for v in range(3):
        for f in range(nframes):
            if cols[v][f]:
                out[(v, cols[v][f])].append(f)
    return dict(out)
