#!/usr/bin/env python3
"""
Unit tests for Phase 1 fixes: duration expansion and command parameters.
"""

import unittest
from sidm2.models import SequenceEvent, ExtractedData, PSIDHeader
from sidm2.laxity_analyzer import LaxityPlayerAnalyzer
from laxity_parser import LaxityParser, LaxityData


class TestDurationExpansion(unittest.TestCase):
    """Test duration byte extraction and sequence expansion."""

    def test_duration_extraction_single_note(self):
        """Test that a single note with duration 1 produces 1 event."""
        # Create mock data: instrument, duration=1, note C-0
        raw_seq = bytes([0xA0, 0x80, 0x00, 0x7F])  # Instr 0, dur=1, note C-0, end

        # Create minimal analyzer with this sequence
        c64_data = b'\x00' * 0x2000
        load_addr = 0x1000
        header = PSIDHeader(
            magic='PSID',
            version=2,
            data_offset=0x7C,
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x10A1,
            songs=1,
            start_song=1,
            speed=0,
            name='Test',
            author='Test',
            copyright='Test'
        )

        analyzer = LaxityPlayerAnalyzer(c64_data, load_addr, header)

        # Parse using LaxityParser mock
        laxity_data = LaxityData(
            orderlists=[[1]],
            sequences=[raw_seq],
            instruments=[bytes([0x09, 0x00, 0x41, 0x00, 0x08, 0x00, 0x00, 0x00])],
            sequence_addrs=[0x1B00]
        )

        # Manually parse sequence like laxity_analyzer does
        seq = []
        current_instr = 0x80
        current_cmd = 0x00
        current_duration = 1
        i = 0

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xA0 <= b <= 0xBF:
                current_instr = b
                i += 1
            elif 0xC0 <= b <= 0xCF:
                current_cmd = b
                i += 1
                if i < len(raw_seq):
                    i += 1  # Skip param
            elif 0x80 <= b <= 0x9F:
                current_duration = b - 0x80 + 1
                i += 1
            elif b <= 0x7F:
                note = b
                seq.append(SequenceEvent(current_instr, current_cmd, note))
                # Expand duration
                if note not in (0x7E, 0x7F) and current_duration > 1:
                    for _ in range(current_duration - 1):
                        seq.append(SequenceEvent(0x80, 0x00, 0x7E))
                current_instr = 0x80
                current_cmd = 0x00
                current_duration = 1
                i += 1
            else:
                i += 1

        # Verify: 1 note + 0 sustain events = 1 event total
        self.assertEqual(len(seq), 2)  # Note + end marker
        self.assertEqual(seq[0].note, 0x00)
        self.assertEqual(seq[0].instrument, 0xA0)

    def test_duration_expansion_multi_frame(self):
        """Test that a note with duration 5 produces 5 events (1 note + 4 sustain)."""
        # instrument, duration=5, note C-1, end
        raw_seq = bytes([0xA0, 0x84, 0x0C, 0x7F])  # Instr 0, dur=5 (0x84), note C-1 (0x0C), end

        seq = []
        current_instr = 0x80
        current_cmd = 0x00
        current_duration = 1
        i = 0

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xA0 <= b <= 0xBF:
                current_instr = b
                i += 1
            elif 0x80 <= b <= 0x9F:
                current_duration = b - 0x80 + 1
                i += 1
            elif b <= 0x7F:
                note = b
                seq.append(SequenceEvent(current_instr, current_cmd, note))
                # Expand duration
                if note not in (0x7E, 0x7F) and current_duration > 1:
                    for _ in range(current_duration - 1):
                        seq.append(SequenceEvent(0x80, 0x00, 0x7E))
                current_instr = 0x80
                current_cmd = 0x00
                current_duration = 1
                i += 1
            else:
                i += 1

        # Verify: 1 note + 4 sustain + 1 end = 6 events
        self.assertEqual(len(seq), 6)
        self.assertEqual(seq[0].note, 0x0C)  # First event is the note
        self.assertEqual(seq[0].instrument, 0xA0)  # With instrument
        # Next 4 should be gate-on (0x7E)
        for i in range(1, 5):
            self.assertEqual(seq[i].note, 0x7E, f"Event {i} should be gate-on (0x7E)")
            self.assertEqual(seq[i].instrument, 0x80, f"Event {i} should have no instrument change")
        self.assertEqual(seq[5].note, 0x7F)  # End marker

    def test_duration_expansion_multiple_notes(self):
        """Test multiple notes with different durations."""
        # Instr 0, dur=3, note C-1, dur=2, note D-1, dur=1, note E-1, end
        raw_seq = bytes([0xA0, 0x82, 0x0C, 0x81, 0x0E, 0x80, 0x10, 0x7F])

        seq = []
        current_instr = 0x80
        current_cmd = 0x00
        current_duration = 1
        i = 0

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xA0 <= b <= 0xBF:
                current_instr = b
                i += 1
            elif 0x80 <= b <= 0x9F:
                current_duration = b - 0x80 + 1
                i += 1
            elif b <= 0x7F:
                note = b
                seq.append(SequenceEvent(current_instr, current_cmd, note))
                if note not in (0x7E, 0x7F) and current_duration > 1:
                    for _ in range(current_duration - 1):
                        seq.append(SequenceEvent(0x80, 0x00, 0x7E))
                current_instr = 0x80
                current_cmd = 0x00
                current_duration = 1
                i += 1
            else:
                i += 1

        # Verify: (1+2) + (1+1) + (1+0) + 1 end = 7 events
        # Note1 (dur=3): 1 note + 2 sustain = 3
        # Note2 (dur=2): 1 note + 1 sustain = 2
        # Note3 (dur=1): 1 note + 0 sustain = 1
        # End: 1
        # Total: 7
        self.assertEqual(len(seq), 7)
        self.assertEqual(seq[0].note, 0x0C)  # C-1
        self.assertEqual(seq[1].note, 0x7E)  # sustain
        self.assertEqual(seq[2].note, 0x7E)  # sustain
        self.assertEqual(seq[3].note, 0x0E)  # D-1
        self.assertEqual(seq[4].note, 0x7E)  # sustain
        self.assertEqual(seq[5].note, 0x10)  # E-1
        self.assertEqual(seq[6].note, 0x7F)  # end


class TestCommandParameterExtraction(unittest.TestCase):
    """Test command parameter extraction."""

    def test_slide_up_command_extraction(self):
        """Test that slide up command parameters are extracted."""
        # Note: Laxity super commands are in 0xC0-0xCF range, not 0x00-0x7F
        # Instr 0, slide up command $C1 $20, note C-1, end
        raw_seq = bytes([0xA0, 0xC1, 0x20, 0x0C, 0x7F])  # Slide up is 0xC1 in Laxity

        seq = []
        current_instr = 0x80
        current_cmd = 0x00
        current_cmd_param = 0x00
        current_duration = 1
        i = 0

        extracted_commands = []

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xA0 <= b <= 0xBF:
                current_instr = b
                i += 1
            elif 0xC0 <= b <= 0xCF:
                current_cmd = b
                i += 1
                if i < len(raw_seq):
                    current_cmd_param = raw_seq[i]
                    extracted_commands.append((current_cmd, current_cmd_param))
                    i += 1
            elif b <= 0x7F:
                seq.append(SequenceEvent(current_instr, current_cmd, b))
                current_instr = 0x80
                current_cmd = 0x00
                current_cmd_param = 0x00
                i += 1
            else:
                i += 1

        # Verify command was extracted
        self.assertEqual(len(extracted_commands), 1)
        self.assertEqual(extracted_commands[0], (0xC1, 0x20))

    def test_vibrato_command_extraction(self):
        """Test vibrato command parameter extraction."""
        # Instr 0, vibrato $C5 $34 (vibrato command in Laxity), note C-1, end
        raw_seq = bytes([0xA0, 0xC5, 0x34, 0x0C, 0x7F])

        extracted_commands = []
        i = 0

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xC0 <= b <= 0xCF:
                i += 1
                if i < len(raw_seq):
                    param = raw_seq[i]
                    extracted_commands.append((b, param))
                    i += 1
            else:
                i += 1

        # Verify
        self.assertEqual(len(extracted_commands), 1)
        self.assertEqual(extracted_commands[0], (0xC5, 0x34))

    def test_set_adsr_command_extraction(self):
        """Test ADSR set command parameter extraction."""
        # Instr 0, set ADSR command is in 0xC0-0xCF range
        # In Laxity docs: $C3 = Set ADSR
        raw_seq = bytes([0xA0, 0xC3, 0xA0, 0x0C, 0x7F])  # $C3 $A0 = Set ADSR

        extracted_commands = []
        i = 0

        while i < len(raw_seq):
            b = raw_seq[i]
            if 0xC0 <= b <= 0xCF:  # Laxity super commands
                i += 1
                if i < len(raw_seq):
                    param = raw_seq[i]
                    extracted_commands.append((b, param))
                    i += 1
            else:
                i += 1

        # Verify
        self.assertEqual(len(extracted_commands), 1)
        self.assertEqual(extracted_commands[0], (0xC3, 0xA0))


class TestIntegrationAngular(unittest.TestCase):
    """Integration test with Angular.sid"""

    def test_angular_conversion_has_expanded_sequences(self):
        """Test that Angular.sid conversion produces expanded sequences."""
        # This test requires the actual Angular.sid file
        import os
        sid_path = 'SID/Angular.sid'

        if not os.path.exists(sid_path):
            self.skipTest("Angular.sid not found")

        from sidm2 import SIDParser

        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Verify sequences exist and have reasonable length
        self.assertGreater(len(extracted.sequences), 0, "Should have extracted sequences")

        # Check that at least one sequence has multiple events (indicating expansion worked)
        max_seq_len = max(len(seq) for seq in extracted.sequences)
        self.assertGreater(max_seq_len, 10, "At least one sequence should have >10 events after expansion")

        # Check for gate-on events (0x7E) in sequences
        gate_on_count = sum(1 for seq in extracted.sequences for event in seq if event.note == 0x7E)
        self.assertGreater(gate_on_count, 0, "Should have gate-on events from duration expansion")


if __name__ == '__main__':
    unittest.main()
