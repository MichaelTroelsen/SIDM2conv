"""Find Laxity files not detected as Laxity_NewPlayer_v21."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.sid_pattern_matcher import SIDPatternMatcher, SIDPatternParser


def main():
    # Load pattern database
    pattern_file = Path(__file__).parent / 'sidid_patterns.txt'
    matcher = SIDPatternMatcher()
    parser = SIDPatternParser(matcher)

    if not parser.parse_file(pattern_file):
        print(f"Failed to load pattern file: {pattern_file}")
        return 1

    # Test Laxity files
    laxity_dir = Path(__file__).parent.parent / "Laxity"
    sid_files = sorted(laxity_dir.glob("*.sid"))

    print(f"Scanning {len(sid_files)} Laxity files...")
    print("=" * 70)

    not_laxity = []

    for sid_file in sid_files:
        sid_data = sid_file.read_bytes()
        result = matcher.identify_buffer(sid_data)
        detected = [name.strip() for name in result.split() if name.strip()]

        if "Laxity_NewPlayer_v21" not in detected:
            not_laxity.append((sid_file.name, detected))

    print(f"\nFiles NOT detected as Laxity_NewPlayer_v21: {len(not_laxity)}")
    print("=" * 70)

    for filename, detected in not_laxity:
        if detected:
            print(f"{filename}: {', '.join(detected)}")
        else:
            print(f"{filename}: (no match)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
