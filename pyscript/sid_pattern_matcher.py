"""SID Pattern Matcher - Ported from JC64 SIDId V1.09

This module provides pattern-based player detection for SID files.
Algorithm ported from JC64 (GPL-2.0) which was based on xSidplay2 SIDId V1.09.

Original algorithm by Cadaver (C) 2012
Python port by Claude Code (C) 2025

Pattern Format:
    PlayerName HH HH ?? and HH end

Where:
    HH   = Hex byte (00-FF)
    ??   = Wildcard (matches any byte)
    and  = AND operator (start new pattern search)
    end  = Pattern terminator

Example:
    Laxity_NewPlayer_v21 78 A9 00 8D 12 D4 end
    Matches: SEI, LDA #$00, STA $D412

License: GPL-2.0 (compatible with original JC64 license)
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PlayerPattern:
    """A single player pattern signature."""
    name: str
    patterns: List[List[int]]  # List of pattern byte arrays


class SIDPatternMatcher:
    """SID player detection using pattern matching.

    This class implements the SIDId V1.09 algorithm for identifying
    SID music players by searching for byte patterns in memory.

    Ported from: sw_emulator.software.SidId.java (JC64)
    Original algorithm: xSidplay2 SIDId V1.09 by Cadaver (C) 2012
    """

    # Pattern markers (from JC64 SidId.java)
    END = -1   # Pattern terminator
    ANY = -2   # Wildcard - matches any byte
    AND = -3   # AND operator - start new pattern search
    NAME = -4  # Player name marker (used in parsing)

    MAX_SIGSIZE = 4096  # Maximum pattern size

    VERSION = "SIDId V1.09 (Python port from JC64)"

    def __init__(self):
        """Initialize pattern matcher with empty pattern database."""
        self.players: List[PlayerPattern] = []
        self.last_match: str = ""

    def get_num_players(self) -> int:
        """Get the number of players in database."""
        return len(self.players)

    def get_num_patterns(self) -> int:
        """Get the total number of patterns across all players."""
        return sum(len(player.patterns) for player in self.players)

    def add_player(self, name: str, patterns: List[List[int]]) -> None:
        """Add a player with patterns to the database.

        Args:
            name: Player name
            patterns: List of pattern byte arrays (can contain END, ANY, AND markers)
        """
        self.players.append(PlayerPattern(name=name, patterns=patterns))

    def identify_buffer(self, buffer: bytes) -> str:
        """Identify player(s) in the given buffer.

        Scans all known players and returns names of any that match.

        Args:
            buffer: SID file data to scan

        Returns:
            Space-separated string of matched player names, or empty string if no match

        Example:
            >>> matcher = SIDPatternMatcher()
            >>> matcher.add_player("Laxity", [[0xA9, 0x00, matcher.END]])
            >>> result = matcher.identify_buffer(b"\\xA9\\x00\\x8D...")
            >>> print(result)
            'Laxity '
        """
        self.last_match = ""

        # Convert bytes to int array (like Java implementation)
        int_buffer = list(buffer)
        length = len(int_buffer)

        # Scan all players
        for player in self.players:
            # Try each pattern for this player
            for pattern in player.patterns:
                if self._identify_bytes(pattern, int_buffer, length):
                    self.last_match += player.name + " "
                    break  # Found match, move to next player

        return self.last_match

    def _identify_bytes(self, pattern: List[int], buffer: List[int], length: int) -> bool:
        """Core pattern matching algorithm.

        This is a direct port of the JC64 identifyBytes() method (lines 224-259).

        Algorithm:
            - c: current position in buffer
            - d: current position in pattern
            - rc: restart position in buffer (for backtracking)
            - rd: restart position in pattern (for backtracking)

        The algorithm searches for the pattern in the buffer, with support for:
            - Exact byte matching
            - Wildcards (ANY)
            - Multiple pattern searches (AND)
            - Backtracking on mismatch

        Args:
            pattern: Pattern byte array (with END, ANY, AND markers)
            buffer: File data as int array
            length: Length of buffer

        Returns:
            True if pattern matches, False otherwise
        """
        c = 0   # Buffer position
        d = 0   # Pattern position
        rc = 0  # Restart buffer position
        rd = 0  # Restart pattern position

        while c < length:
            if d == rd:
                # Starting new match attempt
                if buffer[c] == pattern[d]:
                    rc = c + 1
                    d += 1
                c += 1
            else:
                # Mid-pattern
                if pattern[d] == self.END:
                    return True  # Pattern matched!

                if pattern[d] == self.AND:
                    # AND operator - start searching for next pattern
                    d += 1
                    while c < length:
                        if buffer[c] == pattern[d]:
                            rc = c + 1
                            rd = d
                            break
                        c += 1

                    if c >= length:
                        return False  # Ran out of buffer

                # Check byte match (or wildcard)
                if (pattern[d] != self.ANY) and (buffer[c] != pattern[d]):
                    # Mismatch - backtrack
                    c = rc
                    d = rd
                else:
                    # Match or wildcard - advance
                    c += 1
                    d += 1

        # End of buffer - check if pattern is complete
        if d < len(pattern) and pattern[d] == self.END:
            return True

        return False

    def clear(self) -> None:
        """Clear all patterns from database."""
        self.players.clear()
        self.last_match = ""


class SIDPatternParser:
    """Parser for SIDId pattern files.

    Reads pattern files in JC64 format and builds pattern database.

    Pattern file format:
        PlayerName HH HH ?? and HH end
        AnotherPlayer A9 00 8D ?? ?? end
    """

    def __init__(self, matcher: SIDPatternMatcher):
        """Initialize parser.

        Args:
            matcher: SIDPatternMatcher to populate with parsed patterns
        """
        self.matcher = matcher

    def parse_file(self, filepath: Path) -> bool:
        """Parse pattern file and populate matcher.

        This is a port of the JC64 readConfig() method (lines 96-192).

        Args:
            filepath: Path to pattern file

        Returns:
            True if parsing succeeded, False on error

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If pattern format is invalid
        """
        try:
            self.matcher.clear()

            current_player: Optional[str] = None
            temp_pattern: List[int] = []

            with open(filepath, 'r') as f:
                for line in f:
                    tokens = line.strip().split()
                    if not tokens:
                        continue

                    for token in tokens:
                        if not token:
                            continue

                        # Determine token type
                        token_val = self.matcher.NAME  # Assume player name

                        if token in ('??',):
                            token_val = self.matcher.ANY
                        elif token.lower() in ('end',):
                            token_val = self.matcher.END
                        elif token.lower() in ('and',):
                            token_val = self.matcher.AND
                        elif len(token) == 2 and all(c in '0123456789ABCDEFabcdef' for c in token):
                            # Hex byte
                            token_val = int(token, 16)

                        # Process token
                        if token_val == self.matcher.NAME:
                            # New player name
                            if current_player is None:
                                current_player = token
                            else:
                                # Start of new player - finalize previous
                                if temp_pattern:
                                    raise ValueError(f"Incomplete pattern before '{token}'")
                                current_player = token

                        elif token_val == self.matcher.END:
                            # End of pattern
                            if len(temp_pattern) >= self.matcher.MAX_SIGSIZE:
                                raise ValueError("Maximum signature size exceeded")

                            temp_pattern.append(self.matcher.END)

                            if len(temp_pattern) > 1:
                                if current_player is None:
                                    raise ValueError("No player name defined before pattern")

                                # Add pattern to this player
                                # Find or create player entry
                                player_entry = None
                                for player in self.matcher.players:
                                    if player.name == current_player:
                                        player_entry = player
                                        break

                                if player_entry is None:
                                    # Create new player
                                    self.matcher.add_player(current_player, [temp_pattern[:]])
                                else:
                                    # Add pattern to existing player
                                    player_entry.patterns.append(temp_pattern[:])

                            temp_pattern = []

                        else:
                            # Regular token (byte, ANY, AND)
                            if len(temp_pattern) >= self.matcher.MAX_SIGSIZE:
                                raise ValueError("Maximum signature size exceeded")
                            temp_pattern.append(token_val)

            return True

        except Exception as e:
            print(f"Error parsing pattern file: {e}")
            return False

    def write_file(self, filepath: Path) -> bool:
        """Write current patterns to file in JC64 format.

        Args:
            filepath: Output file path

        Returns:
            True if successful
        """
        try:
            with open(filepath, 'w') as f:
                for player in self.matcher.players:
                    for pattern in player.patterns:
                        # Write player name
                        f.write(player.name)

                        # Write pattern bytes
                        for val in pattern:
                            if val == self.matcher.END:
                                f.write(" end")
                            elif val == self.matcher.ANY:
                                f.write(" ??")
                            elif val == self.matcher.AND:
                                f.write(" and")
                            else:
                                f.write(f" {val:02X}")

                        f.write("\n")

            return True

        except Exception as e:
            print(f"Error writing pattern file: {e}")
            return False


def test_pattern_matcher():
    """Quick test of pattern matcher functionality."""
    print("Testing SID Pattern Matcher...")
    print("-" * 60)

    # Create matcher
    matcher = SIDPatternMatcher()

    # Test 1: Simple exact match
    print("\nTest 1: Simple exact match")
    pattern1 = [0xA9, 0x00, matcher.END]  # LDA #$00
    matcher.add_player("Test1", [pattern1])

    buffer1 = bytes([0xA9, 0x00, 0x8D, 0x00, 0xD4])  # LDA #$00, STA $D400
    result1 = matcher.identify_buffer(buffer1)
    print(f"  Pattern: LDA #$00")
    print(f"  Buffer:  A9 00 8D 00 D4")
    print(f"  Result:  '{result1.strip()}'")
    print(f"  Status:  {'PASS' if 'Test1' in result1 else 'FAIL'}")

    # Test 2: Wildcard match
    print("\nTest 2: Wildcard match")
    matcher.clear()
    pattern2 = [0xA9, matcher.ANY, 0x8D, matcher.ANY, matcher.ANY, matcher.END]  # LDA #??, STA ????
    matcher.add_player("Test2", [pattern2])

    buffer2 = bytes([0xA9, 0xFF, 0x8D, 0x12, 0xD4])  # LDA #$FF, STA $D412
    result2 = matcher.identify_buffer(buffer2)
    print(f"  Pattern: LDA #??, STA ??:??")
    print(f"  Buffer:  A9 FF 8D 12 D4")
    print(f"  Result:  '{result2.strip()}'")
    print(f"  Status:  {'PASS' if 'Test2' in result2 else 'FAIL'}")

    # Test 3: AND operator
    print("\nTest 3: AND operator")
    matcher.clear()
    pattern3 = [0x78, matcher.END, matcher.AND, 0xA9, 0x00, matcher.END]  # SEI ... LDA #$00
    matcher.add_player("Test3", [pattern3])

    buffer3 = bytes([0x78, 0xA2, 0x00, 0xA9, 0x00])  # SEI, LDX #$00, LDA #$00
    result3 = matcher.identify_buffer(buffer3)
    print(f"  Pattern: SEI and LDA #$00")
    print(f"  Buffer:  78 A2 00 A9 00")
    print(f"  Result:  '{result3.strip()}'")
    print(f"  Status:  {'PASS' if 'Test3' in result3 else 'FAIL'}")

    # Test 4: Multiple players
    print("\nTest 4: Multiple players")
    matcher.clear()
    matcher.add_player("Laxity", [[0x78, 0xA9, 0x00, matcher.END]])
    matcher.add_player("Galway", [[0xA9, 0x00, 0x8D, matcher.END]])

    buffer4 = bytes([0x78, 0xA9, 0x00, 0x8D, 0x00, 0xD4])  # Contains both patterns
    result4 = matcher.identify_buffer(buffer4)
    print(f"  Players: Laxity (78 A9 00), Galway (A9 00 8D)")
    print(f"  Buffer:  78 A9 00 8D 00 D4")
    print(f"  Result:  '{result4.strip()}'")
    print(f"  Status:  {'PASS' if 'Laxity' in result4 and 'Galway' in result4 else 'FAIL'}")

    print("\n" + "=" * 60)
    print(f"Pattern Matcher Test Complete")
    print(f"Players: {matcher.get_num_players()}")
    print(f"Patterns: {matcher.get_num_patterns()}")
    print("=" * 60)


if __name__ == "__main__":
    test_pattern_matcher()
