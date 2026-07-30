#!/usr/bin/env python3
"""SF2II editor crash oracle: load a .sf2 in the REAL editor, press PLAY, report
whether the editor survives -- plus the analysis that decides how long to play.

Promoted from untracked scratch (2026-07-25). This exists because an
SF2II-EDITOR-only hazard is invisible to every offline tool in this repo (py65,
zig64, the Python simulator) AND to the instrumented SIDFactoryII_dbg.exe
auto-play path. Only the real interactive editor can decide, so the play-test
has to be scriptable to be run in trials with a control arm.

    py -3 pyscript/blackbird_crash_probe.py <file.sf2> [trials] [load_attempts]
    py -3 pyscript/blackbird_crash_probe.py --schedule <file.sf2>

THE VALIDITY CONDITION, learned the expensive way. The first version of this
probe used a 6-second play window and returned a clean 16/16 SURVIVED for a
build whose earliest combo command fires at ~8.2s -- it executed ZERO of the
thing under test and would have "proved" absence by measuring outside the window
where the effect lives. `assert_window_covers()` now makes that failure mode
raise instead of returning a reassuring number. Never widen a conclusion beyond
what the window actually covered.

A load failure is retried and NEVER reported as a play crash (SF2II's F10-load
is independently heap-flaky). Only a build that loaded, verified its window
title, then died within the post-play window counts as CRASHED.

Exit: 0 survived, 1 crashed, 2 could not load.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pyscript"))
sys.path.insert(0, ROOT)

# SF2II's own sequence-format constants (datasource_sequence.cpp).
SEQ_TERMINATOR = 0x7F
CMD_MIN = 0xC0          # value >= 0xC0 -> command byte, index = value & 0x3F
INSTR_MIN = 0xA0        # value >= 0xA0 -> instrument byte
MAX_EVENT_COUNT = 1024  # m_Events is a fixed 1024-entry heap array

# Blackbird combo fx command indices (E3f): [COMBO_BASE, RESTART_ARM_FX).
RESTART_ARM_FX = 63

PLAY_WAIT_SECONDS = 65.0   # must outlast the first combo command -- see above
PLAY_MARGIN = 1.25         # require this much headroom over the first event


def unpack_sequence(seq):
    """Exact port of SF2II's DataSourceSequence::Unpack (datasource_sequence.cpp).

    Returns (n_events, [(event_index, command_index), ...], packed_size).
    packed_size is None when no 0x7F terminator appears in the 256-byte block.

    NOTE the duration-expansion loop is UNBOUNDED in the C++ -- event_index is
    incremented with no check against MAX_EVENT_COUNT -- so a sequence
    unpacking past 1024 events is a genuine heap overrun. Ported faithfully,
    including that, so callers can detect it (see events_overflow()).
    """
    event_index = 0
    duration = 0
    i = 0
    packed = None
    commands = []
    n = len(seq)
    while i < 0x100 and i < n:
        value = seq[i]; i += 1
        if value == SEQ_TERMINATOR:
            packed = i
            break
        if value >= CMD_MIN:
            commands.append((event_index, value & 0x3F))
            value = seq[i] if i < n else 0
            i += 1
        if value >= INSTR_MIN:
            value = seq[i] if i < n else 0
            i += 1
        if value >= 0x80:
            duration = value & 0x0F
            value = seq[i] if i < n else 0
            i += 1
        event_index += 1 + duration
    return event_index, commands, packed


def events_overflow(seq):
    """True when this sequence unpacks past SF2II's fixed 1024-event array."""
    return unpack_sequence(seq)[0] > MAX_EVENT_COUNT


def load_sf2_sequences(path):
    """(driver_info, sequences, orderlists) for a built .sf2."""
    from sidm2.models import SF2DriverInfo
    from sidm2 import sf2_parser
    data = bytearray(open(path, "rb").read())
    di = SF2DriverInfo()
    load_addr = sf2_parser.parse_sf2_blocks(data, di)
    body = data[2:]

    def at(addr):
        return addr - load_addr

    seqs = []
    for s in range(di.sequence_count):
        addr = body[at(di.sequence_ptrs_lo + s)] | (body[at(di.sequence_ptrs_hi + s)] << 8)
        seqs.append(bytes(body[at(addr):at(addr) + 0x100]))
    orderlists = [
        bytes(body[at(di.orderlist_start + v * di.orderlist_size):
                   at(di.orderlist_start + v * di.orderlist_size) + di.orderlist_size])
        for v in range(di.track_count)
    ]
    return di, seqs, orderlists


def combo_schedule(seqs, orderlists, frames_per_row, combo_lo,
                   combo_hi=RESTART_ARM_FX, fps=50.0):
    """When each combo command actually EXECUTES, in playback order.

    Returns [(seconds, row, voice, command_index), ...] sorted by time. This is
    what decides whether a play window is long enough to mean anything: a probe
    that stops before the first entry has tested nothing.
    """
    info = [unpack_sequence(s) for s in seqs]
    hits = []
    for v, ol in enumerate(orderlists):
        row = 0
        for b in ol:
            if b == 0xFF:
                break
            if b >= INSTR_MIN or b >= len(seqs):
                continue                      # orderlist transpose/marker byte
            n_events, commands, _ = info[b]
            for ev, cmd in commands:
                if combo_lo <= cmd < combo_hi:
                    hits.append(((row + ev) * frames_per_row / fps,
                                 row + ev, v, cmd))
            row += n_events
    return sorted(hits)


def assert_window_covers(schedule, window_seconds=PLAY_WAIT_SECONDS,
                         margin=PLAY_MARGIN):
    """Raise unless the play window comfortably outlasts the first event.

    This is the guard the original 6-second batch lacked. A probe that returns
    SURVIVED without having executed the construct under test is not evidence of
    absence, and must fail loudly rather than reassure.
    """
    if not schedule:
        raise ValueError(
            "no combo commands in this build -- a play-test of it says nothing "
            "about combo command values")
    first = schedule[0][0]
    if window_seconds < first * margin:
        raise ValueError(
            f"play window {window_seconds:.1f}s does not cover the first combo "
            f"command at {first:.1f}s (margin {margin}x): this measurement "
            f"would execute ZERO of the construct under test")
    return True


def classify_termination(exit_code):
    """Map a process's exit code (or None if still running) to an outcome.

    R23 fix: the original oracle called `_is_alive(pid)` once after the play
    wait and reported "SURVIVED" if true, "CRASHED" otherwise -- so a human
    closing the editor window mid-trial was indistinguishable from an actual
    crash (a 492s Driller trial was voided this way, see whats-next.md). A
    clean shutdown (the app's own WM_CLOSE -> ExitProcess path, whether
    triggered by a human or the app itself) reports exit code 0; an unhandled
    exception (access violation, stack overflow, ...) is terminated by Windows
    with the NTSTATUS/exception code as the exit code, which is never 0. So
    exit code 0 is the one value that positively rules out a crash.

    None            -> still running -- SURVIVED the window
    0               -> exited cleanly (very likely a human closing the window,
                       not a crash) -- CLOSED, not CRASHED
    anything else   -> CRASHED
    """
    if exit_code is None:
        return "SURVIVED"
    if exit_code == 0:
        return "CLOSED"
    return "CRASHED"


def tally(results):
    """Summarise trial outcomes; crash-rate is over trials that actually PLAYED.

    CLOSED is excluded from the `played` denominator for the same reason
    NOLOAD already is: a trial the human closed mid-window says nothing about
    whether the build would have crashed on its own, so it must not count for
    OR against the crash rate.
    """
    t = {k: results.count(k) for k in ("SURVIVED", "CRASHED", "CLOSED", "NOLOAD")}
    played = t["SURVIVED"] + t["CRASHED"]
    t["played"] = played
    t["crash_rate"] = (t["CRASHED"] / played) if played else None
    return t


# ---------------------------------------------------------------------------
# GUI driving. Imported lazily so the analysis above stays importable (and
# testable) on a machine with no SF2II, no pywin32 and no display.
# ---------------------------------------------------------------------------
def probe_once(sf2_path, load_attempts=12, play_wait=PLAY_WAIT_SECONDS,
               shot_path=None, shot_interval=None):
    """'SURVIVED' | 'CLOSED' | 'CRASHED' | 'NOLOAD' -- see `classify_termination`.

    shot_interval: if given, take a screenshot roughly every `shot_interval`
    seconds during the play wait (named `<shot_path>.tNN.png`), not only a
    single one at the end -- makes it possible to see roughly when a CLOSED/
    CRASHED trial actually stopped, without changing the total wait duration.
    Opt-in and off by default so existing callers see no behavior change.
    """
    import shutil
    import time
    import win32con
    import sf2_load_test as harness
    import sf2_open_in_editor as opener

    bin_dir = os.path.dirname(opener.EDITOR)
    staged_name = f"_probe_{os.path.splitext(os.path.basename(sf2_path))[0][:24]}.sf2"
    shutil.copyfile(os.path.abspath(sf2_path), os.path.join(bin_dir, staged_name))

    def _snapshot(hwnd, suffix):
        try:
            import win32gui as _wg
            from PIL import ImageGrab
            ImageGrab.grab(bbox=_wg.GetWindowRect(hwnd), all_screens=True) \
                .save(f"{shot_path}{suffix}")
        except Exception as e:
            print(f"    screenshot failed: {e}", file=sys.stderr)

    for attempt in range(1, load_attempts + 1):
        ok, proc = opener._try_one_detached_load(staged_name, bin_dir)
        if not ok:
            print(f"    load attempt {attempt}/{load_attempts} failed - retrying",
                  flush=True)
            time.sleep(0.4)
            continue
        hwnd = opener._find_window_for_pid(proc.pid, timeout=4.0)
        if hwnd is None:
            opener._kill_pid(proc.pid)
            continue
        try:
            import win32gui
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.4)
        harness.send_vk(win32con.VK_F1)     # Key.ScreenEdit.Play
        if shot_path and shot_interval:
            elapsed, tick = 0.0, 0
            while elapsed < play_wait:
                step = min(shot_interval, play_wait - elapsed)
                time.sleep(step)
                elapsed += step
                tick += 1
                if proc.poll() is not None:
                    break            # already terminated; stop early-snapshotting
                _snapshot(hwnd, f".t{tick:02d}.png")
        else:
            time.sleep(play_wait)
        # Non-blocking: None if still running. Reads off the Popen's own
        # retained handle, so (unlike a pid-based alive check) it stays valid
        # even long after the process has exited -- see
        # sf2_open_in_editor._spawn_detached's docstring.
        exit_code = proc.poll()
        outcome = classify_termination(exit_code)
        # Proof of play: a probe that silently failed to deliver F1 would also
        # report SURVIVED, so capture the editor's own "Playing time" readout.
        if outcome == "SURVIVED" and shot_path:
            _snapshot(hwnd, "")
        opener._kill_pid(proc.pid)
        return outcome
    return "NOLOAD"


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--schedule":
        di, seqs, ols = load_sf2_sequences(argv[1])
        fpr = float(argv[2]) if len(argv) > 2 else 4.52
        lo = int(argv[3]) if len(argv) > 3 else 48
        sched = combo_schedule(seqs, ols, fpr, lo)
        print(f"{len(sched)} combo command(s); "
              f"first at {sched[0][0]:.1f}s (row {sched[0][1]}, voice {sched[0][2]})"
              if sched else "no combo commands in this build")
        return 0
    path = argv[0]
    trials = int(argv[1]) if len(argv) > 1 else 1
    load_attempts = int(argv[2]) if len(argv) > 2 else 12
    results = []
    for t in range(1, trials + 1):
        shot = os.path.join(ROOT, "out", "blackbird", f"probe_t{t}.png")
        os.makedirs(os.path.dirname(shot), exist_ok=True)
        r = probe_once(path, load_attempts, shot_path=shot)
        print(f"  trial {t}/{trials}: {r}", flush=True)
        results.append(r)
    t = tally(results)
    print(f"\n{os.path.basename(path)}: SURVIVED={t['SURVIVED']} "
          f"CRASHED={t['CRASHED']} CLOSED={t['CLOSED']} NOLOAD={t['NOLOAD']}")
    if t["CLOSED"]:
        print(f"  note: {t['CLOSED']} trial(s) exited cleanly (exit code 0) "
              f"mid-window -- most likely the window was closed manually, NOT "
              f"a crash. Excluded from crash_rate; re-run for a conclusive "
              f"trial if these need to count as evidence.")
    if t["CRASHED"]:
        return 1
    return 0 if t["SURVIVED"] else 2


if __name__ == "__main__":
    sys.exit(main())
