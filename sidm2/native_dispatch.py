"""Which native builder owns this SID? Probe the parsers, do not trust player-id.

ROADMAP A4 asked for registry entries so `sid-to-sf2.bat` would auto-route the
`bin/` players. Measured 2026-08-17, that cannot work: `PLAYER_REGISTRY` keys on
`player-id.exe` strings and those verdicts are MANY-TO-MANY with the builders.
Sampling 12 files spread across each of 10 corpora, `Matt_Gray` files report
`Soundmonitor` on 10 of 12, and a `DMC` verdict captures 4 HardTrack and 2 SDI
files. Only three families are clean enough to route on the string:

    Galway      Martin_Galway     12/12
    Hubbard     Rob_Hubbard       11/12
    Blackbird   Blackbird/LFT + LFT 11/12 (1 unidentified)

So the discriminator is each parser's own signature-based locate, which every
family already implements and which every family already refuses loudly when it
does not match ("tables not located", "decoded no notes", "not an SDI play+3
rip"). This module turns those refusals into a dispatch decision.

CHEAP BY CONSTRUCTION. A probe constructs the parser's module object, which
runs its locate and raises. It does NOT build, render, emulate or siddump, so
dispatching a file costs milliseconds and is safe to run beside a corpus job.

ORDER IS NOT A GUESS AND MUST NOT BECOME ONE. `PROBE_ORDER` below is only
meaningful if the parsers are actually mutually exclusive on real files; where
two accept the same file the first one wins silently, which is the failure mode
that makes a dispatcher worse than no dispatcher. `dispatch()` therefore takes
`first_match=False` by default and reports EVERY family that accepts the file,
so a collision is visible rather than hidden. Callers that want a single answer
opt into `first_match=True` and accept the ordering.
"""
from __future__ import annotations

# player-id.exe verdicts that are reliable enough to use as a PREFILTER.
# Everything else is measured noise -- see the module docstring.
RELIABLE_PLAYER_IDS = {
    "Martin_Galway": "galway",
    "Rob_Hubbard": "hubbard",
    "Blackbird/LFT": "blackbird",
    "LFT": "blackbird",
}


def _probe_dmc(path):
    """Constructing DMCModule is NOT a discriminator -- measured 2026-08-17, it
    accepts every file in every corpus, because _locate finds plausible-looking
    tables anywhere. The real refusal is at DECODE ("decoded no notes on any
    voice"), so the probe has to go that far."""
    from sidm2.dmc_parser import load_sid, DMCModule, decode_song
    d, la, _h = load_sid(path)
    m = DMCModule(d, la)
    voices = decode_song(m, tick_budget=400)
    if not any(voices[v] for v in range(len(voices))):
        raise ValueError("decoded no notes on any voice")
    return {"load": la, "notes": sum(len(v) for v in voices)}


def _probe_sdi(path):
    from sidm2.sdi_parser import load_sid, SDIModule, is_sdi_play3
    d, la, h = load_sid(path)
    if not is_sdi_play3(d, la, h):
        raise ValueError("not an SDI play+3 rip")
    m = SDIModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_mon(path):
    from sidm2.mon_parser import load_sid, MON
    d, la, _h = load_sid(path)
    m = MON(d, la)
    # KNOWN GAP: MON has no cheap predicate and no decode-level refusal wired in
    # here, so this probe still accepts everything. Until that is closed, `mon`
    # must never be used as a first_match answer -- see the module docstring.
    return {"load": la, "tables": getattr(m, "lay", None), "weak": True}


def _probe_hubbard(path):
    from sidm2.hubbard_parser import load_sid, HubbardModule
    d, la, _h = load_sid(path)
    m = HubbardModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_soundmonitor(path):
    """soundmonitor_parser ships its own predicate, exactly as sdi_parser does.
    Constructing the module alone accepts everything."""
    from sidm2.soundmonitor_parser import load_sid, SoundMonitorModule, is_soundmonitor
    d, la, h = load_sid(path)
    if not is_soundmonitor(d, la, h):
        raise ValueError("not a Sound Monitor rip")
    m = SoundMonitorModule(d, la)
    return {"load": la, "tables": getattr(m, "lay", None)}


def _probe_blackbird(path):
    from sidm2.blackbird_parser import locate_blackbird
    r = locate_blackbird(path)
    if not r:
        raise ValueError("locate_blackbird found nothing")
    return {"tables": r}


def _probe_mattgray(path):
    from sidm2.mattgray_parser import load_sid, MattGrayParser
    d, la, _h = load_sid(path)
    p = MattGrayParser(d, la)
    return {"load": la, "tables": p.locate()}


# Most specific first. See the docstring: this order only decides `first_match`,
# and dispatch() reports collisions rather than letting the order hide them.
PROBE_ORDER = (
    ("blackbird", _probe_blackbird),
    ("sdi", _probe_sdi),
    ("hardtrack", None),          # HardTrackModule takes a different shape; see TODO
    ("mattgray", _probe_mattgray),
    ("dmc", _probe_dmc),
    ("mon", _probe_mon),
    ("hubbard", _probe_hubbard),
    ("soundmonitor", _probe_soundmonitor),
)


# A PROBE BUG MUST NOT LOOK LIKE A REFUSAL. Catching Exception broadly here hid
# a real one: `is_soundmonitor(data, la, h)` was called with two arguments, the
# TypeError was swallowed as "not a Sound Monitor rip", and the family silently
# rejected its OWN corpus while the run still looked clean. Parser refusals are
# ValueError/IndexError/KeyError; a TypeError, AttributeError or NameError is my
# code being wrong and has to surface.
BUG_EXCEPTIONS = (TypeError, AttributeError, NameError, ImportError)


class ProbeBug(Exception):
    """A probe called its parser wrongly. Never a verdict about the file."""


def probe(player, path):
    """(True, evidence) or (False, reason). Raises ProbeBug on a caller error."""
    fn = dict(PROBE_ORDER).get(player)
    if fn is None:
        return False, "no probe implemented"
    try:
        return True, fn(path)
    except BUG_EXCEPTIONS as e:
        raise ProbeBug("%s probe is broken: %s: %s"
                       % (player, type(e).__name__, e)) from e
    except Exception as e:                      # a refusal IS the reject signal
        return False, "%s: %s" % (type(e).__name__, str(e)[:120])


def dispatch(path, player_id=None, first_match=False):
    """Which native builders accept this file?

    Returns {"accepted": [player, ...], "rejected": {player: reason},
             "prefilter": player_or_None}. `accepted` with more than one entry is
    a COLLISION and the caller must not silently take the first unless it asked
    for `first_match`.
    """
    order = [p for p, _ in PROBE_ORDER]
    pre = RELIABLE_PLAYER_IDS.get(player_id) if player_id else None
    if pre and pre in order:                    # prefilter only reorders; it
        order.remove(pre)                       # never excludes, because the
        order.insert(0, pre)                    # verdicts are not exhaustive
    accepted, rejected = [], {}
    for p in order:
        ok, info = probe(p, path)
        if ok:
            accepted.append(p)
            if first_match:
                break
        else:
            rejected[p] = info
    return {"accepted": accepted, "rejected": rejected, "prefilter": pre}
