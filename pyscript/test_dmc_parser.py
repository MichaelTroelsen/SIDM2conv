"""Tests for the DMC (Bjerregaard / Demo Music Creator) parser.

Locks in the RE'd facts: signature-based table location (relocation-safe),
the chromatic freq table, tempo detection, and the track/sector decode
producing onset-validated note streams.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest
from sidm2.dmc_parser import load_sid, DMCModule, decode_song, decode_track
from sidm2.fidelity_common import freq_to_semi

CORP = os.path.join(ROOT, "SID", "JohannesBjerregaard")


def _mod(name):
    d, la, h = load_sid(os.path.join(CORP, f"{name}.sid"))
    return DMCModule(d, la), la, h


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_balloon_tables():
    """Balloon (load $1000) — the reference addresses from the RE."""
    m, la, h = _mod("Balloon")
    assert la == 0x1000
    assert m.lay.sector_lo == 0x1900 and m.lay.sector_hi == 0x1980
    assert m.lay.sound == 0x1500
    assert m.lay.freq == 0x135F
    assert m.lay.trk_lo == 0x104A and m.lay.trk_hi == 0x104D
    assert m.lay.tempo_reload == 4          # 4 frames/tick baked in code


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_relocation_safe():
    """A relocated tune ($C000) locates the same tables offset by load."""
    m, la, h = _mod("Cant_Stop")
    assert la == 0xC000
    # every table sits in the relocated image, above load
    for addr in (m.lay.sector_lo, m.lay.sound, m.lay.freq, m.lay.trk_lo):
        assert la <= addr < la + 0x1000


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_split_freq_table_generation():
    """The $3f00 'Fat' DMC generation uses a SPLIT freq table (separate lo/hi
    arrays, like MoN) rather than Balloon's interleaved note*2 layout. The parser
    must locate both arrays and note_freq must read them as a chromatic scale."""
    m, la, h = _mod("Fat_6")
    assert m.lay.freq and m.lay.freq_hi          # split detected (hi array present)
    assert m.lay.freq_hi > m.lay.freq + 1        # distinct arrays, not interleaved
    assert (m.lay.sector_lo and m.lay.sound and m.lay.trk_lo)  # all four located
    for note in (24, 36, 48, 60):                # exact octaves -> chromatic scale
        assert freq_to_semi(m.note_freq(note)) == note


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_state_generation_sound_fallback():
    """The 'state' DMC generation (In_the_Mood class) copies the sound record into
    per-voice state at note-on (LDA base,Y / STA st,X / LDA base+1,Y / AND #$0F)
    rather than writing AD straight to $D405, so the primary sound signature misses.
    The AD+SR-read fallback must locate the table."""
    m, la, h = _mod("In_the_Mood")
    assert m.lay.sound == 0x4500                 # located via the fallback
    assert (m.lay.sector_lo and m.lay.freq and m.lay.trk_lo)  # all four located


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_absolute_store_sound_fallback():
    """The unrolled-per-voice generation (Thunder_Force / M_A_C_H) writes voice 1's
    AD via `LDA base,Y / STA $D405` with an ABSOLUTE store (8D), not $D405,X — with
    AD/SR consecutive, so base serves m.sound directly. The 8D fallback locates it."""
    m, la, h = _mod("Thunder_Force")
    assert m.lay.sound == 0x89DE                 # AD field == record base here
    assert (m.lay.sector_lo and m.lay.freq and m.lay.trk_lo)


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_indexed_store_sound_fallback():
    """The stack/indexed-store generations (Special_Agent / Spy / Twilight) reload
    the store index between the field read and the SID write:
      LDA field,Y / LDY var,X / STA $D405,Y  (AD)  or  ... / STA $D406,Y (SR, AD=SR-1).
    Two more gated fallbacks locate the AD field."""
    assert _mod("Special_Agent")[0].lay.sound == 0x5AE1    # AD via STA $D405,Y
    assert _mod("Spy_vs_Spy_III")[0].lay.sound == 0x6517   # AD = (SR $6518) - 1


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_state_copy_sound_generation():
    """The state-copy generation (Flimbos_Quest / Stormlord_V2 / STII8 / …) zeroes
    per-voice state at note-on then copies the sound record in: `LDA #$00 / STA st,X
    / STA st,X / LDA sound_ad,Y / STA ad_state,X`. The AD-load fallback locates the
    table (its AD field = the record base)."""
    assert _mod("Stormlord_V2")[0].lay.sound == 0x1B1C
    assert _mod("STII8")[0].lay.sound == 0x1A56
    m = _mod("Flimbos_Quest_main")[0]
    assert m.lay.sound == 0x19C9 and m.lay.freq and m.lay.trk_lo


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_adc_vibrato_freq_generation():
    """The ADC-vibrato generation (Domino_Dancing / Alf_TV_Theme / …) writes the
    freq accumulator through a per-frame vibrato add: `LDA acc,X / CLC / ADC vib,X /
    STA $D400,Y`. The accumulator is the LDA operand (not the ADC/vibrato operand);
    the parser must find it and locate the (split) freq table chromatically."""
    m, la, h = _mod("Domino_Dancing")
    assert m.lay.freq and m.lay.freq_hi                # split table located
    assert (m.lay.sector_lo and m.lay.sound and m.lay.trk_lo)
    for note in (24, 36, 48, 60):
        assert freq_to_semi(m.note_freq(note)) == note


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_interleaved_track_generation():
    """Deel_2 / Fruitbank / Slimbo4 read the track ptr `TXA/ASL/TAY / LDA trk,Y`
    (interleaved lo/hi, indexed voice*2) — a read that also matched the sector sig
    first, mislabelling the sector table. The parser must set trk_interleaved, take
    the track from that idiom, and re-locate the real SPLIT sector table."""
    m, la, h = _mod("Deel_2")
    assert m.lay.trk_interleaved and m.lay.trk_lo == 0x6640
    assert m.lay.sector_lo == 0x66C1 and m.lay.sector_hi == 0x66FE  # split, corrected
    assert (m.lay.sound and m.lay.freq)                            # all four located
    assert not _mod("Balloon")[0].lay.trk_interleaved              # no regression


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_freq_table_is_chromatic():
    """The freq table must be a rising chromatic scale (~1.0595 per step)."""
    m, la, h = _mod("Balloon")
    prev = 0
    for note in range(2, 40):
        f = m.note_freq(note)
        assert f > prev, f"freq table not rising at note {note}"
        # each row within ~a semitone of the standard chromatic index
        assert abs(freq_to_semi(f) - note) <= 1
        prev = f


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_track_terminates():
    """Track decode stops at $FF (loop) / $FE (end), not a runaway."""
    m, la, h = _mod("Dummy_II")
    for v in range(3):
        sectors, loop = decode_track(m, v)
        assert len(sectors) < 512


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_decode_produces_notes():
    """decode_song yields tick-timed note events with valid pitches."""
    m, la, h = _mod("Dummy_II")
    voices = decode_song(m, tick_budget=200)
    assert sum(len(v) for v in voices) > 20
    notes = [n for v in voices for _, n in v if n.pitch >= 0]
    assert notes and all(0 <= n.pitch < 128 for n in notes)


@pytest.mark.skipif(not os.path.isdir(CORP), reason="Bjerregaard corpus absent")
def test_onset_validation_main_player():
    """A couple of main-player tunes decode to >=90% onset match vs siddump."""
    from sidm2.fidelity_common import siddump_note_onsets
    for name in ("Dummy_II", "Blobby"):
        path = os.path.join(CORP, f"{name}.sid")
        m, la, h = _mod(name)
        fpt = m.lay.tempo_reload + 1
        voices = decode_song(m, tick_budget=800)
        real = siddump_note_onsets(path, ["-a0", "-t12"])
        matched = total = 0
        for v in range(3):
            rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
            rf = set(fr for fr, _ in rl if fr < 560)
            if len(rf) < 3:
                continue
            pf = set(tk * fpt for tk, n in voices[v] if n.pitch >= 0)
            best = max(sum(1 for fr in rf if fr in set(x + ph for x in pf))
                       for ph in range(10))
            matched += best
            total += len(rf)
        assert total and 100 * matched / total >= 90, f"{name} onsets low"
