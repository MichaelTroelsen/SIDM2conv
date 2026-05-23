# The SIDM2 Story

*How an "experimental converter" became a byte-accurate bridge between two C64 music tools that don't speak each other's language.*

**Current version:** v3.5.33 (2026-05-23) — 1032 tests, 286-file corpus, **98.6% C2 byte-identical**
**Latest chapter:** [v3.5.33 — gate extended (wave-copy NOP + 200-frame window)](#v3533--gate-extended-wave-copy-nop--200-frame-window-2026-05-23)

---

## TL;DR

SIDM2 converts **Commodore 64 SID music files** (the binary blob format that ships every C64 tune ever written) into **SID Factory II project files** (`.sf2`, the editable format used by the modern SID composition tool).

This is harder than it sounds because:

1. SID files are **compiled 6502 code + opaque data tables**. You hand them an init address and a play address, you call play 50 times a second, and SID registers light up. There is no "the notes" — only what the binary writes to `$D400-$D418` each frame.
2. SID Factory II's project format is **a snapshot of an editor session**, with player code, orderlists, sequences, instruments, wave/pulse/filter programs, hardware preferences, and 9 structured header blocks.
3. There is **no standard SID→SF2 path**. SF2II's author (Chordian) only officially supports SF2-saved files. Round-tripping a real SID through SF2II is unsupported territory.

The project's working definition of "correct" is four criteria, abbreviated **C1, C2, C3, C4**:

- **C1 — Editor loads the SF2**. F10 in SF2II opens the file without crashing.
- **C2 — Audio matches the original**. The SF2's emulated playback produces the same SID register writes as the original SID at every frame (cycle-accurate trace, ignoring cycle column but matching frame/register/value).
- **C3 — Edits propagate**. Changing notes/instruments/wave/pulse/filter in the editor actually affects what the file plays.
- **C4 — Round-trip preserves audio and metadata**. SID → SF2 → SID gives back the same audio (and song title / author / copyright).

Today the project sits at:

| Criterion | Where it lives |
|-----------|---------------|
| **C2 byte-identical** | **282/286 (98.6%)** of the Laxity corpus, plus the canonical references (Stinsen, Unboxed, Beast, Angular) at exactly zero divergent register writes over 300 frames. Of the 4 still-failing: 3 convert-fail (Crosswords, Echo_Beat architectural, Magic_Sound) and 1 audio-diverge (Exorcist_preview wrapper-init) |
| **C1 F10-load** | **85%** (`242/286`) after the SF2II issue #211 workaround landed in v3.5.18 |
| **C4 audio round-trip** | **283/283 (100% of converted)** |
| **C4 metadata round-trip** | **283/283 (100% of converted)** |
| **C3 strict (all five tabs propagate)** | **1 file** (Stinsen). C3 is fundamentally a per-variant reverse-engineering problem and the limiting factor on full editor support. |

The rest of this document is the story of how the project got here. It is roughly chronological — partly because each release built on the previous one, partly because every "obvious next fix" required tooling that didn't exist before the fix before it.

---

## Setting the stage: what we're converting from and to

### The SID file (.sid)

A PSID/RSID file is a tiny header (typically 124 bytes) followed by a chunk of C64 machine code. The header declares three things that matter:

```
load_address   Where the C64 should load the bytes into memory
init_address   The 6502 routine to call once to set up the song
play_address   The 6502 routine to call every PAL vbl (~50 Hz)
```

The whole song lives inside that machine code. Each call to `play_addr` runs whatever 6502 instructions the composer wrote, and those instructions write to the SID chip's 25 registers (`$D400-$D418`). That's the song — there's no MIDI-equivalent abstraction.

Most C64 SID files use one of about a dozen different **player kernels** — code frameworks that authors reuse. The ones that matter for SIDM2 are:

- **Laxity NewPlayer v21 (NP21)** — Thomas E. "Laxity" Petersen's modern player. Most contemporary Laxity-authored tunes use it. Has identifiable scratch regions (`$1A1C/$1A1F` for `ch_seq_ptr`, `$1989/$19A3/$19BD` for filter byte streams, etc.).
- **Driver 11 / 13 / 14 / 15 / 16** — SID Factory II's own player drivers. SF2-authored tunes embed these. Easy to convert (they're already SF2-shaped — just copy).
- **NP20** — Predecessor to NP21. Different register-write conventions.
- **Vibrants V20** — A family of 1987-1990 pre-NP21 players with sub-cluster variations (Wizax-A, Wizax-B, Zetrex/Yield-Point, 2000 A.D., Flexible Arts, …). Each cluster has its own scratch layout.
- **Galway / Hubbard** — Custom players from Martin Galway and Rob Hubbard. Bespoke.

The PSID header doesn't tell you which player was used. You guess from the author/copyright strings, the binary signature, or you just call it `Unknown` and pick a safe default.

### The SF2 file (.sf2)

A SID Factory II project file is a C64 PRG (so it loads at a declared address and runs) containing:

- A magic `0x1337` at the file start (otherwise SF2II refuses to load it)
- **9 header blocks** describing the driver, the music data layout, table addresses, the auxiliary chain, hardware preferences, play markers, instrument names, and so on
- An embedded **SF2 driver** (player code)
- **Music data** in SF2's editable format: orderlists, sequences (notes/durations/instruments/commands packed in a tight byte stream), and per-table programs (instruments, wave, pulse, filter)
- An **auxiliary chain** of typed blocks (song titles, hardware prefs, table-text overlays, …)

The SF2 driver runs at well-known addresses inside the file (`$0F90` INIT, `$0F94` PLAY in our layout). When SF2II opens the file, the editor renders the byte streams as a tracker view (per-voice columns of notes/durations) plus tabbed editors for instruments (F2), wave programs (F3), pulse programs (F4), and filter programs (F5). Each cell in those views is a byte in the file. Edit a cell → the byte changes → next time you play, the driver reads the new byte → different sound.

That is the architectural mismatch we're bridging: a **pre-compiled 6502 program** (the SID) versus a **structured editor-readable data model** (the SF2).

### The two routes that exist

A SID file is *opaque code* and an SF2 file is *visible data*. There are exactly two ways to bridge them:

1. **Extract the data model from the binary.** Statically (or dynamically) analyze the 6502 code, recover where notes/instruments/wave programs live, and re-emit them in SF2's format. This gives a fully editable result. Cost: every player kernel needs its own extractor, and most of them are undocumented.

2. **Embed the original binary verbatim and call it from SF2II's player hooks.** Put the SID code at its native load address inside the SF2, add a thin wrapper at `$0F90`/`$0F94` that JSRs into the original `init`/`play`. SF2II runs the SF2 driver each frame, the driver calls the embedded SID player, the SID player drives the SID chip exactly as it would natively. Result is audio-identical but the editor view is empty (the data isn't where SF2II's editor looks for it).

SIDM2 does **both, layered**. For Laxity NP21 files (the supported case) it embeds the native NP21 binary AND emits a separate SF2 edit-area for the editor to render, AND a runtime "translator" that copies edits from the SF2 edit area into the embedded player's scratch RAM on every PLAY tick. That last piece — the translator — is what makes criterion 3 (edits affect playback) even possible.

---

## The architecture in one diagram

```
SID file (PSID header + 6502 binary at $1000)
  │
  ├── load_address  $1000
  ├── init_address  $1000
  ├── play_address  $1003 or $1006 depending on variant
  └── c64 binary    ─────────────────────────────┐
                                                  │
SF2 file (PRG load=$0D7E)                         │
  ├── $0D7E         SF2 magic 0x1337               │
  ├── $0D80-$0F8F   9 header blocks                │
  ├── $0F90         INIT handler  ── JSR init_addr ─┤
  ├── $0F94         PLAY handler  ── JMP $0F9E      │
  ├── $0F9E-$0FFA   multipat translator             │  the SID binary
  ├── $1000-$XXXX   ← embedded SID binary (verbatim,
  │                   with 4 surgical patches:
  │                     - $1003 trampoline to translator
  │                     - $1006 #211 stamp (if gap)
  │                     - ch_seq_ptr → shadow buffer
  │                     - wave-data scratches refreshed each tick)
  ├── …             SF2 edit area: orderlists, sequences,
  │                   instruments, wave/pulse/filter programs,
  │                   shadow buffer (3 × 256B per-voice byte streams),
  │                   copy routines (wave-copy, instr-copy, …)
  └── META trailer  title/author/copyright (round-trip)
```

The translator at `$0F9E` is the heart of the editor-affects-playback machine. Every PLAY tick:

1. It walks the SF2 edit area's sequence patterns
2. For each voice, copies the byte stream into the voice's shadow buffer
3. JSRs the wave-copy routine (which sweeps the SF2 wave editor table into the embedded NP21 player's wave-data scratches)
4. JSRs instr-copy / pulse-copy / filter-copy (variant-specific)
5. JSRs the original SID play address

The embedded NP21 player then reads from the shadow buffer (because `ch_seq_ptr` was patched to point there) and the wave-data scratches (because copy-routine just refreshed them). What SF2II's editor displays IS what the player reads, on every tick.

That's the design. The interesting part — the part this document exists to tell — is how it got that way.

---

## Era I: "Does this even work?" (v0.1 → v1.4, ~2025-Q4)

The first nine months were prototypes: assemble a Python pipeline that reads a SID, extracts SOMETHING that looks like music data, and writes SOMETHING that SF2II will at least open. v0.1 through v0.6 are archived because they were mostly dead ends. v1.0 produced a file that loaded but played silence. v1.4 produced a file with valid orderlists pointing at empty sequences. The accuracy metric ("does the SF2 trace match the SID trace") was effectively zero.

This era's main contribution was the validation system — a way to MEASURE whether two register-write streams agree. That measurement turned out to be the difference between a wishful project and a verifiable one.

## Era II: Editor coverage (v2.0 → v2.10, ~2025-12)

The v2.x line filled out infrastructure: SF2 Viewer GUI, SID Inventory (a catalog of 658+ SID files we test against), batch testing harness, the Conversion Cockpit GUI. Coverage of SF2-exported files (the easy case — those are already SF2-shaped, just copy them through) reached 100%. Coverage of native Laxity files was still flatlined at <1%.

The unblocking insight in v2.10 was simple and embarrassing: for SF2-authored files, **just find the original .sf2 file Laxity exported from and copy it directly**. Don't try to derive it from the .sid. v3.0.0 turned that insight into automatic reference file detection — search a `learnings/` folder, fuzzy-match filenames, copy through. Result: SF2-exported files at byte-identical accuracy. Useful, but it didn't help with the hundreds of native Laxity files for which no reference SF2 exists.

## Era III: The Laxity driver fork (v3.0.1 → v3.1.5)

The first real native-Laxity success.

The plan: don't try to translate Laxity NP21 to SF2 format. **Embed the original NP21 binary verbatim**, add a minimal SF2 wrapper, and let the SID Factory II editor see an empty data view while audio plays through the native player. v3.0.1 got this to 99.98% accuracy on Stinsen — the first real four-nines result.

v3.1.5 generalized it to "any" Laxity NP21 song, not just Stinsen. The pattern crystalized: **embed the binary; SF2 is a wrapper, not a translation.**

What didn't work yet was the editor view. F2/F3/F4/F5 tabs all displayed garbage because the SF2 Block 3 column addresses pointed at NP21's own scratch regions, which the editor reads as if they were SF2-format tables. The note view (F1) was almost as bad. Anyone who opened one of these files in SF2II got "Hubbardesque tracker view of static" — playable, illegible.

## Era IV: Editable views (v3.1.6 → v3.3.0, ~2026-Q1)

This is where the project stopped being a curiosity and started being a tool.

### v3.1.6: A *valid* SF2 (2026-03-29)

Add the `0x1337` magic. Emit the 5 required header blocks (228 bytes at `$0D7E-$0E62`). Place handlers at `$0F00/$0F04/$0F08`. Now SF2II actually recognizes the file as a project. The byte-identical Stinsen + Unboxed accuracy doesn't change (zig64 trace still 100%), but PyAutoGUI automation can finally load both files in the GUI without an immediate dialog box. Editor view is still empty.

### v3.1.7-3.2.1: Real Block 3 addresses, real metadata

A sequence of small corrections, each born of a specific bug:

- v3.1.7: Build a real SF2 edit area (orderlists + sequences in SF2 format) **after** the embedded NP21 binary. Block 5 now points at real addresses. Editor finally shows voice sequences instead of empty rows.
- v3.1.8: `_extract_raw_seq()` stops at `$FF` (NP21's internal loop terminator) instead of `$7F` (the unreachable safety-only end marker). Stinsen voice 0 goes from 101 spurious bytes to 41 correct bytes.
- v3.1.9 → v3.2.2: A pair of corrections to the NP21↔SF2 note mapping. v3.1.9 thought SF2 notes were 1-based and applied `+1`. v3.2.2 read the SF2II source (`datasource_sequence.cpp:197-267`) and the player code (`$10F4-$10FB`) and discovered NP21 byte `$00` means "no new note this tick" (not "C-0"), so the +1 shift was wrong. The fix is the identity mapping plus a clamp on `$70-$7D` (NP21 has slightly wider pitch range than SF2).
- v3.2.0: Filter table address corrected from `$1A1E` (which was actually `ch_seq_ptr_hi`!) to `$1989`. Editing "filter" entries had been corrupting voice pointers. Wave table address corrected from `$1ACB` to `$1942`. Instruments table set to column-major to match NP21 storage.
- v3.2.1: The driver auto-selector now picks Laxity for `SidFactory_II/Laxity` files (Stinsen et al.). Author/title/copyright round-trip implemented through SF2 aux block id=5 instead of the previous "last-string-wins" string-scan.

After v3.2.1, both Stinsen and Unboxed traced 100% **and** had legible editor views. End-to-end success for two files.

### v3.3.0 (2026-04-30): Criterion 3 — edits propagate to playback

The big architectural piece. The two halves:

**Build-time shadow pre-fill.** After the embedded NP21 binary, append a 3-slot × 256-byte **shadow buffer**. Write each voice's extracted NP21 sequence body (terminated with `$FF $00`) into its shadow slot. **Patch `ch_seq_ptr` at `$1A1C/$1A1F` to point at the shadow slots instead of the original NP21 sequence locations.** The embedded player can't tell the difference — bytes look the same — but now we control where it reads from.

**Runtime translator at `$0F0E`** (later moved to `$0F9E` when multi-pattern support landed in v3.4.0). The SF2 PLAY handler does `JMP $0F0E`. Translator code (51 bytes of 6502, grown over later versions) iterates voices, reads SF2-format bytes from the editor's `seq00_addr`, translates them through `sidm2/sf2_to_np21.py` mapping logic, and writes the result into the shadow buffer. By the time the translator JSRs into the embedded NP21 player, the shadow is fresh from whatever the editor currently has.

Edit a cell in F1 → editor writes a byte → translator re-runs → shadow has new byte → next PLAY tick plays the new byte. C3 closed for sequences on Stinsen + Unboxed. The Python emitter feeds both the build-time pre-fill and the runtime translator, so the two halves are byte-for-byte equivalent by construction — a property pinned by 3 new tests in `TestCriterion3EditProof`.

This release was the moment the project crossed from "converter" to "editor bridge."

## Era V: Multi-variant support (v3.4.0 → v3.5.10, ~2026-04 → 2026-05)

The v3.x machinery worked on Stinsen-class layouts. Real-world Laxity SIDs come in variants — Beast, Angular, Cycles, … — each with slightly different scratch addresses for instruments, wave, pulse, filter.

### v3.4.0: Multi-pattern translator

Stinsen has a flat sequence per voice. Beast splits each voice into multiple **patterns** at instrument-prefix boundaries. The v3.3.0 translator emitted one SF2 pattern per voice; that was structurally wrong for multi-pattern songs.

v3.4.0 introduces multi-pattern segmentation (split each voice's flat NP21 stream at instrument prefixes) and an 87-byte multipat translator at `$0F8E` that walks each voice's pattern list and concatenates them into the shadow slot. Block 9 also gets populated properly (4 descriptors instead of a 1-byte placeholder), and the aux chain is reordered to `[3, 2, 1, 4, 5, END]` matching SF2II's bundled reference corpus.

### v3.4.1: The Block 3 NameLen → TextFieldSize bug

A two-week mystery: solo-loading Stinsen in SF2II crashed 53% of the time. Heap-layout-dependent crash inside the editor's table-row rendering, masked under AppVerifier (so we couldn't catch it with a debugger).

The root cause was a one-byte field misinterpretation. Our Block 3 was writing `NameLen`. SF2II's parser was reading that byte as `m_TextFieldSize`. With `m_TextFieldSize > 0`, every driver table became a `ComponentTableRowElementsWithText` whose `Refresh` writes a stray `0xDE`/`0xDF` byte to `AuxilaryDataTableText` lookups. The byte landed wherever heap fragmentation put it. Sometimes innocuous, sometimes not.

Fix: emit `TextFieldSize = 0` instead of `NameLen`. Solo F10-load: **Stinsen 47% → 100%, Unboxed → 100%**. Same fix unblocked Angular and Beast (those had been crashing 100%).

The investigation was its own contribution: `pyscript/sf2_debug_inspect_v2.py`, `disasm_rva.py`, AppVerifier-mode tooling. The residual 11-file crash (later identified as upstream issue #211) survived this fix and waited until v3.5.18.

### v3.5.0 → v3.5.10: Per-variant detector zoo

Each variant got its own detector module, plus 6502 copy routines that emit into the SF2 edit area:

| Variant | F2 (instr) | F3 (wave) | F4 (pulse) | F5 (filter) |
|---------|-----------|-----------|-----------|------------|
| **Stinsen** | column-major AD/SR @ `$1808/$181C` | parallel arrays @ `$190C`/`$18DA` | parallel arrays @ `$1957`/`$193E` | state machine @ `$1989`/`$19A3`/`$19BD` |
| **Beast** | row-major 8B @ `$1B38` | (Stinsen-style) | nibble-packed 4B records @ `$1AC5` (high nibble→PW lo, low nibble→PW hi) | cutoff_hi @ `$1A7D`, res_routing/mode_vol fixed @ `$100A/$1009` |
| **Angular** | row-major 2B @ `$1ADB` | (Stinsen-style) | nibble-packed 4B records @ `$1A3B` | cutoff_hi @ `$1A1F` (yes, the same place ch_seq_ptr_hi normally lives — see v3.5.17) |

The nibble-pack discovery (v3.5.10) was particularly satisfying. Beast and Angular's pulse byte 0 is `(PW_lo_nibble << 4) | PW_hi_nibble` — pre-split before reaching the SID registers, which is why earlier patches with arbitrary `$A5` values produced `$A0` in `pw_lo` and `$05` in `pw_hi`. Once we wrote the routine `_emit_pulse_packed_copy_routine` to encode/decode the nibble pack, F4 edits became visible in zig64 traces.

By the end of Era V we had editor-affects-playback on F1/F2/F3/F4/F5 for Stinsen, F1/F2/F3/F4/F5 (with limitations) for Beast and Angular. Multiple subclasses of NP21 supported.

The same era documented many **negative results**: variants whose RE proved expensive or infeasible. `stage8.5-load-addr-crash.md`, `multipattern-misnomer.md`, `wave-copy-non-idempotency.md`, `dynamic-instr-detector-attempt.md` — each captures a road we walked down, ran into a wall, documented for the next person.

## Era VI: Corpus convergence (v3.5.11 → v3.5.30)

The pivot in this era was from **canonical files** (Stinsen, Unboxed, Beast, Angular) to **the 286-file Laxity corpus**. The question changed from "does Stinsen play right?" to "how much of the corpus does, and what blocks the rest?"

The early Era VI releases established the Vibrants V20 cluster — 14 files spanning 5+ pre-NP21 player variants from 1987-1990. Most got cluster-detector advisories (v3.5.11 through v3.5.14). Wizax-A (v3.5.15) and Zetrex/Yield-Point (v3.5.16) got actual F1 edit-propagation pipelines wired up, because their byte streams happened to be NP21-compatible despite being from different players.

### v3.5.17: The first audio-correctness gate

While pushing Angular to full 4-criterion pass, two project-wide bugs surfaced:

1. **`$1A1C/$1A1F` isn't always `ch_seq_ptr`.** For Angular, that region is state-machine data the player reads via `LDA $1A1F,Y` at `$10F7`. The default patch caused 3 extra `osc3` register writes per active frame (75 over 300 frames). The fix: add `_ptrs_in_range_check` — only patch if the bytes look like valid in-range pointers. If they don't, skip the patch and preserve audio at the cost of F1 edit propagation for that file.
2. **Metadata round-trip was never actually implemented.** Since v3.2.1, `sf2_to_sid.py` scanned for an aux block (id=5, param=1) with title/author/copyright that **`sf2_writer.py` never emitted**. Title/author/copyright had been silently lost on every SID→SF2→SID for every file. Fix: append a `b"META"` magic + three pascal strings past the SF2 content. SF2II ignores the trailer; `sf2_to_sid.py` rfinds and parses it.

Both fixes corpus-wide. The `_ptrs_in_range_check` heuristic in particular set a pattern — *"patch carefully; assume the player uses these bytes for something else until proven otherwise"* — that the v3.5.29 safety gate would later formalize.

### v3.5.18: The C1 cliff and SF2II upstream #211

When v3.5.4 made the wave-copy idempotent for non-Stinsen variants, it unblocked the JMP-indirection trampoline patch — which redirects zig64 trace through the translator. That moved more files through the editor's load codepath, which immediately exposed a pre-existing SF2II crash we'd been blaming on `m_TableColorRules` for months.

The real root cause (v3.5.18): `Editor::DriverUtils::GetSIDWriteInformationFromDriver` at `driver_utils.cpp:419` dereferences `result.begin()->m_CycleOffset` **without checking if the vector is empty**. The function statically sweeps `[$1000, $1900)` for absolute-indexed (`9D` ABX, `99` ABY) writes to `$D400-$D406`. Binaries not loaded at `$1000` leave that window as zero-fill PRG gap → zero writes → empty `result` → AV READ at `0x1`.

Tooling for this fix:
- A symbolized x86 debug build of SF2II via the local `.pdb`
- Discovery of `main.cpp:95`: SF2II auto-loads `argv[1]`, so we could reproduce the crash from the command line without PyAutoGUI hangs (`pyscript/sf2_argv_crash.py`)
- A patched diagnostic build (admin-elevated AppVerifier mode) that let us localize the AV to the exact line

Upstream declined to prioritize the fix (collaborator: "SF2II only officially supports SF2II-saved files"). SF2-side workaround: `_ensure_sid_write_in_scan_window_universal()` in `sf2_writer.py`, called once after all injection paths converge. Every path emits a 2-JMP trampoline at `$1000` (a deterministic anchor for SF2II's sweep). If `$1006` (the post-trampoline slot) is inert gap (`00 00 00`), stamp a dead `STA $D400,X` (`9D 00 D4`) there. Scanner finds the write → no crash; trampoline intact (zig64/playback unaffected).

Result on the full 286-file corpus (v3.5.19):
- **C1 134/286 → 242/286** (47% → 85%)
- **109 files recovered 0/15 → 15/15** F10-load
- Audio byte-identical (the stamp is in the scan window but never executed during play)

### v3.5.20-v3.5.25: The sub-$1000 cluster

Some Laxity files load at `$0F00`, `$0900`, `$0800`, even `$0400` — below where our SF2 wrapper lives (`$0D7E` header + `$0F90` handlers + `$0F9E` translator). Naively they overlap. The converter aborted with "Translator overflow" and produced a silent SF2.

The fix (`_build_low_load_sf2`) is an alternate layout: place the SF2 header **below** the binary (SF2II is `TopAddress`-relative, no lower bound), put minimal handlers **after** the binary, set a safe placeholder track view. Six versions of this — v3.5.20 ($0F00 cluster, 6 files), v3.5.21 (Phase 2: $0900 cluster, 4 files; also #211-hardening for low-load), v3.5.22 (aux-pointer-$0FFB corruption fix — SF2II reads the aux chain pointer from a HARDCODED `$0FFB`, which low-load binaries span, so we set `_skip_aux=True`), v3.5.23 (lower the floor to `$0500` for DNA_Warrior at `$0800`), v3.5.24 (validation pass on 15 V20-flagged `$0F00` files), v3.5.25 (No_System-Part_2 recovered through the minimal-path; Echo_Beat `$0400` finally fails *cleanly* with an architectural-limit error instead of a `struct.pack` overflow).

**Sub-$1000 cumulative: 30 of 31 files recovered.** The one survivor — Echo_Beat at `$0400` — is genuinely architecturally infeasible. The binary occupies `$0400-$0A6B`, leaving 512 bytes below it for a 525-byte header, and the floor can't drop below `$0500` (zeropage + stack live at `$0000-$01FF`).

### v3.5.26: The Wizax false-positive V20-gate

A 27-file "Angular-class" cluster — SF2 plays but register writes diverge from the original SID — turned out to be mostly false-positive Wizax-A / Zetrex-YP redirects.

The Wizax-A detector's 11-byte voice-clear signature (`LDA #$00; STA $D404; STA $D40B; STA $D412`) is too common. Many regular Laxity SF2-authored NP21 players do exactly that at INIT. Combined with the loose `B9-85-B9-85` ptr-table-setup scan, the redirect was patching `ch_seq_ptr` at addresses that aren't `ch_seq_ptr` at all → corrupted live player data → audio divergence.

Fix: both detectors got an optional `copyright_str=''` parameter. When supplied (every real call site now passes it), they gate on `detect_vibrants_v20()` first. Wizax-A and Zetrex/YP are strict subsets of V20 (which requires a V20-class copyright label like Wizax / Yield Point / Vibrants / Zetrex / 2000 A.D. / Flexible Arts / Laxity-1990 AND size ≤ `$1800`). The gate cleanly distinguishes 4 real Wizax-A + 3 real Zetrex/YP from the 22 false-positive matches.

**20 of 27 → C2 byte-identical** in a single fix, including the entire Unboxed_Intro/Turn_Disk family and SID_Factory_demo_tune_3/4. Backwards-compatible (empty `copyright_str` keeps legacy behavior, existing tests untouched).

### v3.5.27: The Digidag #211 fallback

A second wave of #211 investigation. Of the 4 still-crashing C1 files post-v3.5.18, three (Quark, Space_Game, Too_Much_Hubbard) parse cleanly via argv-load but the pyautogui F10 keyboard-shortcut codepath fails 100% — same Heisenbug class as IAME et al., out of converter scope.

The fourth — Digidag — is a genuine architectural #211 case. `$1000 = 68 98 58` (PLA TYA PLA — binary code, NOT a 2-JMP trampoline). And the player uses ABS `STA $D404` (`8D 04 D4`), not the ABX `9D` form SF2II's scanner counts. So zero matches in `[$1000, $1900)` → AV.

Extended `_ensure_sid_write_in_scan_window_universal()`: when there's no trampoline AND zero natural ABX/ABY `$D40x` writes in the scan window, **append a dead `STA $D400,X; RTS` (`9D 00 D4 60`) at the end of `self.output`** and patch Block 1's `m_DriverCodeTop`/`m_DriverCodeSize` in place to point at the appended stub. Conservative gating (byte-scan = lower bound on opcode sweep). Digidag: C1 0/15 → 10/10 PASS.

### v3.5.28 → v3.5.31: The residual-7 finale

After v3.5.26, the 27-file Angular-class cluster had 7 stubborn survivors. v3.5.28 through v3.5.30 picked off 3 of them (Twone_Five, Dark_Fun, SID_Factory_demo_tune_1), each via a fundamentally different mechanism, described in detail below.

v3.5.31 then turned the entire corpus upside down. The first full-corpus C2/C4 batch surfaced **two files with the SF2-trace=0-writes signature** (Joe_Gunn_Extras, Patterns) — meaning the SF2 produced ZERO SID register writes for files that the SID original played normally. Investigation pinned this to the converter's `init_addr+3` trampoline patch, which was applied indiscriminately whenever `play_addr != init+3` — but for files like Joe_Gunn_Extras (load=$1900), `$1903` is LIVE PLAYER CODE (the operand byte of an `LDA $1928,Y` instruction at $1901), and the patch corrupted init.

The biggest surprise: fixing the patch also recovered **Alliance and Racer**, both of which had been categorized as "deferred V20/Zetrex architectures" requiring multi-week per-variant RE. Two of the original "residual 7" weren't architectural blockers at all — they were our own converter corrupting live code via a too-eager patch. Final corpus state: **C2 280/286 (98%)** with only 3 audio divergences and 3 convert-fails remaining.

---

## Three deep technical stories

### v3.5.28 — The Twone_Five reads-past-binary-end bug

The smallest residual divergence: Twone_Five.sid produced only **+2 extra register writes** vs the original SID. Easy, right?

Disassembling the player at PC `$1148` revealed the entire game:

```
$1140: B9 22 12     LDA $1222,Y     ; freq LO from table at $1222
$1143: 48           PHA
$1144: B9 23 12     LDA $1223,Y     ; freq HI from table at $1223
$1147: BC 6E 11     LDY $116E,X     ; reload Y with voice-specific offset
$114A: 99 01 D4     STA $D401,Y     ; osc<n>_freq_hi
$114D: 68           PLA
$114E: 99 00 D4     STA $D400,Y     ; osc<n>_freq_lo
```

The freq HI table lives at `$1223`. The Twone_Five binary ends at **`$1222`**. So `$1223` is *one byte past the binary*. In a real C64 environment, this is uninitialized DRAM (= `$00`), and the table's natural extension produces benign zero freq HI writes for the silent intro frames.

But the converter's minimal-embed path places the SF2 edit area at `sid_la + len(c64_data) = $1223` — exactly where the player expects RAM zeros. The first bytes of the edit area happen to be `29 29 29 13 14 15 29 ...` (the OL pointer lo bytes for tracks 0/1/2 = `$1329`, `$1429`, `$1529` — same low byte `$29` because OL slots are page-aligned).

So the player reads `$29` instead of `$00` and writes `osc1_freq_hi = $29`, `osc2_freq_hi = $29`, `osc3_freq_hi = $29` at frame 0. Three spurious writes per voice. Plus alignment shifts (the SID and SF2 register-write streams diverge from there on).

**Fix:** in `_inject_player_raw_minimal`, insert a 256-byte zero guard (`POST_BINARY_GUARD = 0x100`) between the embedded binary and the SF2 edit area. 256 bytes covers the full 6502 absolute-Y addressing range. `bytearray(file_size)` zero-initializes the new space, so no extra memset code is needed. `gen.driver_size` includes the guard so SF2II sees the right code-region length.

Result: 1326 register writes byte-identical to original SID. The fix is general — any SID player that declares a data table near the binary end and reads slightly past it now sees RAM-zero where it expects it.

### v3.5.29 — Dark_Fun and the ch_seq_ptr safety gate

Dark_Fun was the biggest residual divergence — voices 1 and 2 silent in the SF2, only voice 0 wrote SID registers. The bytes at `$1A1C-$1A21` looked **exactly** like valid `ch_seq_ptr` data (`54 7C 1B 1B 1B 1B` → pointers `$1B54/$1B7C/$1B1B`, all in-range, all landing on plausible NP21-shaped byte streams). The v3.5.17 `_ptrs_in_range_check` heuristic approved the patch.

But py65 trace of the original player showed **zero reads to `$1A1C-$1A21` during INIT or PLAY**. Static disasm of the player revealed exactly one instruction touching the region: `LDA $1A1E,Y` at PC `$10C1`. The player uses `$1A1E` as a Y-indexed one-byte data table — not as voice-2's ch_seq_ptr lo byte. After patching, `LDA $1A1E,Y` reads `$1F` (the shadow low byte) instead of `$1B` (the original data) → wrong data → silent voices.

**Fix:** new module `sidm2/ch_seq_safety_gate.py`. `is_ch_seq_patch_safe()` does this:

1. Run py65 INIT + N PLAY ticks on the *original* `c64_data`, record SID register writes
2. Build a *patched* copy: `$1A1C-$1A21` repointed at a synthetic shadow buffer; shadow filled with the bytes the original `ptrs[v]` point at
3. Run py65 on the patched copy, record writes
4. Compare write tuples. If identical, the patch is functionally transparent (player uses ch_seq_ptr as designed). If different, the patch corrupts something the player reads.

For a player that uses ch_seq_ptr the standard way (Stinsen, Unboxed), the patched shadow contains the same bytes the player would have read at the original addresses — audio matches. For a player that uses `$1A1C-$1A21` for OTHER data (Dark_Fun), the patched bytes don't match what the player expects, and audio diverges. The gate detects this empirically without needing to disassemble the player or maintain a per-variant ZP table.

Wired into `_inject_laxity_raw_np21` at the existing `_ptrs_in_range_check` site. If the gate returns False, set `skip_ch_seq_patch=True` (preserves `$1A1C-$1A21`, disables F1 edit propagation for the file — but audio is correct, which is the priority).

Result: 1719 register writes byte-identical. Canonical regressions unaffected. 31-file stratified sample 26/31 PASS, gate fired once (Dark_Fun), zero false positives.

### v3.5.32 — Edie_Ball, shared-stream designs, and cycle-accurate verification

After v3.5.31 recovered Alliance and Racer (both V20/Zetrex), Edie_Ball remained as the last Zetrex/YP residual. Same player (1987 Yield Point Music, load `$E000`, init `$E51F`, play `$E009`), same Zetrex/YP detector verdict (ptr_lo=`$E849`, ptr_hi=`$E86C`), same patches applied. So why does Racer pass byte-identical and Edie_Ball not?

py65 didn't help. The v3.5.29 ch_seq_ptr safety gate said SAFE for both. The reason: py65 doesn't simulate CIA-IRQ-driven INIT. The Zetrex/YP player at `$E51F` installs a CIA timer pointing at `$E009`. py65 sees the install but never fires the IRQ during INIT, so its trace of the patched-vs-original simulation doesn't actually exercise the divergence path.

Ablation revealed the truth: reverting the 6 patched bytes (3 lo + 3 hi at `$E849-$E84B` + `$E86C-$E86E`) gives byte-identical audio for Edie_Ball. So the patch IS the cause. But why for Edie_Ball and not Racer?

Looking at Edie_Ball V0's byte stream at `$E887`:
```
00 00 00 00 00 00 00 00 FF 5B FF 85 0A 18 01 18 83 ...
```
The first 8 bytes are zeros (= silence ticks in NP21). Byte 8 is `$FF` — NP21 loop terminator. Byte 9 is `$5B` (= 91) — the loop target. The player jumps to offset 91 of the byte stream.

In the **original** SID memory layout, V0's `$E887 + 91 = $E8E2`. That falls INSIDE V1's stream region (V1 starts at `$E891`). So Edie_Ball uses a **shared-stream design**: V0 has 8 silence ticks then loops into V1's data. V0 effectively continues playing V1's notes after the silent intro.

The converter's shadow pre-fill, however, only writes V0's extracted body (8 zeros) + `$FF $5B` + zeros for the rest of the 256-byte slot. After ch_seq_ptr patch, the player reads V0's shadow at offset 91 — which is zero. V0 plays silence forever where it should have played V1's notes.

Racer V0 also has an early `$FF` and a high loop target (`$83` = 131), but Racer's V0 is musically minor — it's effectively a sustained drone with V1 and V2 carrying the song. Whether V0 plays silence or V1's notes doesn't change the audible output (V1's stream plays anyway via V1's own ch_seq_ptr). For Edie_Ball, V0 is significant, and losing it produces silence-after-intro behavior.

The fix isn't a smarter byte-level heuristic — there isn't one that cleanly distinguishes Edie_Ball from Racer without RE'ing the per-file score data. The fix is a **defense-in-depth audio gate that doesn't depend on understanding the player at all**: just run cycle-accurate emulation on the SF2 we built, compare to the SID, and revert patches if they diverge.

New `sidm2/zig64_audio_gate.py` uses the bundled `tools/sidm2-sid-trace.exe` (zig64, cycle-accurate). After `_inject_laxity_raw_np21` produces `self.output` and the universal #211 stamp lands, the gate traces SF2 vs SID over 16 PAL frames (~50ms each trace). If divergence is detected, the recorded `_ch_seq_patches: list[(offset, original_byte)]` are reverted byte-exact, preserving every other patch (translator, #211 stamp, META trailer).

**Edie_Ball: 433-diff → byte-identical 637 writes**. The gate reverts 6 bytes. Racer, Jewels, Waste's patches are kept because their audio matches. F1 edit propagation is preserved for the 3 files that have it; only Edie_Ball loses F1 — which it never had working-with-correct-audio anyway.

The gate is generic — it verifies SF2 audio matches SID audio for ANY file the converter produces. Future architectural bugs that escape the build-time checks will be caught here. The cost (~200ms per file when the gate fires, ~70% of corpus) is acceptable; the full 286-file batch takes ~1 minute longer than v3.5.31.

**Final corpus state at v3.5.32: C2 281/286 (98.25%), C4 audio 100% of converted, C4 metadata 100% of converted.** Remaining 5: 3 CONV_FAIL (Crosswords, Echo_Beat architectural, Magic_Sound) + 2 C2-diverge (Exorcist_preview wrapper-init, Patterns 11 minor divergences).

### v3.5.31 — Joe_Gunn_Extras, the init+3 patch, and the false "deferred architecture"

This is the most consequential single fix of the entire post-v3.5.18 run.

The first full-corpus C2/C4 batch at v3.5.30 produced 7 C2 fails. Two of them stood out as structurally weird:

| File | SID writes | SF2 writes |
|------|-----------:|-----------:|
| Joe_Gunn_Extras | 1756 | **0** |
| Patterns | 1793 | **0** |

The SF2 was producing **zero SID register writes**. Not "wrong audio" — **silent**. For files whose SID original plays normally and whose embedded NP21 binary is byte-identical to the SID's binary in our SF2 output. Something was breaking the player binary itself.

Inspecting the SF2 bytes for Joe_Gunn_Extras (PSID load=$1900):

```
$1900: A8           TAY              ← init entry
$1901: B9 28 19     LDA $1928,Y      ← in original SID
                                       ↓
$1900: A8           TAY              ← init entry
$1901: B9 28 4C     LDA $4C28,Y      ← in our SF2 — corrupted!
$1904: 9E 0F         (illegal opcode)
```

Bytes `$1903 $1904 $1905` in the original SID were `$19 $85 $FB` — the operand high byte of the `LDA $1928,Y` instruction, plus a `STA $FB` opcode/operand. In our SF2, those bytes had been overwritten with `$4C $9E $0F` (JMP $0F9E — the translator). The `LDA $1928,Y` instruction's high-byte operand became `$4C`, so it read from `$4C28` instead of `$1928`. Init crashed. Player ran no code. SF2 silent.

Tracing back: `_inject_laxity_raw_np21` has always written a JMP at `init_addr+3` to redirect zig64's auto-detect PLAY (which calls init+3) through the translator. The safety check was:

```python
play_redirect_safe = (play_addr != init_addr + 3)
if play_addr == init_addr + 3:
    # validate as JMP $XXXX, extract play target
    play_redirect_safe = True

if play_redirect_safe:
    # patch init+3 with JMP TRANSLATE_BASE
```

That safety check is **exactly backwards**. It says "init+3 is safe to patch when `play_addr != init+3`." For Stinsen/Unboxed/Beast/Angular this happens to be fine because their init+3 is either `JMP $XXXX` (covered by the `if play_addr == init+3` branch) or inert gap. For files like Joe_Gunn_Extras where init=$1900, play=$1006, AND init+3 contains live player code, the patch is destructive.

**Fix:** flip the meaning of `play_redirect_safe`. It now means "the bytes at init+3 ARE safe to patch":

```python
play_redirect_safe = False
stub_lo = init_addr + 3 - sid_la
if 0 <= stub_lo and stub_lo + 2 < len(c64_data):
    b0, b1, b2 = c64_data[stub_lo:stub_lo + 3]
    if b0 == 0x4C:           # Case A: JMP abs
        # extract jmp_target as effective_play_addr if play_addr == init+3
        if sid_la <= (b1 | (b2 << 8)) < sid_la + len(c64_data):
            if play_addr == init_addr + 3:
                effective_play_addr = b1 | (b2 << 8)
            play_redirect_safe = True
    elif (b0, b1, b2) in ((0x00, 0x00, 0x00), (0xEA, 0xEA, 0xEA)):
        # Case B: inert gap
        play_redirect_safe = True
```

Any other byte pattern is treated as live code → skip the patch.

The result was bigger than expected. The full-corpus re-run recovered **four files**, not the two I'd targeted:

| File | C2 v3.5.30 | C2 v3.5.31 |
|------|------------|------------|
| Joe_Gunn_Extras | DIFF (1756 vs 0) | **PASS (1756 byte-identical)** |
| SID_Factory_demo_tune_2 | DIFF (1133 vs 1136) | **PASS (1133 byte-identical)** |
| Alliance | DIFF (1283 vs 532) | **PASS (1283 byte-identical)** |
| Racer | DIFF (909 vs 2211) | **PASS (909 byte-identical)** |

**Alliance and Racer had been documented as "deferred V20/Zetrex architectures"** in `memory/vibrants-v20-findings.md` and the Zetrex/YP cluster notes. The presumed root cause was that pre-NP21 player variants need full per-variant reverse engineering. The actual root cause was the same init+3 patch corrupting their player code. Once we stop corrupting init, the embedded-binary path produces byte-identical audio.

This is the single most impactful single-fix moment of the entire project. Two assumed-multi-week-RE blockers turned out to be a single mis-stated safety check.

Final corpus state at v3.5.31:
- **C2: 280/286 (98%)** — up from 219/286 (77%) before this session
- **C4 audio: 283/283 (100% of converted)**
- **C4 metadata: 283/283 (100% of converted)**
- Remaining 6 fails: 3 CONV_FAIL (Crosswords, Echo_Beat architectural, Magic_Sound) + 3 C2-diverge (Edie_Ball, Exorcist_preview, Patterns)

The "audio first; C3 second" principle paid off. Editor-view propagation for Alliance/Racer is still deferred (their V20/Zetrex players don't expose NP21-compatible byte streams to the editor), but the audio is now bit-exact.

### v3.5.30 — SID_Factory_demo_tune_1 and the late-divergence trap

After v3.5.29, the gate caught Dark_Fun but missed SID_Factory_demo_tune_1, which kept showing the same voice-misorder pattern. Six-case ablation pinpointed the cause:

| What's reverted in the SF2 | Diffs vs SID |
|---------------------------|--------------|
| nothing (baseline) | 377 |
| `$1003` trampoline only | 377 |
| ch_seq_ptr only | **0** |
| translator only | 377 |
| `$1003` + ch_seq_ptr | **0** |
| `$1003` + translator | 377 |
| ch_seq_ptr + translator | **0** |

Reverting *only* the ch_seq_ptr patch gives byte-identical audio. The patch IS the cause — but the v3.5.29 safety gate said it was safe?

The bytes at `$1A1C-$1A21` for SFd1: `1E 1E 1E 1F 1F 1F` → all three voices point at **`$1F1E`** (highly unusual — same address for V0/V1/V2). The gate's mirrored shadow buffer copies the bytes from `$1F1E` into all three shadow slots. For the first 14 PLAY frames, py65 produces IDENTICAL audio between original and patched — the bytes line up. Divergence only emerges at frame 14+.

The default `n_play=4` traced too few frames.

**Fix:** three tuning changes to `is_ch_seq_patch_safe()`:

1. **`n_play` default 4 → 16.** Covers SFd1 with margin.
2. **`early_exit_check` callback in `_trace_register_writes`.** As soon as the patched simulation's writes diverge from the pre-traced original, abort. Cuts UNSAFE-file cost from ~5s to ~2s — most UNSAFE files diverge in the first few frames; SFd1 is the outlier.
3. **`max_init_cyc` 2_000_000 → 20_000.** Most INITs complete in <50k cycles. The old 2M cap was wasted on busy-wait INITs (Stinsen's INIT loops on a CIA timer that py65 doesn't simulate, so the cycles produce no register writes anyway — they're just slow).

Result: 1904 register writes byte-identical. 31-file sample 27/31 PASS, +1 over v3.5.29. Gate fires twice (Dark_Fun + SFd1), still zero false positives.

The lesson: empirical gates need conservative trace windows. v3.5.29's choice of `n_play=4` was reasonable on the data we had (Dark_Fun diverged immediately). v3.5.30 expanded it as soon as a counterexample emerged.

---

## What's left

Of the 27 originally-divergent files in the Angular cluster, **22 were fixed by the v3.5.26 Wizax/Zetrex V20-gate, 3 more by v3.5.28-v3.5.30 (Twone_Five, Dark_Fun, SID_Factory_demo_tune_1), plus 4 more by v3.5.31's init+3 patch safety (Joe_Gunn_Extras, SID_Factory_demo_tune_2, and the two assumed-deferred Alliance + Racer)**. Three genuine C2 residuals remain across the entire 286-file Laxity corpus:

| File | Architecture | Status |
|------|--------------|--------|
| **Edie_Ball** | Zetrex/YP `$E000` (1987 Yield Point) | Didn't recover with the v3.5.31 init+3 fix like sibling Racer did — needs separate investigation. The Zetrex/YP "cluster" sharing-the-same-player-binary claim should be re-tested with the new converter. |
| **Exorcist_preview** | Laxity `$9000` autodetect | Wrapper-init interaction — the SF2 wrapper layer adds ~50 extra register writes per 60 frames even with the translator and wave-copy fully disabled. Native trace at `$9000/$9006` matches the SID exactly; only the wrapper trace via `$0F90/$0F94` diverges. Most plausible: CIA-IRQ-during-init interaction or accumulated cycle drift. Multi-hour RE; documented in `memory/exorcist-preview-deferred.md` |
| **Patterns** | Laxity `$5FF4` autodetect | Reduced from 1793-vs-0 to 11 minor divergences (instrument-table edge case at frame 169). Same number of register writes (1793 each), just 11 with wrong content (0.6%). |

Plus 3 CONV_FAIL files: **Crosswords** (unknown player rejected by converter), **Echo_Beat** (load=$0400 architectural dead-end — header can't fit below the binary), **Magic_Sound** (unknown player rejected).

The v3.5.31 finding that 2 of the 4 "deferred V20/Zetrex" cases were actually init+3 corruption suggests the "deferred architecture" categorization should be revisited for editor-view propagation too. **Audio** works fine for V20/Zetrex files through the embedded-binary path; only the editor-side byte-stream interpretation requires per-variant RE.

---

## Tools and infrastructure

The fix-then-verify loop benefits as much from tooling as from clever code:

- **zig64 cycle-accurate SID tracer** (`tools/sidm2-sid-trace.exe`) — fast, deterministic register-write traces. The ground truth for the C2 criterion.
- **py65 6502 emulator** — slower but Python-native, lets us instrument every memory access (`Obs.__getitem__/__setitem__`) for read-before-write analysis, ZP usage scans, and the v3.5.29 safety gate's patched-vs-original audio comparison.
- **`verify_audio_match.py`** — the C2 test driver. Traces SID + SF2 in zig64, strips the cycle column, compares (frame, register, value) tuples. Reports first divergence with context.
- **`pyscript/find_rbw_scratch.py`** — new in v3.5.22. py65 read-before-write detector. Catches "binary needs RAM-zero in window X" cases (the `$0FFB` aux-pointer corruption, the Twone_Five `$1223` freq-table extension).
- **`pyscript/sf2_argv_crash.py`** — argv-load reproducer for SF2II crashes. Discovered while symbolizing the #211 bug; bypasses the PyAutoGUI flakiness that masked the real crash.
- **The 286-file Laxity corpus** — the test set that's caught more bugs than the unit tests. Every release runs C1/C2/C4 against it.
- **Memory notes** (`~/.claude/projects/.../memory/`) — per-investigation findings that survive context compactions. The negative findings (`zp-indirect-y-negative.md`, `dynamic-instr-detector-attempt.md`, `wave-copy-non-idempotency.md`) are arguably more valuable than the positive ones because they prevent repeated dead-ends.

The **test suite** stands at 1026 tests as of v3.5.30. Most are pure-Python unit tests for the detector zoo and the 6502 emitters. The integration tests (canonical Stinsen/Unboxed/Beast/Angular byte-identical regression checks) catch architectural mistakes immediately.

---

## Recurring patterns

A few patterns showed up over and over and are worth naming:

**The byte-shape false positive.** v3.5.17 (ch_seq_ptr in-range check), v3.5.26 (Wizax/Zetrex copyright gate), v3.5.29 (ch_seq_ptr py65 safety gate). Every time a heuristic looks at bytes and says "this looks like X," some file will have bytes that look like X but mean something else. The defense is layered: name-based hint → structural shape → empirical simulation.

**The "patch one byte, break everything" trap.** Single-byte patches (the `$1003` trampoline, the `$1006` #211 stamp, the `$1A1C-$1A21` ch_seq_ptr redirect) live deep in the player binary. Each one has to be verified against (a) the player's static usage of that address, (b) the player's dynamic reads at INIT, (c) the player's dynamic reads during PLAY, (d) end-to-end audio match. Skipping any of (a)-(c) means hitting a Dark_Fun.

**The minimal-window constraint.** The SF2 wrapper has to fit between the SF2II-expected header layout (`$0D7E` magic) and the embedded binary (`$1000`). That's 642 bytes minus the 9 header blocks, leaving 98 bytes for the multipat translator at `$0F9E-$0FFA`. Multiple fixes (v3.5.8 trampoline consolidation, v3.5.30 ZP early-exit instead of save/restore) were shaped by this window.

**"Audio first; C3 second."** When a fix has to choose between "F1/F2/etc. edits propagate to playback" and "the SF2 audio matches the original SID," we choose audio. The safety gates default to `skip_ch_seq_patch=True` when patching would break audio, even though that disables F1 edit propagation for the file. The user can still edit the file in SF2II — they just won't see their edits reflected in playback, which is a softer failure than wrong audio.

---

## Per-version index

This section is the running release log, updated at each version bump. Older entries get compressed but kept for the narrative arc. For technical detail beyond what's here, see `CHANGELOG.md`.

### v3.5.33 — gate extended (wave-copy NOP + 200-frame window) (2026-05-23)

The final fixable audio residual. Patterns.sid had the right NUMBER
of register writes (1793) but 11 of them diverged: `osc2_attack_decay:
$7F` (SF2) vs `$00` (SID), recurring at frames 169, 185, 201, 249,
265, 281 — every 16 frames. Ablation pinpointed the wave-copy
routine: it writes 32 bytes from the SF2 edit area to
`np21_wave_data_addr` (`$6903`) and `np21_note_addr` (`$6963`) every
PLAY tick; for Patterns those addresses overlap the file's instrument
table, so the wave-copy stomps an AD byte with `$7F` (the SF2 packed
sequence terminator).

Extended `_run_post_build_audio_gate()` with progressive revert:
trace at 200 PAL frames; if diverge, try reverting ch_seq_ptr patches
first, then NOP'ing wave-copy JSR, then both. The gate now tracks
`_wave_copy_jsr_offs: list[int]` of absolute file offsets where the
translator JSRs the wave-copy routine, found via 3-byte pattern match
during translator emit.

**Patterns: 11-diff → byte-identical 1793 writes.** C2 corpus
281/286 → 282/286 (98.6%). Cost: ~30-120ms per file depending on how
many revert attempts the gate makes.

The wave-copy disable is a tradeoff — Patterns loses F3 (wave) edit
propagation in exchange for byte-identical audio. The post-build
gate makes that tradeoff automatic and per-file.

### v3.5.32 — zig64 post-build audio gate (2026-05-23)

The Edie_Ball recovery — the last Zetrex/YP residual. py65 can't
simulate the CIA-IRQ-driven INIT, so the py65 ch_seq_ptr safety gate
falsely says SAFE for Edie_Ball; cycle-accurate emulation diverges.
Edie_Ball V0's `$FF $5B` (loop to offset 91) is a shared-stream
design — offset 91 falls inside V1's data in the original, but the
converter's truncated shadow only writes 8 zeros + `$FF $5B` + zeros,
so the player jumps to silence. New `sidm2/zig64_audio_gate.py`:
cycle-accurate post-build verification via the bundled
`tools/sidm2-sid-trace.exe`. After the universal #211 stamp, the gate
traces SF2 vs SID; if audio diverges, the ch_seq_ptr patches are
reverted byte-exact. **Edie_Ball: 433-diff → byte-identical 637
writes.** The gate selectively keeps Racer/Jewels/Waste's patches
(audio matches, F1 propagation preserved). C2 corpus 280/286 → 281/286.
Cost: ~200ms per file when gate runs. 1032 tests (+3
`TestZig64AudioGate`).

### v3.5.31 — init+3 patch safety (2026-05-23)

The most impactful single fix of the post-v3.5.18 run. Old check
`play_redirect_safe = (play_addr != init_addr + 3)` had safety
EXACTLY BACKWARDS: it patched init+3 with `JMP TRANSLATE_BASE`
whenever play_addr was elsewhere, even when init+3 contained live
player code. For Joe_Gunn_Extras (load=$1900), $1903 = `$19` (the
operand high byte of `LDA $1928,Y` at $1901); patching it crashed
init → SF2 silent (0 SID writes). New check: only patch when init+3
is `$4C XX XX` (JMP — Stinsen/Beast/Hubbard) OR inert gap
(`$00 $00 $00` / `$EA $EA $EA` — Twone_Five-class). Any other byte
pattern → live code → skip. **C2 audio: 276/286 → 280/286 (97%→98%)
across the full 286-file corpus**. Recovered: Joe_Gunn_Extras,
SID_Factory_demo_tune_2, **Alliance + Racer** (both had been
categorized as "deferred V20/Zetrex architectures" — turns out the
issue was our init+3 patch, not the player kernel). Partially
recovered: Patterns (1793 writes vs 0 → 1793 vs 1793 with 11 minor
divergences). 1029 tests; 3 new `TestInitPlus3PatchSafety`.

### v3.5.30 — Late-divergence safety gate (2026-05-23)

`is_ch_seq_patch_safe()` tuned to catch SID_Factory_demo_tune_1, which diverges only at frame 14 — past the v3.5.29 default trace window. `n_play` 4→16, new `early_exit_check` callback (UNSAFE files exit in ~2s), `max_init_cyc` capped at 20k. SFd1: 1904 writes byte-identical. 1026 tests; 31-file sample 27/31 PASS, gate fires twice, zero false positives.

### v3.5.29 — ch_seq_ptr py65 safety gate (Dark_Fun fix) (2026-05-23)

New module `sidm2/ch_seq_safety_gate.py` empirically verifies the ch_seq_ptr → shadow patch under py65 with a mirrored shadow buffer. Catches Dark_Fun (and similar) files where `$1A1C-$1A21` bytes look like in-range pointers but the player uses them for other data. Dark_Fun: 1719 writes byte-identical. 1025 tests.

### v3.5.28 — Minimal-embed post-binary zero guard (Twone_Five fix) (2026-05-23)

256-byte zero guard between embedded binary and SF2 edit area in `_inject_player_raw_minimal`. Some players (Twone_Five canonical) declare a data table at the binary's last byte and read 1+ bytes past, relying on RAM-zero. The edit area's OL ptr bytes had been landing where the player expected zeros. Twone_Five: 1326 writes byte-identical. 1020 tests.

### v3.5.27 — Digidag #211 alternate scan-window (2026-05-22)

For C1-crashing files where `$1000` is binary code (no 2-JMP trampoline) AND the player uses ABS `STA $D404` not ABX, append a `9D 00 D4 60` stub at end-of-file and patch Block 1's `m_DriverCodeTop`/`m_DriverCodeSize` to point at it. Digidag: C1 0/15 → 10/10. Q/SG/TMH remain (pyautogui-only Heisenbug, out of converter scope). 1019 tests.

### v3.5.26 — Wizax/Zetrex V20-gate (2026-05-21)

The Wizax-A and Zetrex/YP byte-pattern detectors gate on `detect_vibrants_v20()` first (copyright-class hint + size ≤ `$1800`). Eliminates 22 false-positive matches that had been corrupting `ch_seq_ptr`. 20 of 27 Angular-class divergences recovered. 1016 tests.

### v3.5.25 — Sub-$1000 cluster complete (2026-05-21)

No_System-Part_2 recovered via the minimal-path low-load dispatch (corrects a memory note that had claimed driver11-template path). Echo_Beat now fails cleanly with an architectural-limit error instead of a `struct.pack` overflow. Sub-$1000 cumulative: 30 of 31 files recovered (Echo_Beat at `$0400` is the sole architectural dead-end). 1014 tests.

### v3.5.24 — V20+$0F00 validation (2026-05-21)

The 15 Vibrants-V20-flagged sub-$1000 files (load=`$0F00`) all pass C2 byte-identical and C4 MATCH already — the low-load layout from v3.5.20+ covers them. The "V20 deferred" memory entry was about editor-view edit propagation (still deferred); the gating C1/C2/C4 blocker was sub-$1000 collision. No code change.

### v3.5.23 — DNA_Warrior $0800 (2026-05-21)

Lowered the low-load `LOAD_BASE` floor `$0600→$0500` (stays above zeropage/stack/BASIC buffer). DNA_Warrior (load=$0800, init=$2133>play=$2130) fully recovered.

### v3.5.22 — Aux-pointer $0FFB corruption fix (2026-05-19)

SF2II reads the aux-chain pointer from hardcoded `$0FFB`. Low-load binaries span `$0FFB`, so `_inject_auxiliary_data`'s pointer write corrupts live player data. Fix: `_build_low_load_sf2` sets `_skip_aux`; `_inject_auxiliary_data` early-returns; binary's `$0FFB` stays intact; SF2II reads it as unmapped RAM and cleanly skips aux. $0900 cluster: 7/7 recovered.

### v3.5.21 — Sub-$1000 Phase 2 + low-load #211 hardening (2026-05-19)

Lowered floor to $0600 for $0900-load files. Low-load layout now emits a "scan bait" `STA $D400,X; RTS` for the #211 sweep boundary, making it crash-robust. Hand_Interludes/Rudolph recovered; Broom_Tycoon/Slash deferred (header overlaps player scratch).

### v3.5.20 — Sub-$1000 wrapper-collision (Phase 1) (2026-05-19)

New `_build_low_load_sf2()`: header below the binary, handlers after the binary. Recovered Annelouise, Axel_F, Beat_the_Shit_3, Crap_5, Force_Tune, Shit ($0F00-load).

### v3.5.19 — #211 validation at corpus scale (2026-05-19)

C1 134/286 → 242/286 (47% → 85%); 109 files recovered 0/15 → 15/15. Audio byte-identical (the stamp is in the scan window but never executed during play).

### v3.5.18 — SF2II upstream #211 fix (2026-05-18)

`Editor::DriverUtils::GetSIDWriteInformationFromDriver` at `driver_utils.cpp:419` dereferenced `result.begin()->m_CycleOffset` on an empty vector. SF2-side workaround: stamp a dead `STA $D400,X` (`9D 00 D4`) at `$1006` when that slot is inert PRG gap.

### v3.5.17 — `_ptrs_in_range_check` + META trailer (2026-05-14)

Two corpus-wide fixes. `_inject_laxity_raw_np21` skips the `$1A1C/$1A1F` patch when those bytes aren't valid in-range pointers (Angular: that region is state-machine data). Metadata round-trip implemented for the first time — title/author/copyright in a `b"META"` trailer past SF2 content.

### v3.5.16 — Zetrex/YP F1 cluster (2026-05-12)

3-file cluster (Jewels, Waste, Racer) gets F1 edit-propagation pipeline. Same architecture as Wizax-A: voice byte streams accessed via ZP-indirect-Y, NP21-compatible bytes, file-specific ptr-table addresses. Also adds zig64 entry stub at `$1000` for binaries loaded elsewhere ($E000 etc.).

### v3.5.15 — Wizax-A F1 cluster (2026-05-12)

First Vibrants V20 sub-cluster with working edit propagation through the NP21 multipat-translator pipeline. 4 files (2000_A_D, Fight_TST_II, Hall_of_Fame, Min_Axel_F).

### v3.5.14 — All 14 V20 files identified (2026-05-12)

Cluster coverage 14/14: Wizax-A (4), Wizax-B (2 — adds Magic_Sound), James_Bond_Theme_Remix (singleton), Atom_Rock (singleton), Fast_Stuff_1 (singleton). `V20_MAX_SIZE` bumped to `$1800`; "Laxity" added to V20 copyright hints.

### v3.5.13 — Wizax-A + Wizax-B detection (2026-05-12)

The "1987 Wizax 2004" copyright covers 4 files split across 2 sub-clusters by player code (Wizax-A: 3 files, voice-control-clear signature; Wizax-B: Cool_as_Wize_Title, indexed STA writes).

### v3.5.12 — Zetrex/YP detection (2026-05-12)

Second V20 cluster (Jewels, Waste, Racer — 3 files sharing the same player at load `$E000`). Detected by 35-byte player signature at c64_data offset 9.

### v3.5.11 — V20 advisory + autodetect short-circuit (2026-05-12)

Pre-NP21 Vibrants V20 files (1987-1990, copyrights Wizax/Yield Point/2000 A.D./Zetrex/Flexible Arts) get an advisory log line and skip the NP21 ch_seq_ptr autodetect (which had been lifting 2-14 byte "patterns" from freq LUTs — garbage from the SF2 editor's perspective). 13 detected.

### v3.5.10 — F4 (pulse) Beast + Angular (2026-05-12)

Discovered the nibble-packed PW byte 0 encoding (high nibble → PW lo, low nibble → PW hi). New `_emit_pulse_packed_copy_routine` (34B 6502). Stage 7 now complete across F1/F2/F3/F4/F5 for all three canonical variants modulo column-set limitations.

### v3.5.9 — F5 (filter) Beast + Angular (2026-05-12)

Cutoff_hi byte streams at `$1A7D` (Beast) / `$1A1F` (Angular); res_routing + mode_vol fixed at `$100A/$1009`. cutoff_lo (D415) unused in both. 19-byte cutoff-only routine.

### v3.5.8 — F5 (filter) Stinsen + translator consolidation (2026-05-11)

Full RE of the filter handler at `$15F6-$167F`. State machine: bit 7 of cmd selects SET vs SWEEP. Tail of translator consolidated (instr + pulse + filter into a 10B trampoline) to fit the 98-byte window after adding the 4th JSR.

### v3.5.7 — F4 (pulse) Stinsen (2026-05-11)

Parallel PW lo / PW hi byte streams at `$1957`/`$193E`. 25-byte split-copy routine. zig64-verified.

### v3.5.6 — ch_seq_ptr short-body neutralized (2026-05-10)

Editor-view yield 76% → 78%. Files with one silent voice (Intro_2 voice 1 = 2-byte body) had their entire ch_seq_ptr table rejected. Short bodies (1-7 bytes) now return 0 (neutral) instead of -1000.

### v3.5.5 — play_reads filter relaxed (2026-05-10)

Editor-view yield 30% → 76% (+129 files). The ch_seq_ptr autodetect's strict play-reads-coverage check was rejecting structurally-valid candidates; relaxed from hard reject to +score bonus.

### v3.5.4 — Wave-copy idempotency + Beast/Angular F2 verifiable (2026-05-10)

Removed the `$7F`-swap from `find_and_extract_wave_table`. Wave-copy now byte-perfect round-trip. End-to-end zig64-verified F2 edit propagation for Beast + Angular.

### v3.5.3 — Beast/Angular instrument table detectors (2026-05-10)

F2 (instruments) AD/SR edits now propagate for three known layouts: Stinsen column-major, Beast row-major 8B, Angular row-major 2B.

### v3.5.0 → v3.5.2 — Stage 7 F2/F3 (2026-05-09 → 2026-05-10)

Criterion 3 extends from sequences to wave (F3, v3.5.0) and instruments (F2 Stinsen, v3.5.2). 31-byte split-copy routine for wave, 41-byte column-copy routine for instruments. `_inject_laxity_raw_np21` autodetect lifts +12 net new files (75→87 editor-view, 18%→30%).

### v3.4.1 — Block 3 NameLen → TextFieldSize (2026-05-09)

Solo F10-load: Stinsen 47% → 100%, Unboxed → 100%. Block 3 emits `TextFieldSize=0` instead of `NameLen`. Same fix unblocks Angular + Beast (was 0% deterministic crash → 100%). Toolkit (`appverifier-*.bat`, `pyscript/sf2_debug_inspect_v2.py`) created during the investigation.

### v3.4.0 — Editor fidelity push (2026-05-08)

SF2 output structurally matches SF2II's bundled reference corpus across all 9 header blocks. Multi-pattern segmentation splits each voice's NP21 byte stream at instrument-prefix boundaries. 87-byte multi-pattern translator at `$0F8E`. Driver-11-format Wave/Pulse/Filter/Instruments tables emitted. Block 9 populated. Aux chain `[3, 2, 1, 4, 5, END]` matches reference.

### v3.3.0 — Criterion 3 closed for sequences (2026-04-30)

Two-part architecture: build-time shadow pre-fill (3-slot × 256B, `ch_seq_ptr` patched to shadow), runtime translator at `$0F0E` (51 bytes of 6502) regenerating the shadow each PLAY tick via `sidm2/sf2_to_np21.py`. Stinsen and Unboxed both pass C3 strict for F1.

### v3.2.2 — NP21↔SF2 byte mapping corrected (2026-04-29)

Removed the +1 note shift from v3.1.9. Verified against player disassembly at `$10F4-$10FB`: NP21 byte `$00` = "no new note this tick" (not C-0). 6 regression tests pin the corrected mapping.

### v3.2.1 — First end-to-end Stinsen + Unboxed (2026-04-27)

Auto-driver-selector picks Laxity for `SidFactory_II/Laxity` files. `sf2_to_sid.py` reads metadata from SF2 aux block id=5. Inline EDITABLE-REPLAY GAP comment block in `_build_np21_sf2_edit_area`.

### v3.2.0 → v3.1.6 — Editable SF2 + correct Block 3 (2026-03-22 → 2026-03-30)

Real Block 3 column addresses (Filter `$1989`, Wave `$1942`, Instruments column-major). Note index mapping correctness. NP21 sequence extraction stops at `$FF`. Valid SF2 output (magic + headers) recognized by SF2II.

### v3.1.5 → v3.0.1 — Laxity driver fork (2026-03-22 → 2025-12-27)

Embed any Laxity NP21 binary verbatim at `$1000` with a minimal `$0D7E` wrapper. Restored 99.93% accuracy (from 0.60%) for native Laxity files. Filter accuracy validation pipeline (zig64 ground truth tracer).

### v3.0.0 — Auto SF2 reference detection (2025-12-27)

For SF2-exported SIDs, automatic detection and pass-through copy of the original SF2 reference. Restored from "almost zero" to 100% byte-identical for that subset.

### v2.10 and earlier (2025 and before)

Foundation: SF2 Viewer GUI, SID Inventory (658+ files), Conversion Cockpit, validation system, batch testing harness, CI/CD. Coverage of native Laxity files was effectively zero. See archived `docs/archive/changelogs/CHANGELOG_v2.md`, `CHANGELOG_v1.md`, `CHANGELOG_v0.md` for full history.

---

## Reading further

- `CHANGELOG.md` — full release log with per-version technical detail
- `CLAUDE.md` — AI-assistant quick reference for the current state (architecture, conventions, critical rules)
- `docs/ARCHITECTURE.md` — technical architecture document
- `docs/COMPONENTS_REFERENCE.md` — module reference
- `docs/reference/SF2_FORMAT_SPEC.md` — SF2 file format reference
- `memory/` (in the AI assistant's project memory) — per-investigation findings, including negative results

This story document is maintained alongside the codebase. **Each version bump appends a section to the per-version index.** The narrative sections (Eras I-VI and the deep technical stories) get updated when a new architectural finding warrants it.

If you're working on adding support for a new C64 player, the recommended reading order is:

1. This document (overview and recurring patterns)
2. `CLAUDE.md` (the active "what's where" reference)
3. `docs/ARCHITECTURE.md` (technical reference)
4. The memory notes for the closest existing variant cluster

If you're a C64 music archivist trying to convert a specific SID file, the recommended reading order is:

1. `README.md` (installation + quick start)
2. `docs/guides/GETTING_STARTED.md`
3. `docs/guides/TROUBLESHOOTING.md` when it inevitably breaks

If you're an AI agent picking up this codebase, **start with `CLAUDE.md` and the memory notes**, not this document.

---

*"There are exactly two ways to bridge a pre-compiled 6502 program and a structured editor data model: extract the model from the binary, or embed the binary and call it from the editor's hooks. SIDM2 does both, layered, with a runtime translator stitching them together."*
