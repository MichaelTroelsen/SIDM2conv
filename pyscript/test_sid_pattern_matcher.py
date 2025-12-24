"""Unit tests for SID Pattern Matcher

Tests the pattern matching algorithm ported from JC64 SIDId V1.09.
"""

import pytest
from pathlib import Path
from pyscript.sid_pattern_matcher import SIDPatternMatcher, SIDPatternParser, PlayerPattern


class TestSIDPatternMatcher:
    """Test suite for SID pattern matcher."""

    @pytest.fixture
    def matcher(self):
        """Create a fresh matcher for each test."""
        return SIDPatternMatcher()

    def test_initialization(self, matcher):
        """Test matcher initializes correctly."""
        assert matcher.get_num_players() == 0
        assert matcher.get_num_patterns() == 0
        assert matcher.last_match == ""

    def test_add_player(self, matcher):
        """Test adding a player with patterns."""
        pattern1 = [0xA9, 0x00, matcher.END]
        pattern2 = [0x78, matcher.END]

        matcher.add_player("TestPlayer", [pattern1, pattern2])

        assert matcher.get_num_players() == 1
        assert matcher.get_num_patterns() == 2

    def test_simple_exact_match(self, matcher):
        """Test exact byte matching."""
        # Pattern: LDA #$00
        pattern = [0xA9, 0x00, matcher.END]
        matcher.add_player("Test", [pattern])

        # Buffer contains pattern
        buffer = bytes([0xA9, 0x00, 0x8D, 0x00, 0xD4])
        result = matcher.identify_buffer(buffer)

        assert "Test" in result

    def test_simple_no_match(self, matcher):
        """Test non-matching pattern."""
        # Pattern: LDA #$00
        pattern = [0xA9, 0x00, matcher.END]
        matcher.add_player("Test", [pattern])

        # Buffer doesn't contain pattern
        buffer = bytes([0xA9, 0x01, 0x8D, 0x00, 0xD4])
        result = matcher.identify_buffer(buffer)

        assert "Test" not in result
        assert result == ""

    def test_wildcard_match(self, matcher):
        """Test wildcard (ANY) matching."""
        # Pattern: LDA #??, STA ????
        pattern = [0xA9, matcher.ANY, 0x8D, matcher.ANY, matcher.ANY, matcher.END]
        matcher.add_player("Wildcard", [pattern])

        # Should match with any values in wildcard positions
        buffer = bytes([0xA9, 0xFF, 0x8D, 0x12, 0xD4])
        result = matcher.identify_buffer(buffer)

        assert "Wildcard" in result

    def test_wildcard_multiple_values(self, matcher):
        """Test wildcard matches different values."""
        pattern = [0xA9, matcher.ANY, matcher.END]
        matcher.add_player("Any", [pattern])

        # Should match LDA #$00, LDA #$FF, LDA #$42
        for value in [0x00, 0xFF, 0x42]:
            buffer = bytes([0xA9, value, 0x60])
            result = matcher.identify_buffer(buffer)
            assert "Any" in result, f"Failed for value ${value:02X}"

    def test_and_operator(self, matcher):
        """Test AND operator - multiple pattern search."""
        # Pattern: SEI ... LDA #$00 (somewhere later in buffer)
        pattern = [0x78, matcher.AND, 0xA9, 0x00, matcher.END]
        matcher.add_player("AndTest", [pattern])

        # Buffer: SEI, LDX #$00, LDA #$00
        buffer = bytes([0x78, 0xA2, 0x00, 0xA9, 0x00])
        result = matcher.identify_buffer(buffer)

        assert "AndTest" in result

    def test_and_operator_no_second_pattern(self, matcher):
        """Test AND operator fails if second pattern not found."""
        pattern = [0x78, matcher.AND, 0xA9, 0xFF, matcher.END]
        matcher.add_player("AndFail", [pattern])

        # Has SEI but not LDA #$FF
        buffer = bytes([0x78, 0xA2, 0x00, 0xA9, 0x00])
        result = matcher.identify_buffer(buffer)

        assert "AndFail" not in result

    def test_pattern_at_start_of_buffer(self, matcher):
        """Test pattern at beginning of buffer."""
        pattern = [0x78, 0xA9, 0x00, matcher.END]
        matcher.add_player("Start", [pattern])

        buffer = bytes([0x78, 0xA9, 0x00, 0x60])
        result = matcher.identify_buffer(buffer)

        assert "Start" in result

    def test_pattern_at_end_of_buffer(self, matcher):
        """Test pattern at end of buffer."""
        pattern = [0xA9, 0x00, 0x60, matcher.END]
        matcher.add_player("End", [pattern])

        buffer = bytes([0x78, 0xA2, 0xFF, 0xA9, 0x00, 0x60])
        result = matcher.identify_buffer(buffer)

        assert "End" in result

    def test_pattern_not_in_buffer(self, matcher):
        """Test pattern completely absent from buffer."""
        pattern = [0xDE, 0xAD, 0xBE, 0xEF, matcher.END]
        matcher.add_player("NotFound", [pattern])

        buffer = bytes([0xA9, 0x00, 0x8D, 0x00, 0xD4])
        result = matcher.identify_buffer(buffer)

        assert "NotFound" not in result

    def test_multiple_players_single_match(self, matcher):
        """Test multiple players with one match."""
        matcher.add_player("Player1", [[0xA9, 0x00, matcher.END]])
        matcher.add_player("Player2", [[0xDE, 0xAD, matcher.END]])
        matcher.add_player("Player3", [[0x78, matcher.END]])

        buffer = bytes([0x78, 0xA2, 0x00])
        result = matcher.identify_buffer(buffer)

        assert "Player3" in result
        assert "Player1" not in result
        assert "Player2" not in result

    def test_multiple_players_multiple_matches(self, matcher):
        """Test multiple players with multiple matches."""
        matcher.add_player("Laxity", [[0x78, 0xA9, matcher.END]])
        matcher.add_player("Galway", [[0xA9, 0x00, matcher.END]])

        buffer = bytes([0x78, 0xA9, 0x00, 0x60])
        result = matcher.identify_buffer(buffer)

        assert "Laxity" in result
        assert "Galway" in result

    def test_player_with_multiple_patterns(self, matcher):
        """Test player with multiple alternative patterns."""
        pattern1 = [0x78, 0xA9, matcher.END]
        pattern2 = [0xA9, 0x00, 0x8D, matcher.END]

        matcher.add_player("Multi", [pattern1, pattern2])

        # Should match first pattern
        buffer1 = bytes([0x78, 0xA9, 0x00])
        assert "Multi" in matcher.identify_buffer(buffer1)

        # Should match second pattern
        buffer2 = bytes([0xA9, 0x00, 0x8D, 0x00])
        assert "Multi" in matcher.identify_buffer(buffer2)

    def test_backtracking(self, matcher):
        """Test pattern backtracking on partial match."""
        # Pattern that requires backtracking
        pattern = [0xA9, 0x00, 0xA9, 0x00, matcher.END]
        matcher.add_player("Backtrack", [pattern])

        # Buffer: A9 00 A9 01 A9 00 A9 00
        # Should find second occurrence after backtracking
        buffer = bytes([0xA9, 0x00, 0xA9, 0x01, 0xA9, 0x00, 0xA9, 0x00])
        result = matcher.identify_buffer(buffer)

        assert "Backtrack" in result

    def test_long_pattern(self, matcher):
        """Test longer pattern matching."""
        # Pattern: 16 bytes
        pattern = [0x78, 0xA9, 0x00, 0xAA, 0x9D, 0x00, 0xD4, 0xCA,
                  0x10, 0xFB, 0xA9, 0x0F, 0x8D, 0x18, 0xD4, 0x58, matcher.END]
        matcher.add_player("LongPattern", [pattern])

        buffer = bytes([0x78, 0xA9, 0x00, 0xAA, 0x9D, 0x00, 0xD4, 0xCA,
                       0x10, 0xFB, 0xA9, 0x0F, 0x8D, 0x18, 0xD4, 0x58, 0x60])
        result = matcher.identify_buffer(buffer)

        assert "LongPattern" in result

    def test_empty_buffer(self, matcher):
        """Test with empty buffer."""
        pattern = [0xA9, 0x00, matcher.END]
        matcher.add_player("Test", [pattern])

        buffer = bytes([])
        result = matcher.identify_buffer(buffer)

        assert result == ""

    def test_empty_pattern_list(self, matcher):
        """Test player with no patterns."""
        matcher.add_player("Empty", [])

        buffer = bytes([0xA9, 0x00])
        result = matcher.identify_buffer(buffer)

        assert "Empty" not in result

    def test_clear(self, matcher):
        """Test clearing all patterns."""
        matcher.add_player("Test1", [[0xA9, matcher.END]])
        matcher.add_player("Test2", [[0x78, matcher.END]])

        assert matcher.get_num_players() == 2

        matcher.clear()

        assert matcher.get_num_players() == 0
        assert matcher.get_num_patterns() == 0

    def test_real_laxity_pattern(self, matcher):
        """Test with real Laxity NewPlayer pattern."""
        # Laxity NewPlayer v21 init sequence
        pattern = [0x78, 0xA9, 0x00, 0x8D, 0x12, 0xD4, matcher.END]
        matcher.add_player("Laxity_NewPlayer_v21", [pattern])

        # Simulated init code: SEI, LDA #$00, STA $D412, ...
        buffer = bytes([0x78, 0xA9, 0x00, 0x8D, 0x12, 0xD4, 0x8D, 0x0D, 0xD4])
        result = matcher.identify_buffer(buffer)

        assert "Laxity_NewPlayer_v21" in result

    def test_real_galway_pattern(self, matcher):
        """Test with real Martin Galway pattern."""
        # Martin Galway typical init: LDA #$00, STA $D400, ... JMP
        pattern = [0xA9, 0x00, 0x8D, 0x00, 0xD4, matcher.AND, 0x4C, matcher.ANY, matcher.ANY, matcher.END]
        matcher.add_player("Martin_Galway", [pattern])

        # Simulated code
        buffer = bytes([0xA9, 0x00, 0x8D, 0x00, 0xD4, 0xA2, 0x00, 0x4C, 0x00, 0x10])
        result = matcher.identify_buffer(buffer)

        assert "Martin_Galway" in result


class TestSIDPatternParser:
    """Test suite for SID pattern file parser."""

    @pytest.fixture
    def matcher(self):
        """Create a fresh matcher."""
        return SIDPatternMatcher()

    @pytest.fixture
    def parser(self, matcher):
        """Create a parser with matcher."""
        return SIDPatternParser(matcher)

    @pytest.fixture
    def temp_pattern_file(self, tmp_path):
        """Create a temporary pattern file."""
        return tmp_path / "test_patterns.txt"

    def test_parse_simple_pattern(self, parser, temp_pattern_file):
        """Test parsing simple pattern file."""
        content = "TestPlayer 78 A9 00 end\n"
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True
        assert parser.matcher.get_num_players() == 1
        assert parser.matcher.get_num_patterns() == 1

    def test_parse_wildcard_pattern(self, parser, temp_pattern_file):
        """Test parsing pattern with wildcards."""
        content = "Wildcard A9 ?? 8D ?? ?? end\n"
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True

        # Test that wildcard works
        buffer = bytes([0xA9, 0xFF, 0x8D, 0x12, 0xD4])
        match_result = parser.matcher.identify_buffer(buffer)
        assert "Wildcard" in match_result

    def test_parse_and_operator(self, parser, temp_pattern_file):
        """Test parsing pattern with AND operator."""
        content = "AndTest 78 and A9 00 end\n"
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True

        # Test that AND works
        buffer = bytes([0x78, 0xA2, 0x00, 0xA9, 0x00])
        match_result = parser.matcher.identify_buffer(buffer)
        assert "AndTest" in match_result

    def test_parse_multiple_players(self, parser, temp_pattern_file):
        """Test parsing multiple players."""
        content = """Laxity 78 A9 00 end
Galway A9 00 8D 00 D4 end
Hubbard 78 A9 1F end
"""
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True
        assert parser.matcher.get_num_players() == 3
        assert parser.matcher.get_num_patterns() == 3

    def test_parse_multiple_patterns_per_player(self, parser, temp_pattern_file):
        """Test player with multiple patterns."""
        content = """Laxity 78 A9 00 end
Laxity A2 00 BD 00 1A end
"""
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True
        assert parser.matcher.get_num_players() == 1
        assert parser.matcher.get_num_patterns() == 2

    def test_parse_case_insensitive(self, parser, temp_pattern_file):
        """Test case insensitive keywords."""
        content = "Test 78 AND A9 00 END\n"
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True

    def test_parse_empty_lines(self, parser, temp_pattern_file):
        """Test parsing with empty lines."""
        content = """
Laxity 78 A9 00 end

Galway A9 00 end

"""
        temp_pattern_file.write_text(content)

        result = parser.parse_file(temp_pattern_file)

        assert result is True
        assert parser.matcher.get_num_players() == 2

    def test_write_pattern_file(self, parser, matcher, temp_pattern_file):
        """Test writing patterns back to file."""
        # Add patterns manually
        matcher.add_player("Test1", [[0x78, 0xA9, 0x00, matcher.END]])
        matcher.add_player("Test2", [[0xA9, matcher.ANY, matcher.END]])

        # Write to file
        result = parser.write_file(temp_pattern_file)

        assert result is True
        assert temp_pattern_file.exists()

        # Read back and verify
        content = temp_pattern_file.read_text()
        assert "Test1" in content
        assert "78 A9 00 end" in content
        assert "Test2" in content
        assert "A9 ?? end" in content

    def test_roundtrip(self, parser, temp_pattern_file):
        """Test parse then write produces equivalent result."""
        original_content = """Laxity 78 A9 00 end
Galway A9 ?? 8D ?? ?? end
"""
        temp_pattern_file.write_text(original_content)

        # Parse
        parser.parse_file(temp_pattern_file)

        # Write to new file
        output_file = temp_pattern_file.parent / "output.txt"
        parser.write_file(output_file)

        # Parse output file into new matcher
        new_matcher = SIDPatternMatcher()
        new_parser = SIDPatternParser(new_matcher)
        new_parser.parse_file(output_file)

        # Should have same number of players/patterns
        assert new_matcher.get_num_players() == parser.matcher.get_num_players()
        assert new_matcher.get_num_patterns() == parser.matcher.get_num_patterns()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
