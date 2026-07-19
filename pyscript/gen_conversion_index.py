#!/usr/bin/env python3
"""Generate docs/SID_TO_SF2_CONVERSIONS.md — a master list of every SID song that
has actually been converted to an SF2 file on disk, across BOTH known locations:

  * out/<player>/    — the native-driver build pipeline (9 known player subdirs)
  * SF2/ (+subdirs)  — the older/separate conversion set (root + Fun_Fun,
                        Galway_Martin, Hubbard_Rob, Tel_Jeroen, Laxity)

For each song it resolves: Name, Original Player, Subtunes, SF2 Driver, Files
(part count), Composer, Released. The "SF2 Driver" column is read directly from
the SF2 file's own descriptor block (Block 1) — never guessed from a directory
name. The "Original Player"/Subtunes/Composer/Released fields come from the
matching source .sid file's PSID/RSID header (and, for the SF2/ set only,
tools/player-id.exe — the out/ pipeline's player is already known per subdir).

Writes between <!-- BEGIN GENERATED: conversion index --> / <!-- END GENERATED -->
markers in docs/SID_TO_SF2_CONVERSIONS.md, so a short hand-written intro can live
above the markers and the generated block can be safely re-run:

    py -3 pyscript/gen_conversion_index.py

Mirrors the conventions of pyscript/gen_sf2_index.py (which stays untouched —
that script covers native-build fidelity only; this one is the broader
"everything that has been converted" index). See CLAUDE.md's
"After building native SF2s" note.
"""
import os
import re
import glob
import struct
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "SID_TO_SF2_CONVERSIONS.md")
PLAYER_ID_EXE = os.path.join(ROOT, "tools", "player-id.exe")
BEGIN = "<!-- BEGIN GENERATED: conversion index -->"
END = "<!-- END GENERATED -->"

# ---------------------------------------------------------------------------
# out/<subdir> -> (player, composer, driver label). Same mapping as
# gen_sf2_index.py's PLAYERS (kept in sync manually; that script is the
# source of truth for the native-build side and is NOT imported here to keep
# this script standalone/dependency-free).
# ---------------------------------------------------------------------------
OUT_PLAYERS = [
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
OUT_SID_DIRS = {
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

# SF2/ locations: (label, relative dir, non-recursive). Root + the 5 subdirs.
SF2_LOCATIONS = [
    ("SF2/ (root)",         "SF2"),
    ("SF2/Fun_Fun",         "SF2/Fun_Fun"),
    ("SF2/Galway_Martin",   "SF2/Galway_Martin"),
    ("SF2/Hubbard_Rob",     "SF2/Hubbard_Rob"),
    ("SF2/Tel_Jeroen",      "SF2/Tel_Jeroen"),
    ("SF2/Laxity",          "SF2/Laxity"),
]

# probe/scratch prefixes to ignore (same shape as gen_sf2_index.py's SKIP)
SKIP = re.compile(r"(^_|_ab$|_abg|_abl|_tmp|_probe|verify_probe|dmcfid)", re.I)
PART = re.compile(r"_part\d+$", re.I)
SUFFIX = re.compile(r"(_sub\d+|_song\d+|_native)$", re.I)


# ---------------------------------------------------------------------------
# PSID/RSID header parsing
# ---------------------------------------------------------------------------
def _psid_meta(path):
    """(author, released, subtunes) from the PSID/RSID header, or None."""
    try:
        raw = open(path, "rb").read(0x80)
        if raw[:4] not in (b"PSID", b"RSID"):
            return None
        subtunes = struct.unpack(">H", raw[0x0E:0x10])[0]
        author = raw[0x36:0x56].split(b"\0")[0].decode("latin-1").strip()
        released = raw[0x56:0x76].split(b"\0")[0].decode("latin-1").strip()
        return author, released, subtunes
    except (OSError, struct.error):
        return None


# ---------------------------------------------------------------------------
# SF2 descriptor (Block 1) driver-name decode.
#
# The name field is NOT plain ASCII. Empirically (verified against the known
# string "Driver 11.03.00 - The Standard" in sidm2/sf2_header_generator.py):
# uppercase letters/digits/punctuation/space are stored as literal ASCII, but
# LOWERCASE letters are stored as their C64 screen-code value (a=0x01 ..
# z=0x1A) instead of ASCII 0x61-0x7A. Both encodings are seen in the corpus
# (older SF2/Laxity/*.sf2 files use plain ASCII throughout; out/ native
# builds and Driver-11 builds use the screen-code-lowercase form) -- this
# decoder handles both since printable ASCII passes through unchanged.
# ---------------------------------------------------------------------------
def _decode_descriptor_name(raw):
    out = []
    for b in raw:
        if b == 0:
            break
        elif 1 <= b <= 26:
            out.append(chr(0x60 + b))          # screen-code lowercase a-z
        elif 0x20 <= b <= 0x7E:
            out.append(chr(b))                  # literal ASCII
        else:
            out.append(f"[{b:02x}]")             # genuinely unknown byte
    return "".join(out).strip()


def sf2_driver_name(path):
    """Read the driver name straight out of the SF2's descriptor block (Block 1)."""
    try:
        data = open(path, "rb").read()
    except OSError:
        return None
    if len(data) < 4 or struct.unpack("<H", data[2:4])[0] != 0x1337:
        return None
    offset = 4
    while offset + 2 <= len(data):
        block_id = data[offset]
        block_size = data[offset + 1]
        if block_id == 0xFF:
            break
        if offset + 2 + block_size > len(data):
            break
        if block_id == 0x01:                    # DESCRIPTOR block
            block = data[offset + 2:offset + 2 + block_size]
            if len(block) < 4:
                return None
            return _decode_descriptor_name(block[3:]) or None
        offset += 2 + block_size
    return None


# ---------------------------------------------------------------------------
# Grouping helpers (shared shape with gen_sf2_index.py)
# ---------------------------------------------------------------------------
def songs_in(dirpath, recursive=False):
    """-> {song_key: [file paths]} for one directory of .sf2 files."""
    pattern = os.path.join(dirpath, "**", "*.sf2") if recursive else os.path.join(dirpath, "*.sf2")
    songs = {}
    for path in glob.glob(pattern, recursive=recursive):
        stem = os.path.splitext(os.path.basename(path))[0]
        if SKIP.search(stem):
            continue
        key = PART.sub("", stem)
        songs.setdefault(key, []).append(path)
    for k in songs:
        songs[k].sort()
    return songs


def _sid_lookup(subdir_list):
    """case-insensitive stem -> sid path, for a list of corpus dirs."""
    look = {}
    for d in subdir_list:
        for p in glob.glob(os.path.join(ROOT, d, "*.sid")):
            look[os.path.splitext(os.path.basename(p))[0].lower()] = p
    return look


def song_psid(key, look):
    for cand in (key, SUFFIX.sub("", key)):
        p = look.get(cand.lower())
        if p:
            return _psid_meta(p)
    return None


# ---------------------------------------------------------------------------
# Per-group SF2 Driver resolution.
#
# A song group can legitimately mix an OLDER un-suffixed base file (predating
# part-splitting) with a NEWER, internally-consistent set of `_partNN` files
# from a rebuild -- e.g. `out/dmc/Rockbuster.sf2` (2026-07-08, driver
# "Laxity") alongside `Rockbuster_part01..16.sf2` (2026-07-11, driver
# "Romuzak"). Reading only `parts[0]` (alphabetically first -- and `.` sorts
# before `_`) silently picked the stale leftover and mis-reported both the
# driver and the file count for the whole group.
#
# This resolves EVERY file's driver name and, if they disagree, first tries
# the "one older un-suffixed base file vs. a consistent newer _partNN set"
# shape; only if that shape doesn't hold does it fall back to showing the
# raw per-driver breakdown so nothing is hidden.
# ---------------------------------------------------------------------------
def resolve_group_driver(parts):
    """-> (driver_label, effective_file_count, note) for one song's file list.

    driver_label is either a single driver name, or (fallback) a
    "Driver (n), Driver2 (m)" breakdown string if no clean resolution
    applies. note is an inline "(N stale legacy build(s) excluded)" suffix,
    or "" if nothing was excluded.
    """
    drivers = {p: (sf2_driver_name(p) or "(unknown)") for p in parts}
    distinct = set(drivers.values())
    if len(distinct) <= 1:
        return next(iter(distinct), "(unknown)"), len(parts), ""

    # Split into "part" files (stem ends in _partNN) vs "base" files (don't).
    base_files = [p for p in parts
                  if not PART.search(os.path.splitext(os.path.basename(p))[0])]
    part_files = [p for p in parts if p not in base_files]

    if base_files and part_files:
        part_drivers = {drivers[p] for p in part_files}
        if len(part_drivers) == 1:
            base_mtimes = [os.path.getmtime(p) for p in base_files]
            part_mtimes = [os.path.getmtime(p) for p in part_files]
            # Every base file strictly older than every part file: treat the
            # base file(s) as a superseded leftover build. Don't delete
            # anything on disk -- just exclude from this group's count/driver
            # and say so inline.
            if max(base_mtimes) < min(part_mtimes):
                driver = next(iter(part_drivers))
                note = (f" ({len(base_files)} stale legacy "
                        f"build{'s' if len(base_files) != 1 else ''} excluded)")
                return driver, len(part_files), note

    # No clean "stale leftover" shape -- don't guess, show the breakdown.
    counts = {}
    for d in drivers.values():
        counts[d] = counts.get(d, 0) + 1
    breakdown = ", ".join(f"{d} ({n})" for d, n in
                          sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))
    return breakdown, len(parts), ""


# ---------------------------------------------------------------------------
# Whole-repo SID/ index, for the SF2/ side (source may live anywhere under SID/)
# ---------------------------------------------------------------------------
def build_global_sid_index():
    idx = {}
    for p in glob.glob(os.path.join(ROOT, "SID", "**", "*.sid"), recursive=True):
        stem = os.path.splitext(os.path.basename(p))[0].lower()
        idx.setdefault(stem, []).append(p)
    return idx


def resolve_source(key, idx):
    """-> (sid_path or None, reason) trying key then the suffix-stripped key.
    reason is one of: 'ok', 'zero', 'multiple'."""
    for cand in (key, SUFFIX.sub("", key)):
        matches = idx.get(cand.lower())
        if matches:
            if len(matches) == 1:
                return matches[0], "ok"
            return None, "multiple"
    return None, "zero"


_PLAYER_ID_CACHE = {}


def player_id(sid_path):
    """Run tools/player-id.exe on a resolved source .sid, cached by path."""
    if sid_path in _PLAYER_ID_CACHE:
        return _PLAYER_ID_CACHE[sid_path]
    result = None
    if os.path.exists(PLAYER_ID_EXE):
        try:
            proc = subprocess.run(
                [PLAYER_ID_EXE, sid_path],
                capture_output=True, text=True, timeout=15,
            )
            # player-id.exe echoes the path back (forward slashes, may be the
            # full path we passed) followed by whitespace and the player id,
            # e.g. "C:/.../SID/Beast.sid        Laxity_NewPlayer_V21" -- match
            # on the basename appearing anywhere in the line, not a prefix.
            base = os.path.basename(sid_path)
            for line in proc.stdout.splitlines():
                stripped = line.strip()
                if base in stripped and stripped != base:
                    result = stripped.split()[-1]
                    break
        except (OSError, subprocess.SubprocessError):
            result = None
    _PLAYER_ID_CACHE[sid_path] = result
    return result


# ---------------------------------------------------------------------------
# Render: out/ pipeline section
# ---------------------------------------------------------------------------
def render_out_section():
    lines = ["## Native-build pipeline — `out/<player>/`", ""]
    lines.append("*The 9 known native/Driver-11-Stage-A player subdirectories under `out/` "
                 "(same mapping as `pyscript/gen_sf2_index.py`). \"Original Player\" is the "
                 "already-known label for these dirs (not re-detected); \"SF2 Driver\" is read "
                 "live from each SF2's descriptor block.*")
    lines.append("")
    grand_songs = 0
    grand_files = 0
    composer_stats = {}  # (composer, original_player) -> song_count
    for subdir, player, composer, driver_label in OUT_PLAYERS:
        songs = songs_in(os.path.join(ROOT, "out", subdir))
        if not songs:
            continue
        look = _sid_lookup(OUT_SID_DIRS.get(subdir, []))
        rows = []
        total_files = 0
        for key in sorted(songs, key=str.lower):
            parts = songs[key]
            meta = song_psid(key, look)
            author, released, subtunes = meta if meta else ("", "", None)
            drv, file_count, note = resolve_group_driver(parts)
            sub_s = str(subtunes) if subtunes is not None else "?"
            total_files += file_count
            rows.append(f"| {key.replace('_', ' ')} | {player} | {sub_s} | {drv}{note} | "
                        f"{file_count} | {author} | {released} |")
            ck = (author or "(unknown)", player)
            composer_stats[ck] = composer_stats.get(ck, 0) + 1
        grand_songs += len(songs)
        grand_files += total_files
        lines.append(f"### {player} — {composer}  ·  {len(songs)} songs / {total_files} SF2 files")
        lines.append("")
        lines.append("| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released |")
        lines.append("|------|------------------|---------:|------------|------:|----------|----------|")
        lines.extend(rows)
        lines.append("")
    return lines, grand_songs, grand_files, composer_stats


# ---------------------------------------------------------------------------
# Render: SF2/ section
# ---------------------------------------------------------------------------
def render_sf2_section(sid_idx):
    lines = ["## Separate conversion set — `SF2/`", ""]
    lines.append("*Loose conversions under `SF2/` (root + subdirs), predating/parallel to the "
                 "`out/` native pipeline — NOT necessarily the same build as an `out/` song with "
                 "the same name. \"Original Player\" is detected fresh per song via "
                 "`tools/player-id.exe` against the matched source `.sid` (searched across the "
                 "whole `SID/` tree); \"unresolved\" = zero or multiple candidate source files "
                 "were found and the match was not guessed.*")
    lines.append("")
    grand_songs = 0
    grand_files = 0
    unresolved = []
    composer_stats = {}  # (composer, original_player) -> song_count
    for label, reldir in SF2_LOCATIONS:
        songs = songs_in(os.path.join(ROOT, reldir))
        if not songs:
            continue
        rows = []
        total_files = 0
        for key in sorted(songs, key=str.lower):
            parts = songs[key]
            drv, file_count, note = resolve_group_driver(parts)
            total_files += file_count
            sid_path, reason = resolve_source(key, sid_idx)
            if sid_path:
                meta = _psid_meta(sid_path)
                author, released, subtunes = meta if meta else ("", "", None)
                orig_player = player_id(sid_path) or "(undetected)"
                sub_s = str(subtunes) if subtunes is not None else "?"
                rel_sid = os.path.relpath(sid_path, ROOT).replace("\\", "/")
            else:
                orig_player, sub_s, author, released = "unresolved", "?", "", ""
                rel_sid = f"unresolved ({reason} matches)"
                unresolved.append((f"{label}/{key}", reason))
            rows.append(f"| {key.replace('_', ' ')} | {orig_player} | {sub_s} | {drv}{note} | "
                        f"{file_count} | {author} | {released} | `{rel_sid}` |")
            composer_key = author or ("(unresolved)" if not sid_path else "(unknown)")
            ck = (composer_key, orig_player)
            composer_stats[ck] = composer_stats.get(ck, 0) + 1
        grand_songs += len(songs)
        grand_files += total_files
        lines.append(f"### {label}  ·  {len(songs)} songs / {total_files} SF2 files")
        lines.append("")
        lines.append("| Song | Original Player | Subtunes | SF2 Driver | Files | Composer | Released | Source SID |")
        lines.append("|------|------------------|---------:|------------|------:|----------|----------|------------|")
        lines.extend(rows)
        lines.append("")
    return lines, grand_songs, grand_files, unresolved, composer_stats


def _merge_composer_stats(*stat_dicts):
    merged = {}
    for d in stat_dicts:
        for key, songs in d.items():
            merged[key] = merged.get(key, 0) + songs
    return merged


def render_composer_section(composer_stats):
    lines = ["## Songs converted per composer", ""]
    lines.append("*Every (composer, original player) pair appearing in either scanned location, "
                "aggregated by the PSID header's author field (\"Composer\" column above) — sorted "
                "by song count, descending. A composer who worked across more than one player/engine "
                "gets one row per player. `(unknown)` = a resolved source `.sid` with a blank author "
                "field; `(unresolved)` = the `SF2/`-side songs with no unambiguous source match "
                "(see the unresolved note above).*")
    lines.append("")
    lines.append("| Composer | Original Player | Songs |")
    lines.append("|----------|------------------|------:|")
    for (composer, orig_player), songs in sorted(
        composer_stats.items(), key=lambda kv: (-kv[1], kv[0][0].lower(), kv[0][1].lower())
    ):
        lines.append(f"| {composer} | {orig_player} | {songs} |")
    lines.append("")
    return lines


def render():
    out_lines, out_songs, out_files, out_composer_stats = render_out_section()
    sid_idx = build_global_sid_index()
    sf2_lines, sf2_songs, sf2_files, unresolved, sf2_composer_stats = render_sf2_section(sid_idx)
    composer_stats = _merge_composer_stats(out_composer_stats, sf2_composer_stats)

    header = [
        BEGIN,
        "",
        "## Summary",
        "",
        f"**{out_songs + sf2_songs} songs / {out_files + sf2_files} SF2 files** converted on disk, "
        f"across two independently-scanned locations (counts are NOT deduplicated between them — "
        f"the same song may legitimately appear in both):",
        "",
        f"- `out/<player>/` native-build pipeline: **{out_songs} songs / {out_files} files** "
        f"across {len([p for p in OUT_PLAYERS if songs_in(os.path.join(ROOT, 'out', p[0]))])} player dirs",
        f"- `SF2/` (root + subdirs): **{sf2_songs} songs / {sf2_files} files**"
        + (f" — **{len(unresolved)} unresolved source match(es)**: "
           + ", ".join(f"{name} ({reason})" for name, reason in unresolved) if unresolved else ""),
        "",
        "*`output/` (repo root) was scanned and excluded: it holds only 3 stray `.sf2` files under "
        "test-report scratch dirs (`output/cockpit_test/`), duplicating names already covered by "
        "`SF2/` and not a real conversion location.*",
        "",
        "---",
        "",
    ]
    header += render_composer_section(composer_stats) + ["---", ""]
    body = out_lines + ["---", ""] + sf2_lines
    return "\n".join(header + body + [END])


def main():
    block = render()
    if os.path.exists(DOC):
        text = open(DOC, encoding="utf-8").read()
        if BEGIN in text and END in text:
            pre = text[:text.index(BEGIN)]
            post = text[text.index(END) + len(END):]
            text = pre + block + post
        else:
            text = text.rstrip() + "\n\n---\n\n" + block + "\n"
    else:
        text = ("# SID to SF2 Conversion Index\n\n"
                "A script-generated master list of every SID song that has actually been "
                "converted to an SF2 file on disk. Re-run after building/converting more tunes:\n\n"
                "    py -3 pyscript/gen_conversion_index.py\n\n"
                "See also [`docs/SF2.md`](SF2.md) for the native-build fidelity index (a "
                "narrower, hand-curated companion doc covering the same `out/` pipeline).\n\n"
                "---\n\n" + block + "\n")
    open(DOC, "w", encoding="utf-8", newline="\n").write(text)
    print(f"Updated {DOC}")


if __name__ == "__main__":
    main()
