#!/usr/bin/env python3
"""The single source of truth for `out/<subdir>` -> player / composer / corpus.

`gen_sf2_index.py` and `gen_conversion_index.py` both need this mapping, and
until now each carried its own copy -- 13 entries and a 13-entry corpus dict,
duplicated verbatim, with a comment saying they were "kept in sync manually".
They were not. Matt Gray, Future Composer and HardTrack all shipped builds that
appeared in neither document; `grep -ci matt` returned 0 from both while
`out/mattgray_native/` held 25 SF2 files.

Deduplicating is only half the fix, because the list is still hand-written: a
new builder writes `out/<newdir>/` and nothing notices. So every directory under
`out/` that contains SF2 files must be classified here as either a PLAYER or an
IGNORED entry with a stated reason, and `unclassified()` reports any that is
neither. `test_player_index.py` fails on a non-empty result, which is what turns
"someone must remember to edit two lists" into "the suite says so".

That guard found 273 more files the moment it was written -- see IGNORED.
"""
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# out/ subdir -> (player, composer, driver label). Order = display order.
PLAYERS = [
    ("dmc",          "DMC (Demo Music Creator)",    "Johannes Bjerregaard", "native"),
    ("mon",          "Maniacs of Noise",            "Jeroen Tel",           "native"),
    ("hubbard",      "Rob Hubbard",                 "Rob Hubbard",          "native"),
    ("galway_sf2",   "Martin Galway",               "Martin Galway",        "native"),
    ("romuzak",      "ROMUZAK V6.3",                "Oliver Blasnik",       "native"),
    ("soundmonitor", "Sound Monitor (Musicmaster)", "Fun Fun",              "native"),
    ("sdi_sf2",      "SID Duzz' It (SDI)",          "Gallefoss/Tjelta",     "Driver 11 (Stage A)"),
    ("sdi",          "SID Duzz' It (SDI)",          "Gallefoss/Tjelta",     "native (Stage B)"),
    ("kimmel_sf2",   "Jeroen Kimmel (Hubbard-derived)", "Jeroen Kimmel",    "Driver 11 (Stage A)"),
    ("deenen_sf2",   "Maniacs of Noise / Deenen",   "Charles Deenen",       "Driver 11 (Stage A)"),
    ("blackbird",    "Blackbird / lft",             "lft",                  "native"),
    ("hardtrack",    "HardTrack Composer",          "Longhair/Brush",       "Driver 11 (Stage A)"),
    ("hardtrack_native", "HardTrack Composer",      "Longhair/Brush",       "native (Stage B)"),
    ("mattgray_native", "Matt Gray",                "Matt Gray",            "native (Stage B)"),
    ("fc",           "Future Composer",             "Michael Troelsen",     "native (Stage B)"),
]

# out/ subdir -> SID corpus dir(s) holding the ORIGINAL files, for the per-song
# PSID metadata (title/author/released at header +$16/+$36/+$56).
SID_DIRS = {
    "dmc":          ["SID/JohannesBjerregaard"],
    "mon":          ["SID/Tel_Jeroen"],
    "hubbard":      ["SID/Hubbard_Rob"],
    "galway_sf2":   ["SID/Galway_Martin"],
    "romuzak":      ["SID/Fun_Fun"],
    "soundmonitor": ["SID/Fun_Fun"],
    "sdi_sf2":      ["SID/Gallefoss_Glenn"],
    "sdi":          ["SID/Gallefoss_Glenn"],
    "kimmel_sf2":   ["SID/Red_kommel_jeroen"],
    "deenen_sf2":   ["SID/deenen"],
    "blackbird":    ["SID/LFT"],
    "hardtrack":    ["SID/Shogoon"],
    "hardtrack_native": ["SID/Shogoon"],
    "mattgray_native": ["SID/Gray_Matt"],
    "fc":           ["SID/Fun_Fun"],
}

# Directories that hold SF2 files but are deliberately NOT indexed. A reason is
# required: the point of this table is that excluding a build is a decision
# somebody made on the record, not an omission nobody noticed.
IGNORED = {
    "sm_sf2": "superseded Stage A output; no builder writes it any more, and "
              "the shipped Sound Monitor build is out/soundmonitor/",
    "fc_sf2": "superseded Stage A output; no builder writes it any more, and "
              "the shipped Future Composer build is out/fc/ (native Stage B)",
    "_a3_baseline": "A/B scratch -- *_BEFORE.sf2 captures kept for comparison",
    "_a3_after": "A/B scratch -- the AFTER half of the same comparison",
    "_dump": "scratch dumps from ad-hoc investigation, not a build",
    "_truncation_sweep": "scratch from the pattern-truncation sweep, not a build",
    "fc_native": "empty; superseded by out/fc/",
    "mattgray_playtest": "empty; SF2II play-test scratch",
}


def out_dirs_with_sf2(root=ROOT):
    """Every directory under out/ that actually contains SF2 files."""
    out = os.path.join(root, "out")
    if not os.path.isdir(out):
        return []
    return sorted(
        d for d in os.listdir(out)
        if os.path.isdir(os.path.join(out, d))
        and glob.glob(os.path.join(out, d, "*.sf2"))
    )


def unclassified(root=ROOT):
    """[(subdir, sf2_count)] present on disk but in neither PLAYERS nor IGNORED.

    Non-empty means a build exists that no document will ever mention. Classify
    it -- in PLAYERS if it should be indexed, in IGNORED with a reason if not.
    """
    known = {p[0] for p in PLAYERS} | set(IGNORED)
    return [(d, len(glob.glob(os.path.join(root, "out", d, "*.sf2"))))
            for d in out_dirs_with_sf2(root) if d not in known]


def warn_if_unclassified(root=ROOT):
    """Print the guard's finding. Called by both generators so a stale mapping
    is visible at the moment the docs are regenerated, not only under pytest."""
    missing = unclassified(root)
    for d, n in missing:
        print(f"  WARNING: out/{d}/ holds {n} SF2 file(s) and is in neither "
              f"PLAYERS nor IGNORED -- it appears in NO document. "
              f"Classify it in pyscript/player_index.py.")
    return missing
