"""Unit tests for sidm2.sf2_to_np21_tables — SF2-edit-area → NP21
table format conversions (Stage 7 Phase A).
"""
import pytest

from sidm2.sf2_to_np21_tables import (
    convert_wave_table,
    convert_instruments_table,
    convert_pulse_table,
)


# ---------------------------------------------------------------------------
# Wave: identity copy
# ---------------------------------------------------------------------------

class TestWaveTable:
    def test_identity_copy(self):
        sf2 = bytes(range(64))   # 32 rows × 2 cols
        out = convert_wave_table(sf2, n_rows=32)
        assert out == sf2

    def test_short_input_raises(self):
        with pytest.raises(ValueError, match="too short"):
            convert_wave_table(b'\x00' * 10, n_rows=32)

    def test_returns_exactly_n_rows(self):
        sf2 = bytes(range(128))   # 64 rows × 2 cols
        out = convert_wave_table(sf2, n_rows=8)
        assert len(out) == 16
        assert out == sf2[:16]

    def test_edit_propagates_byte_for_byte(self):
        sf2 = bytearray(64)
        # Simulate "user edits row 5 wave to (note=$0F, waveform=$41)"
        sf2[5 * 2 + 0] = 0x0F
        sf2[5 * 2 + 1] = 0x41
        out = convert_wave_table(bytes(sf2))
        assert out[10] == 0x0F
        assert out[11] == 0x41


# ---------------------------------------------------------------------------
# Instruments: NP21 8-byte rows merged with SF2 6-col rows
# ---------------------------------------------------------------------------

class TestInstrumentsTable:
    def _np21_row(self, ad, sr, restart, flags2, flags3, pulse_param, pulse_ptr, wave_ptr):
        return bytes([ad, sr, restart, flags2, flags3, pulse_param, pulse_ptr, wave_ptr])

    def _sf2_row(self, ad, sr, hr, filt, pulse, wave):
        return bytes([ad, sr, hr, filt, pulse, wave])

    def test_no_edit_round_trips_with_preserve(self):
        """When SF2 view exactly mirrors what was extracted (AD, SR, HR,
        0=Filter, Pulse_ptr, Wave_ptr), and we feed back the same values,
        the result equals the original NP21 row byte-for-byte (since
        bytes 3/4/5 come straight from np21_existing)."""
        np21 = self._np21_row(0x09, 0xA0, 0x01, 0xAA, 0xBB, 0xCC, 0x05, 0x07)
        sf2  = self._sf2_row(0x09, 0xA0, 0x01, 0x00, 0x05, 0x07)
        out = convert_instruments_table(sf2, np21, n_rows=1)
        assert out == np21

    def test_ad_edit_propagates(self):
        np21 = self._np21_row(0x09, 0xA0, 0x01, 0xAA, 0xBB, 0xCC, 0x05, 0x07)
        sf2  = self._sf2_row(0xF7, 0xA0, 0x01, 0x00, 0x05, 0x07)   # AD edited
        out = convert_instruments_table(sf2, np21, n_rows=1)
        assert out[0] == 0xF7   # AD propagated
        # bytes 3/4/5 preserved
        assert out[3] == 0xAA
        assert out[4] == 0xBB
        assert out[5] == 0xCC

    def test_pulse_and_wave_edits_propagate_to_correct_bytes(self):
        np21 = self._np21_row(0x09, 0xA0, 0x01, 0xAA, 0xBB, 0xCC, 0x05, 0x07)
        sf2  = self._sf2_row(0x09, 0xA0, 0x01, 0x00, 0x12, 0x34)   # Pulse, Wave edited
        out = convert_instruments_table(sf2, np21, n_rows=1)
        assert out[6] == 0x12   # Pulse ptr → NP21 byte 6
        assert out[7] == 0x34   # Wave ptr  → NP21 byte 7

    def test_filter_column_not_propagated(self):
        """SF2 col 3 (Filter) is not propagated — NP21's filter selection
        is global per song, not per-instrument. Even if user sets a
        nonzero value in F2 col 3, the NP21 binary's filter byte stays
        unchanged. (We don't have a target byte for it anyway.)"""
        np21 = self._np21_row(0x09, 0xA0, 0x01, 0xAA, 0xBB, 0xCC, 0x05, 0x07)
        sf2  = self._sf2_row(0x09, 0xA0, 0x01, 0xFF, 0x05, 0x07)   # Filter=0xFF
        out = convert_instruments_table(sf2, np21, n_rows=1)
        # NP21 bytes 3/4/5 are preserved from existing — they don't pick
        # up the SF2 Filter column at all
        assert out[3] == 0xAA
        assert out[4] == 0xBB
        assert out[5] == 0xCC

    def test_hr_byte_propagates_to_np21_byte_2(self):
        np21 = self._np21_row(0x09, 0xA0, 0x01, 0xAA, 0xBB, 0xCC, 0x05, 0x07)
        sf2  = self._sf2_row(0x09, 0xA0, 0x42, 0x00, 0x05, 0x07)   # HR edited
        out = convert_instruments_table(sf2, np21, n_rows=1)
        assert out[2] == 0x42

    def test_multiple_rows(self):
        np21 = b''.join(self._np21_row(i, i+1, i+2, 0xAA, 0xBB, 0xCC, i+6, i+7) for i in range(4))
        sf2  = b''.join(self._sf2_row(i, i+1, i+2, 0, i+6, i+7) for i in range(4))
        out = convert_instruments_table(sf2, np21, n_rows=4)
        assert out == np21   # no edits → exact byte-for-byte

    def test_short_sf2_raises(self):
        np21 = b'\x00' * (32 * 8)
        sf2  = b'\x00' * 10
        with pytest.raises(ValueError, match="SF2 instr"):
            convert_instruments_table(sf2, np21, n_rows=32)

    def test_short_np21_raises(self):
        np21 = b'\x00' * 10
        sf2  = b'\x00' * (32 * 6)
        with pytest.raises(ValueError, match="NP21 existing"):
            convert_instruments_table(sf2, np21, n_rows=32)


# ---------------------------------------------------------------------------
# Pulse: 3-col SF2 → 4-col NP21, preserve byte 3
# ---------------------------------------------------------------------------

class TestPulseTable:
    def test_first_three_bytes_propagate(self):
        np21 = bytes([0xAA, 0xBB, 0xCC, 0xDD])    # one row
        sf2  = bytes([0x11, 0x22, 0x33])
        out = convert_pulse_table(sf2, np21, n_rows=1)
        assert out == bytes([0x11, 0x22, 0x33, 0xDD])

    def test_byte_3_preserved(self):
        np21 = bytes([0xAA, 0xBB, 0xCC, 0xDD])
        sf2  = bytes([0xAA, 0xBB, 0xCC])   # no edit
        out = convert_pulse_table(sf2, np21, n_rows=1)
        assert out[3] == 0xDD

    def test_multiple_rows(self):
        np21 = bytes(range(16 * 4))
        sf2  = bytes(range(16 * 3))
        out = convert_pulse_table(sf2, np21, n_rows=16)
        assert len(out) == 64
        for r in range(16):
            assert out[r*4 + 0] == sf2[r*3 + 0]
            assert out[r*4 + 1] == sf2[r*3 + 1]
            assert out[r*4 + 2] == sf2[r*3 + 2]
            assert out[r*4 + 3] == np21[r*4 + 3]

    def test_short_inputs_raise(self):
        with pytest.raises(ValueError, match="SF2 pulse"):
            convert_pulse_table(b'', b'\x00' * 64, n_rows=16)
        with pytest.raises(ValueError, match="NP21 existing"):
            convert_pulse_table(b'\x00' * 48, b'', n_rows=16)


# ---------------------------------------------------------------------------
# Round-trip property: extract → render → write-back = identity (no edit)
# ---------------------------------------------------------------------------

class TestRoundTripProperty:
    """If we extract an NP21 table to SF2 format and then write it
    straight back through these conversions (no user edit), the
    resulting NP21 bytes should equal the original. This is the
    edit-propagation correctness property: zero edits must produce
    a no-op round trip."""

    def test_instruments_round_trip_identity(self):
        # Mirror the writer's Stage 3 emit (sf2_writer.py:2879-2891):
        #   sf2[0]=ad, sf2[1]=sr, sf2[2]=restart, sf2[3]=0,
        #   sf2[4]=pulse_ptr (NP21 byte 6), sf2[5]=wave_ptr (NP21 byte 7)
        np21 = b''.join([bytes([
            (i*7 + 1) & 0xFF,   # ad
            (i*7 + 2) & 0xFF,   # sr
            (i*7 + 3) & 0xFF,   # restart (flags1)
            (i*7 + 4) & 0xFF,   # flags2
            (i*7 + 5) & 0xFF,   # flags3
            (i*7 + 6) & 0xFF,   # pulse_param
            (i*7 + 7) & 0xFF,   # pulse_ptr
            (i*7 + 8) & 0xFF,   # wave_ptr
        ]) for i in range(32)])

        # Synthesise the SF2 edit area from np21 (mirroring writer's
        # Stage 3 logic):
        sf2 = bytearray()
        for i in range(32):
            base = i * 8
            sf2.extend([
                np21[base + 0],   # AD
                np21[base + 1],   # SR
                np21[base + 2],   # HR (= flags1)
                0x00,             # Filter (synthesised 0)
                np21[base + 6],   # Pulse ptr
                np21[base + 7],   # Wave ptr
            ])

        # Write back through the converter
        out = convert_instruments_table(bytes(sf2), np21, n_rows=32)
        assert out == np21, "round-trip identity broken for instruments"

    def test_pulse_round_trip_identity(self):
        np21 = bytes(range(16 * 4))
        # Synthesise SF2 from np21 (drop byte 3 of each 4-byte row)
        sf2 = bytearray()
        for r in range(16):
            sf2.extend(np21[r*4 + 0 : r*4 + 3])
        out = convert_pulse_table(bytes(sf2), np21, n_rows=16)
        assert out == np21, "round-trip identity broken for pulse"

    def test_wave_round_trip_identity(self):
        np21 = bytes(range(64))
        # Wave is identity
        sf2 = np21
        out = convert_wave_table(sf2, n_rows=32)
        assert out == np21
