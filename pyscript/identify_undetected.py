"""Identify actual players used in undetected Laxity files."""

import subprocess
from pathlib import Path

undetected = [
    "Dead_Iron.sid",
    "Lax_Selector.sid",
    "Laxace.sid",
    "Musique.sid",
    "No_Nothing.sid",
    "Ocean_Reloaded.sid",
    "Repeat_me.sid",
    "Twone_Five.sid",
    "Waste.sid"
]

laxity_dir = Path(__file__).parent.parent / "Laxity"
player_id = Path(__file__).parent.parent / "tools" / "player-id.exe"

print("Identifying actual players in undetected files")
print("=" * 70)
print(f"{'File':<40} {'Identified Player'}")
print("-" * 70)

for filename in undetected:
    filepath = laxity_dir / filename
    if not filepath.exists():
        print(f"{filename:<40} FILE NOT FOUND")
        continue

    try:
        result = subprocess.run(
            [str(player_id), str(filepath)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse output - look for the filename line
        for line in result.stdout.split('\n'):
            if filename in line:
                # Extract player name (after filename, before newline)
                parts = line.split()
                if len(parts) >= 2:
                    player = parts[-1]  # Last part is usually the player name
                    print(f"{filename:<40} {player}")
                    break
        else:
            print(f"{filename:<40} UNIDENTIFIED")

    except Exception as e:
        print(f"{filename:<40} ERROR: {e}")

print("-" * 70)
