#!/usr/bin/env python3
"""Regenerate the "Complete build inventory" section of docs/SF2.md.

Scans the built native SF2 files under out/<player>/, groups them into songs
(stripping the `_partNN` suffix), counts how many parts each song is split into,
and writes a markdown table per player between the GENERATED markers in
docs/SF2.md. Re-run after building more tunes to keep the list current:

    py -3 pyscript/gen_sf2_index.py

The curated fidelity tables above the markers are hand-maintained and untouched.
"""
import os
import re
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "SF2.md")
BEGIN = "<!-- BEGIN GENERATED: build inventory -->"
END = "<!-- END GENERATED -->"

# out/ subdir -> (player, composer, driver). Order = display order.
PLAYERS = [
    ("dmc",          "DMC (Demo Music Creator)",    "Johannes Bjerregaard", "native"),
    ("mon",          "Maniacs of Noise",            "Jeroen Tel",           "native"),
    ("hubbard",      "Rob Hubbard",                 "Rob Hubbard",          "native"),
    ("galway_sf2",   "Martin Galway",               "Martin Galway",        "native"),
    ("romuzak",      "ROMUZAK V6.3",                "Oliver Blasnik",       "native"),
    ("soundmonitor", "Sound Monitor (Musicmaster)", "Fun Fun",              "native"),
    ("sdi_sf2",      "SID Duzz' It (SDI)",          "Gallefoss/Tjelta",     "Driver 11 (Stage A)"),
    ("kimmel_sf2",   "Jeroen Kimmel (Hubbard-derived)", "Jeroen Kimmel",    "Driver 11 (Stage A)"),
    ("deenen_sf2",   "Maniacs of Noise / Deenen",   "Charles Deenen",       "Driver 11 (Stage A)"),
]
# out/ subdir -> SID corpus dir(s) holding the ORIGINAL files, for the
# per-song PSID metadata (title/author/released at header +$16/+$36/+$56)
SID_DIRS = {
    "dmc":          ["SID/JohannesBjerregaard"],
    "mon":          ["SID/Tel_Jeroen"],
    "hubbard":      ["SID/Hubbard_Rob"],
    "galway_sf2":   ["SID/Galway_Martin"],
    "romuzak":      ["SID/Fun_Fun"],
    "soundmonitor": ["SID/Fun_Fun"],
    "sdi_sf2":      ["SID/Gallefoss_Glenn"],
    "kimmel_sf2":   ["SID/Red_kommel_jeroen"],
    "deenen_sf2":   ["SID/deenen"],
}
# suffixes the builders append to the source SID's stem
SUFFIX = re.compile(r"(_sub\d+|_song\d+|_native)$", re.I)


def _psid_meta(path):
    """(author, released) from the PSID/RSID header, or None."""
    try:
        raw = open(path, "rb").read(0x80)
        if raw[:4] not in (b"PSID", b"RSID"):
            return None
        author = raw[0x36:0x56].split(b"\0")[0].decode("latin-1").strip()
        released = raw[0x56:0x76].split(b"\0")[0].decode("latin-1").strip()
        return author, released
    except OSError:
        return None


def _sid_lookup(subdir):
    """case-insensitive stem -> sid path for the player's corpus dirs."""
    look = {}
    for d in SID_DIRS.get(subdir, []):
        for p in glob.glob(os.path.join(ROOT, d, "*.sid")):
            look[os.path.splitext(os.path.basename(p))[0].lower()] = p
    return look


def song_meta(subdir, key, look):
    """PSID (author, released) for a built song key, or None."""
    for cand in (key, SUFFIX.sub("", key)):
        p = look.get(cand.lower())
        if p:
            return _psid_meta(p)
    return None
# probe / scratch prefixes to ignore
SKIP = re.compile(r"(^_|_ab$|_abg|_abl|_tmp|_probe|verify_probe|dmcfid)", re.I)
PART = re.compile(r"_part\d+$", re.I)


def songs_in(subdir):
    """-> {song_key: part_count} for one out/<subdir>."""
    d = os.path.join(ROOT, "out", subdir)
    songs = {}
    for path in glob.glob(os.path.join(d, "*.sf2")):
        stem = os.path.splitext(os.path.basename(path))[0]
        if SKIP.search(stem):
            continue
        key = PART.sub("", stem)          # strip _partNN
        songs[key] = songs.get(key, 0) + 1
    return songs


def render():
    out = [BEGIN,
           "",
           "## Complete build inventory",
           "",
           "*Auto-generated from the built SF2 files under `out/` by "
           "`pyscript/gen_sf2_index.py` — re-run after building more tunes. "
           "\"Parts\" = the number of SF2 files a song is split into (a long song "
           "exceeds the SF2II table/`$D000` caps and ships as windowed parts; "
           "1 = a single file).*",
           ""]
    grand = 0
    for subdir, player, composer, driver in PLAYERS:
        songs = songs_in(subdir)
        if not songs:
            continue
        total_parts = sum(songs.values())
        grand += len(songs)
        out.append(f"### {player} — {composer}  ·  `{driver}`  ·  "
                   f"{len(songs)} songs / {total_parts} SF2 files")
        out.append("")
        out.append("| Song | Composer | Released | Parts |")
        out.append("|------|----------|----------|------:|")
        look = _sid_lookup(subdir)
        for key in sorted(songs, key=str.lower):
            meta = song_meta(subdir, key, look)
            author, released = meta if meta else ("", "")
            out.append(f"| {key.replace('_', ' ')} | {author} | {released} "
                       f"| {songs[key]} |")
        out.append("")
    out.insert(4, f"**{grand} songs built** across "
                  f"{len([p for p in PLAYERS if songs_in(p[0])])} native players "
                  f"(each song may span several SF2 parts).")
    out.insert(5, "")
    out.append(END)
    return "\n".join(out)


def main():
    block = render()
    if os.path.exists(DOC):
        text = open(DOC, encoding="utf-8").read()
        if BEGIN in text and END in text:
            pre = text[:text.index(BEGIN)]
            post = text[text.index(END) + len(END):]
            text = pre + block + post
        else:                              # append before the trailing footer note
            text = text.rstrip() + "\n\n---\n\n" + block + "\n"
        open(DOC, "w", encoding="utf-8", newline="\n").write(text)
        print(f"Updated {DOC}")
    else:
        print(f"{DOC} not found")
    # also echo a summary
    for subdir, player, *_ in PLAYERS:
        s = songs_in(subdir)
        if s:
            print(f"  {player:26} {len(s):4d} songs / {sum(s.values()):4d} files")


if __name__ == "__main__":
    main()
