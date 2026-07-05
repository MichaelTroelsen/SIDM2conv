"""Shared plumbing for the fidelity/validation tools (roadmap A3).

Before this module, six validators (mon_fidelity, mon_sf2_validate, mon_validate,
romuzak_validate, romuzak_native_validate, fc_validate, plus sf2ii_vs_real and
build_mon_native_song.filter_trace) each carried private copies of the same
helpers: PSID probe wrapping, freq->semitone conversion, siddump table parsing,
and the zig64 fill-forward serializer. The copies had drifted — most notably the
semitone reference frequency (0x1168 vs 0x1167 vs an inline log2), a latent
inconsistency this module fixes by canonicalizing on one reference.

Everything here is measurement plumbing only: no player knowledge, no policy.
"""
import math
import re
import subprocess

# Canonical semitone reference: the PAL SID freq value for C-4 (261.63 Hz at
# phi2 = 985248 Hz -> 261.63 * 2^24 / 985248 ~= 4455 = $1167). "+48" maps C-4 to
# note index 48, matching the 96-entry note-table space. The pre-consolidation
# copies used $1168 (mon) / $1167 (romuzak) — a ~0.004-semitone difference that
# never crosses a rounding boundary for 16-bit SID freq pairs, verified by
# baseline-diffing every validator's output during the extraction.
SEMI_REF = 0x1167


def freq_to_semi(freq):
    """16-bit SID freq value -> nearest note index (0..95), or -1 for silence.

    None / 0 / sub-audio (<8, below the note table) all map to -1 so a silent
    voice compares equal to a silent voice.
    """
    if not freq or freq < 8:
        return -1
    return max(0, min(95, round(12 * math.log2(freq / SEMI_REF) + 48)))


def psid_wrap(data, load, init, play, songs=1, start_song=1):
    """Wrap a raw C64 binary as a minimal PSID so trace tools can drive it."""
    from scripts.sf2_to_sid import PSIDHeader
    h = PSIDHeader(load_address=load, init_address=init, play_address=play)
    h.songs = songs
    h.start_song = start_song
    return h.to_bytes() + data


# ---------------------------------------------------------------------------
# siddump (pyscript/siddump_complete.py) — run + table parsing
# ---------------------------------------------------------------------------

def run_siddump(path, args):
    """Run the Python siddump on `path` with extra `args`; returns its stdout."""
    return subprocess.run(['py', '-3', 'pyscript/siddump_complete.py', path] + list(args),
                          capture_output=True, text=True).stdout


def iter_siddump_rows(txt):
    """Yield (frame_or_None, cells) for each data row of a siddump table.

    cells = the '|'-split, stripped columns (cells[1]=frame, cells[2..4]=voices,
    cells[5]=filter). frame is None when the column isn't an int (callers that
    key on frames skip those rows; callers that count rows keep them).
    """
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        try:
            fr = int(c[1])
        except ValueError:
            fr = None
        yield fr, c


def siddump_per_frame(path, args):
    """siddump -> per-frame fill-forwarded voice + filter state.

    Returns frames[i] = ({0,1,2: {'freq','wf','pul'}}, fcut) with ints
    (None until a register is first written). This is the per-frame state the
    MoN fidelity metrics compare on.
    """
    txt = run_siddump(path, args)
    st = [{'freq': None, 'wf': None, 'pul': None} for _ in range(3)]
    fc = [None]
    frames = []

    def cv(x):
        return None if (not x or '.' in x) else int(x, 16)

    for fr, c in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi in range(3):
            m = re.match(r'^([0-9A-F\.]{4})\s+\S+\s+\S+\s+([0-9A-F\.]{2})\s+'
                         r'[0-9A-F\.]{4}\s+([0-9A-F\.]{3})', c[2 + vi])
            if m:
                for k, val in zip(('freq', 'wf', 'pul'), m.groups()):
                    cvv = cv(val)
                    if cvv is not None:
                        st[vi][k] = cvv
        fm = re.match(r'^([0-9A-F\.]{4})', c[5])
        if fm:
            cvv = cv(fm.group(1))
            if cvv is not None:
                fc[0] = cvv
        frames.append(({vi: dict(st[vi]) for vi in range(3)}, fc[0]))
    return frames


def siddump_note_onsets(path, args, require_wf=False):
    """siddump -> {0,1,2: [(frame, note_name), ...]} unbracketed note onsets.

    require_wf=True additionally demands the waveform column be present on the
    onset row (a fresh gated onset), matching the MoN validators; the
    ROMUZAK/FC validators accept any unbracketed note.
    """
    txt = run_siddump(path, args)
    pat = (re.compile(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\s+([0-9A-F]{2})\b') if require_wf
           else re.compile(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\b'))
    V = {0: [], 1: [], 2: []}
    for fr, c in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi, cell in enumerate(c[2:5]):
            m = pat.match(cell)
            if m and m.group(1) != '0000':
                V[vi].append((fr, m.group(2)))
    return V


def siddump_filter_trace(path, args):
    """siddump -> per-row global filter state (fill-forward): [(cutoff11, ctrl)]
    where cutoff11 = ($D415&7)|($D416<<3) and ctrl = $D417 (res+routing).
    One entry per siddump data row (frame-parse failures still emit a row, so
    the list length matches the dump length)."""
    txt = run_siddump(path, args)
    cut, ctrl, out = 0, 0xF1, []
    for fr, c in iter_siddump_rows(txt):
        mm = re.match(r'^([0-9A-F\.]{4})\s+([0-9A-F\.]{2})', c[5])
        if mm:
            if '.' not in mm.group(1):
                cut = int(mm.group(1), 16)
            if '.' not in mm.group(2):
                ctrl = int(mm.group(2), 16)
        out.append((cut, ctrl))
    return out


# ---------------------------------------------------------------------------
# zig64 cycle-accurate trace — fill-forward serialization
# ---------------------------------------------------------------------------

def fill_forward(writes, n, initial=0):
    """{frame: value} sparse write dict -> length-n per-frame list, carrying the
    last written value forward (frames before the first write get `initial`)."""
    out, cur = [], initial
    for i in range(n):
        if i in writes:
            cur = writes[i]
        out.append(cur)
    return out


def zig64_voices(reg, n):
    """zig64 trace dict {(voice, field): {frame: val}} -> per-voice per-frame state.

    Returns {v: {'freq' (16-bit), 'wf', 'pw' (12-bit), 'ad', 'sr'}} — the shape
    the deterministic native validators diff on.
    """
    def ser(vi, fld):
        return fill_forward(reg.get((vi, fld), {}), n)
    V = {}
    for v in range(3):
        fh, fl = ser(v, 'freq_hi'), ser(v, 'freq_lo')
        ph, pl = ser(v, 'pw_hi'), ser(v, 'pw_lo')
        V[v] = {
            'freq': [(fh[i] << 8) | fl[i] for i in range(n)],
            'wf': ser(v, 'control'),
            'pw': [((ph[i] & 0xF) << 8) | pl[i] for i in range(n)],
            'ad': ser(v, 'attack_decay'),
            'sr': ser(v, 'sustain_release'),
        }
    return V


def zig64_trace_voices(path, n, init, play, subtune):
    """Run the zig64 tracer on `path` and return zig64_voices(...) for n frames."""
    from sidm2 import galway_trace_extract as T
    return zig64_voices(T.run_trace(path, n, init, play, subtune), n)


# ---------------------------------------------------------------------------
# offset alignment
# ---------------------------------------------------------------------------

def best_gated_offset(offsets, count_fn):
    """Try each offset, keep the one with the most hits.

    count_fn(off) -> (hits, total, extra) where extra is any per-offset payload
    (e.g. a delta Counter). Returns (best_off, hits, total, extra); ties keep
    the earliest offset (matching the pre-consolidation loops).
    """
    bo, bh, bt, bx = 0, -1, 1, None
    for off in offsets:
        h, t, x = count_fn(off)
        if h > bh:
            bo, bh, bt, bx = off, h, t, x
    return bo, bh, bt, bx
