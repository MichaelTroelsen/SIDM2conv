"""Check entry point patterns of undetected Laxity files."""

from pathlib import Path
import sys

# Undetected files (from find_undetected_laxity.py)
undetected = [
    "21_G4_demo_tune_3.sid", "Basics.sid", "Beastie_Boys_Intro_Music.sid",
    "Blue_Blop.sid", "Bountyhunter-Destiny_Now.sid", "Dead_Iron.sid",
    "Demo_Music.sid", "Flintstones.sid", "Galaxylogo.sid", "Heart_Beat.sid",
    "Ikari_Intro.sid", "Ikari_Intro_Song.sid", "Introtune.sid",
    "James_Bond_Theme_Remix.sid", "Kick_Ass.sid", "Lax_Selector.sid",
    "Laxace.sid", "Manimalize.sid", "Musique.sid", "No_Nothing.sid",
    "Ocean_Reloaded.sid", "Pink_Panther.sid", "Pocket_Freeze.sid",
    "Proven_Notes.sid", "Realistic_Crap.sid", "Repeat_me.sid",
    "Short_Tune.sid", "Sigma_Logo.sid", "Thyge.sid", "Twone_Five.sid",
    "Upfront.sid", "Uppercut.sid", "Waste.sid", "Wind_Blows.sid", "Wisdom.sid"
]


def parse_sid_header(sid_data: bytes) -> dict:
    """Parse PSID/RSID file header."""
    if len(sid_data) < 0x7C:
        return None

    magic = sid_data[0:4].decode('ascii', errors='ignore')
    if magic not in ('PSID', 'RSID'):
        return None

    data_offset = (sid_data[6] << 8) | sid_data[7]
    load_addr = (sid_data[8] << 8) | sid_data[9]
    play_addr = (sid_data[0xC] << 8) | sid_data[0xD]

    if load_addr == 0 and len(sid_data) > data_offset + 2:
        load_addr = sid_data[data_offset] | (sid_data[data_offset + 1] << 8)
        code_start = data_offset + 2
    else:
        code_start = data_offset

    return {
        'load_addr': load_addr,
        'play_addr': play_addr,
        'code_start': code_start,
    }


def main():
    laxity_dir = Path(__file__).parent.parent / "Laxity"

    print("Entry Point Patterns of Undetected Laxity Files")
    print("=" * 80)
    print(f"{'File':<40} {'First 12 bytes (hex)'}")
    print("-" * 80)

    for filename in undetected:
        filepath = laxity_dir / filename
        if not filepath.exists():
            print(f"{filename:<40} FILE NOT FOUND")
            continue

        sid_data = filepath.read_bytes()
        header = parse_sid_header(sid_data)
        if not header:
            print(f"{filename:<40} INVALID HEADER")
            continue

        # Get first 12 bytes of code
        code_start = header['code_start']
        code_bytes = sid_data[code_start:code_start + 12]
        hex_str = ' '.join(f'{b:02X}' for b in code_bytes)

        # Decode first instruction (usually JMP)
        play_offset = header['play_addr'] - header['load_addr']

        print(f"{filename:<40} {hex_str} (play@+{play_offset:02X})")

    print("-" * 80)


if __name__ == "__main__":
    main()
