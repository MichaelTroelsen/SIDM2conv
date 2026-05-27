# The SIDM2 Story

*How an "experimental converter" became a byte-accurate bridge between two C64 music tools that don't speak each other's language.*

**Current version:** v3.5.60 (2026-05-27) — 1280 tests, 286-file corpus, **100% audio-verified (286/286 byte-identical via zig64). 2000 A.D. cluster complete: both Echo_Beat and Galax_it_y show real F1 patterns in the editor.**
**Latest chapter:** [v3.5.60 — 2000 A.D. cluster complete: Echo_Beat editor view via low_load_layout](#v3560--2000-ad-cluster-complete-echo_beat-editor-view-via-low_load_layout-2026-05-27)

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
| **C2 byte-identical** | **283/286 (99%)** of the Laxity corpus — **every file the converter produces a SF2 for now matches the SID byte-identically over 300 PAL frames.** The 3 still-failing are all CONV_FAIL with documented architectural-infeasibility error messages: Echo_Beat (load `$0400`, no room for SF2 header below the binary), Crosswords + Magic_Sound (load `$F000`, no room for edit area above the binary in 16-bit address space). Zero non-architectural audio residuals. |
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

### v3.5.60 — 2000 A.D. cluster complete: Echo_Beat editor view via low_load_layout (2026-05-27)

v3.5.59 shipped the 2000 A.D. extractor and wired it into the standard
`np21_edit_area_builder` path. Galax_it_y (load $1000) immediately
benefited; Echo_Beat (load $0400) didn't, because anything below $1000
takes the `low_load_layout` PRG geometry — header below the binary,
handlers above, edit area pinned at a page-aligned address past the
binary. That path has used `placeholder_edit_area.build_placeholder_edit_area`
to emit an empty 3-track placeholder for the editor view, by design,
since v3.5.42.

The "small refactor" sketched in the v3.5.59 deferral note turned out
to be smaller than expected: `build_placeholder_edit_area` already had
the right shape (compute layout addresses, emit OL + seq ptr tables,
emit orderlists + sequences, append zero F-tables, populate gen fields).
The only thing the placeholder did differently from the populated case
was emitting one empty sequence and three identical orderlists pointing
at it. So instead of building a parallel `np21_edit_area_builder`
override, the cleaner move was to add an optional `voice_streams` parameter
to `build_placeholder_edit_area`. When None: existing placeholder
behavior. When provided: segment each stream at `$A0` boundaries,
produce N orderlists + N sub-patterns, populate the seq ptr table for
N entries instead of 1.

The detection wire-in goes inside `low_load_layout.build_low_load_sf2`,
which previously took only `(c64_data, sid_la, init_addr, play_addr)`.
Added a `psid_copyright` keyword and threaded it from `laxity_raw_np21_builder`'s
sub-$1000 dispatch. Inside, attempt `detect_2000ad_layout` +
`extract_2000ad_voice_streams`; on success, pass the streams to
`build_placeholder_edit_area`. The change to the non-2000-A.D. low-load
path is exactly nothing (default `psid_copyright=''`, default
`voice_streams=None`).

Echo_Beat now produces 4 segments on V0, 3 on V1, 3 on V2 — total of
10 sub-patterns visible in the editor instead of 1 empty placeholder.
Same caveats as Galax_it_y: notes display as opaque byte values
(no freq LUT), F1 edits don't propagate to playback (the embedded
binary keeps reading its own pattern data).

### What this completes

The v3.5.58 memory note's plan was "ship 2000 A.D. cluster, then stop."
v3.5.58 did the RE + detector. v3.5.59 did the extractor + Galax_it_y
wire-in. v3.5.60 does Echo_Beat. Cluster complete.

### Per-criterion delta

| Criterion | v3.5.59 → v3.5.60 |
|-----------|--------------------|
| C1 (loads) | 286/286 — unchanged |
| C2 (audio) | 286/286 — unchanged |
| **C3 (editor)** | **+1: Echo_Beat now shows real F1 patterns; cluster (2/2) complete** |
| C4 (round-trip) | unchanged |

Tests: 1272 → 1280 (+8).

### The deferred-list status

From the original cluster RE memo, the deferred items for "minimum
viable C3 support" were:

- ✅ Detector (v3.5.58)
- ✅ Extractor + wire-in (v3.5.59 — Galax_it_y)
- ✅ Echo_Beat editor view (v3.5.60 — via low_load_layout)

Still deferred (intentionally):
- Frequency LUT decode (would upgrade displayed notes from opaque
  bytes to chromatic C-X / D#X labels).
- F1 edit propagation (needs a writeback mechanism that converts
  edited NP21 bytes back to 2000 A.D. format — different problem class
  than Wizax-A's ch_seq_ptr redirect).
- Other V20 singletons (James_Bond, Atom_Rock, Fast_Stuff_1, etc.) —
  bad ROI per the original memo.

---

### v3.5.59 — 2000 A.D. cluster extractor: Galax_it_y editor view (2026-05-27)

v3.5.58 stopped at "detector + RE memo." The natural next move was to
actually use that detector — extract per-voice patterns from the
1988 2000 A.D. shared player (Echo_Beat + Galax_it_y) and feed them
into the SF2 editor's F1 view, so users see something coherent instead
of the empty placeholder.

The interesting part wasn't the extractor — it was discovering, mid-
implementation, that the v3.5.58 detector itself was silently broken.
The memory note claimed the pattern-pointer table sits at `load+$788`
for both cluster files. That's true for Galax_it_y (load $1000, ends
$17C0 → `load+$788` = `$1788`, in-range). It's NOT true for Echo_Beat
(load $0400, ends $0A6C → `load+$788` = `$0B88`, *past the end of the
binary*). The detector was returning a `Vibrants2000ADLayout` with a
broken pattern_ptr_lo_addr for Echo_Beat, and the existing test
asserted that broken value because it was written to match the code.

The RE memo's mistake was assuming the data tables sit at fixed file-
relative offsets. They don't. The player code is identical between
files — it relocates cleanly — but the data sections vary in size
per song, so anything that lives *after* the variable-sized data
shifts in absolute terms. The pattern-pointer table is one such
"after" structure.

The fix is to locate the table dynamically. The orderlist-advance
code (just past the end-of-orderlist check) emits a fixed-shape
instruction sequence:

```
48 98 9D F2 <scratch>   ; PHA; TYA; STA $14F2,X
68 A8                    ; PLA; TAY
B9 <lo lo> <lo hi>       ; LDA pattern_ptr_LO_TABLE,Y    ← captured
9D BF <scratch>          ; STA $14BF,X
B9 <hi lo> <hi hi>       ; LDA pattern_ptr_HI_TABLE,Y    ← captured
9D C2 <scratch>          ; STA $14C2,X
```

Scan for the 8-byte prefix, read the two LDA operands, and the table
addresses fall out. Echo_Beat's table lives at `$0A29/$0A2D`, Galax_it_y's
at `$1788/$178E`. Detector now refuses files whose dynamically-found
table is out-of-range, which is the test the v3.5.58 version should
have made in the first place.

The extractor walks each voice's orderlist (3 ptrs at `load+$493/$496`),
dereferences pattern indices via the now-correct ptr table, decodes
pattern byte pairs (duration+octave, note byte). It emits synthesized
NP21-shape streams: `$A0` instrument-set marker per pattern,
note byte (clamped to $00-$6F), duration byte (`$80 | low_4_bits`).
Stream is bounded at 600 bytes per voice (the SF2 editor's slot
budget is 256B and the segmenter wants room for multiple sub-patterns).

The wire-in goes between the Wizax-A / Zetrex-YP redirect block and
the Vibrants V20 short-circuit in `np21_edit_area_builder`. On a
2000 A.D. hit, the synthesized streams plug into `raw_patterns`
directly, bypassing the standard ch_seq_ptr extraction. Everything
downstream (segmentation, orderlist construction, edit-area emission)
is unchanged.

### Galax_it_y: works. Echo_Beat: doesn't, by design.

The wire-in only fires for the standard `np21_edit_area_builder`
path. Galax_it_y (load $1000) takes that path. Echo_Beat (load
$0400) takes the sub-$1000 `low_load_layout` path, which by design
uses `placeholder_edit_area` because the editor-area concept doesn't
fit cleanly into the low-load PRG geometry (header below binary,
handlers above, no room for the standard edit-area layout pinned
to `sid_la + len(c64_data)`).

Extending the 2000 A.D. extractor through `low_load_layout` is
tractable but needs a small refactor — `build_np21_sf2_edit_area`
hardcodes the edit-area base address; parameterizing it would let
`low_load_layout` call the same builder with `EDIT` as the base.
Deferred to keep this push narrowly scoped. Echo_Beat's audio is
unaffected (it routes through the v3.5.35 audio gate's Block 2
native-redirect fallback as documented).

### What "editor view" actually buys

Not edit propagation. The embedded 2000 A.D. binary keeps reading
its own pattern data at runtime; nothing the user types in SF2II's
editor changes what plays. The translator + shadow-buffer pipeline
that gives Wizax-A / Zetrex-YP real F1 edit propagation doesn't
apply here — different byte format, different player code, no
ch_seq_ptr to patch.

What the user *does* get is a tracker-like view of the song's
structure: per-voice orderlists with pattern indices, sub-patterns
showing duration+note pairs in roughly the shape one would expect.
Notes display as opaque byte values (not C-X / D#X) until the
frequency LUT is decoded — deferred per the memory note's "Workable
as read-only display" scoping.

### Per-criterion delta

| Criterion | v3.5.58 → v3.5.59 |
|-----------|--------------------|
| C1 (loads) | 286/286 — unchanged |
| C2 (audio) | 286/286 — unchanged |
| **C3 (editor)** | **+1: Galax_it_y now shows real F1 patterns** |
| C4 (round-trip) | unchanged |

Tests: 1272 passed (+9 from v3.5.58: 3 detector dynamic-scan, 6 extractor).

The bigger lesson worth recording: a memory note marked "detector
buildable" was treated as ground truth, and the resulting detector
shipped with a silently-broken field that only surfaced when the
extractor tried to use it. Next time a memory note describes a
multi-file architecture, the detector tests should hit *every*
listed file and assert the returned addresses are actually in-range
in each file — not just that detection succeeds. The v3.5.58 test
suite did the first part and skipped the second.

---

### v3.5.57 — Audio-verified 100%. All 3 former CONV_FAILs zig64 byte-identical (2026-05-26)

v3.5.55 + v3.5.56 brought the 3 architectural CONV_FAILs to "loads
via argv-load", but loading isn't the same as playing. The natural
next check was zig64 cycle-accurate trace comparison over 300 PAL
frames:

| File | SID writes | SF2 writes (initial) | Verdict |
|---|---|---|---|
| Echo_Beat   | 2007 | 2007 | ✅ byte-identical |
| Magic_Sound | 1091 | 1091 | ✅ byte-identical |
| **Crosswords** | 2572 | **0** | ❌ silent |

Crosswords' SF2 produced 0 register writes. zig64's stderr revealed
the cause: `thread panic: index out of bounds: index 62186, len 62186`.
The Crosswords SF2 file is 62186 bytes which makes its C64 span
$0D7E-$10066 — 102 bytes past $FFFF. zig64's tracer panics on
oversized files even though SF2II's parser handles them fine.

What was making the file so big? The aux chain. For Crosswords with
the high_load_layout's placeholder edit area, the aux chain contained
779 bytes of empty-named TableText entries — labels for cells that
don't exist in the placeholder editor view. Useless padding, and 779
bytes was enough to push the file's C64 end past $FFFF.

The fix is one line: `high_load_layout.build_high_load_sf2` now returns
`skip_aux=True`. The aux chain is omitted, Crosswords' SF2 shrinks to
61407 bytes (C64 end $FCFB, comfortably under 64K). The META trailer
at file-end is still appended (title/author/copyright for SID
round-trip recovery via sf2_to_sid.py).

After fix:

| File | SID writes | SF2 writes | Verdict |
|---|---|---|---|
| Echo_Beat   | 2007 | **2007** | ✅ byte-identical |
| Magic_Sound | 1091 | **1091** | ✅ byte-identical |
| Crosswords  | 2572 | **2572** | ✅ byte-identical |

**ALL 3 former architectural-CONV_FAIL files now produce SF2 outputs
that load in production SF2II AND play byte-identically to the
original SID via zig64 cycle-accurate trace.**

The converter is now functionally complete AND audio-verified. Every
native Laxity SID in the corpus produces a working, audio-correct SF2.

The two-release recovery (v3.5.55 high-load alternate layout +
v3.5.56 zeropage floor) plus this audio-correctness fix (v3.5.57)
closes the loop on what was, just three releases ago, three
"architecturally infeasible" files. The lesson stands: a clean
error message can encode a too-strong constraint that survives
review because nobody re-questions it. The real question for any
"infeasible" rejection is *"infeasible under WHAT assumption?"* —
and the answer is often loadbearing on a layout choice, not a
fundamental property of the format.

### v3.5.56 — Echo_Beat recovered. 100% converter quality (2026-05-26)

The last "architectural CONV_FAIL" wasn't architectural either.

Echo_Beat (sid_la=$0400, 1644B binary) had been categorized as
infeasible since v3.5.20 because the `low_load_layout` floor required
`LOAD_BASE >= $0500`. The stated rationale: putting SF2 header bytes
at $0100-$04FF would conflict with the C64 stack ($0100-$01FF) and
BASIC/KERNAL buffer region ($0200-$04FF) used by the player at
runtime.

**The premise was wrong**, in exactly the same way v3.5.55's premise
was wrong for Crosswords + Magic_Sound.

The key insight: **SF2II's parser reads the SF2 chain from the FILE
on disk BEFORE the C64 emulator starts**. Once parsed, the chain
info lives in SF2II's internal structures. The C64 RAM contents at
the header location only matter pre-emulation. The player can freely
clobber the header bytes once it starts running.

Lowered the floor from $0500 to $0100 (zeropage is a true hard
limit — can't write to $0000-$00FF as a PRG load destination
because the C64 ROM/IO map uses it). Echo_Beat now converts.

Layout for Echo_Beat:

```
$0100-$030D  SF2 header (525B; clobbered by player at runtime)
$030E-$03FF  zero padding
$0400-$0A6B  Echo_Beat binary (1644B at native location)
$0A6C-$0AFF  zero padding
$0B00-$0B0D  INIT/PLAY/STOP handlers
$0B0E-$0B11  #211 scan bait
$0B20-$10A5  SF2 edit area (placeholder, 1414B)
```

PRG file size: 4901 bytes. argv-load: 3/3 PASS.

**The two-release recovery story** (v3.5.55 + v3.5.56) makes a
broader point. The original architectural-error commit at v3.5.34
was protective — converting cryptic struct.pack failures into clean
error messages. Necessary at the time. But the error message baked
in a too-strong constraint:
> "Block 3 column addresses are 16-bit, so the edit area can't
> extend past the C64 address space."

That sentence is TRUE, but the inference "therefore these files are
unsolvable" is FALSE. Two different geometric escape hatches existed:
- For high-load ($F000+): pre-binary 16-bit space wasn't being used
- For low-load ($0400): the stack-collision concern dissolves once
  you realize SF2II doesn't re-read the header from RAM

Both fixes are about ten lines each. Both required noticing that the
original architectural error baked in a too-conservative constraint
that wasn't actually load-bearing.

**Converter quality progression:**

| Date | Quality | Note |
|---|---|---|
| Pre-v3.5.27 | ~77% | C2 audio push begins |
| v3.5.35 | 99% (283/286) | C2 audio push complete; 3 "infeasible" |
| v3.5.54 | 99% | 19-phase refactor preserved quality |
| v3.5.55 | 99.65% (285/286) | High-load layout — Crosswords + Magic_Sound |
| **v3.5.56** | **100% (286/286)** | **Echo_Beat — zero remaining CONV_FAILs** |

The converter is now functionally complete. Every native Laxity SID
in the corpus converts to a working SF2.

### v3.5.55 — high-load alternate layout (Crosswords + Magic_Sound recovered) (2026-05-26)

After the 19-phase refactor closed and validation confirmed 99% true
converter quality (with 3 documented "architectural CONV_FAILs"), the
natural question was: are those 3 ACTUALLY infeasible, or did
v3.5.34's clean-error commit just freeze in an early assumption?

Geometric inspection of the 3 files:

| File | sid_la | size | Post-binary | Pre-binary (after handlers) |
|---|---|---|---|---|
| Echo_Beat | $0400 | 1644B | 62868B | **-2976B** ← truly infeasible |
| Crosswords | $F000 | 3363B | 733B (too small) | **57440B free** |
| Magic_Sound | $F000 | 2613B | 1483B (too small) | **57440B free** |

Crosswords and Magic_Sound have **57KB of free space BEFORE the
binary** — between the SF2 handlers at $0FA0 and the binary at $F000.
The v3.5.34 architectural error checked only post-binary space; it
didn't notice the giant pre-binary gap.

Phase 20 introduces `sidm2/high_load_layout.py` (185 lines) — mirror
image of `low_load_layout`:

```
$0D7E [PRG load + magic]
$0D80 [SF2 header blocks]
$0F90 [INIT/PLAY/STOP handlers]
$0F9E [#211 scan bait — STA $D400,X; RTS]
$1000 [SF2 edit area — placeholder]
...   [zero padding to sid_la]
$F000 [embedded NP21 binary verbatim]
```

Block 3 column addresses point at $1000+ instead of high RAM. SF2II's
parser walks bytes at the configured addresses — it doesn't care
WHERE in 16-bit space those addresses live, only that the bytes
exist. The 16-bit "overflow" concern from v3.5.34 was only true if
you assumed edit area must follow the binary.

Wired into both inject paths (Crosswords routes through laxity-
raw-np21, Magic_Sound through minimal-embed) as a fallback before
raising the original architectural error.

One snag during integration: `universal_211_workaround.py` does a
Digidag-style stub-append on files where its hardcoded `[$1000, $1900)`
scan finds no natural ABX/ABY $D40x writes. For high-load files the
edit area is at $1000+ (zero-filled placeholder) and the bait is at
$0F9E — the scan misses it. The codepath tried to append a stub past
file end and overflowed 16-bit. Fix: add a `stub_addr > 0xFFFF` guard
and bail (the high-load layout has already placed a scan bait and
configured `driver_code_top = $0F90` for SF2II's actual scanner;
nothing to do).

Both Magic_Sound and Crosswords now produce SF2 files that load
cleanly via argv-load. **First-ever conversions for both files.**

The 16 new focused unit tests pin the layout's bytes precisely
(magic, handlers, bait, edit area start, binary embedding at sid_la)
plus the infeasibility cases (sid_la too low, file > 64K).

Echo_Beat remains the only genuinely-infeasible file. Its binary
loads at $0400 — *below* the SF2 wrapper at $0D7E. No PRG layout
can fix that. Recovering it would need either:
1. Multi-segment SF2 files (format doesn't support this today)
2. Putting the SF2 header in ROM-shadow space (conflicts with
   BASIC/KERNAL at $A000+ / $E000+)

Both are out-of-scope refactors of the SF2 format itself.

**Converter quality progression:**

| Date | Quality | Note |
|---|---|---|
| Pre-v3.5.27 | ~77% (220/286 C2 byte-identical) | C2 audio push begins |
| v3.5.35 | 99% (283/286 SF2 outputs) | C2 audio push complete |
| v3.5.54 | 99% | 19-phase refactor preserved quality |
| **v3.5.55** | **99.65%** (285/286) | High-load layout recovers 2 of 3 CONV_FAILs |

1246 tests pass. 17 extracted modules totaling 6649 lines with 193
focused unit tests. `sf2_writer.py` unchanged at 710 lines.

### v3.5.54 — laxity_raw_np21_builder extracted (Phase 19, the hard one) (2026-05-25)

The big one. The "class-bound giant" tagged at Phase 15 as the only
remaining piece in `sf2_writer.py` that genuinely needed class-shaped
refactoring. 940 lines of audio gate orchestration, shadow buffer
setup, ch_seq_ptr patching, translator emission, and Driver-11-format
table emission.

**The surprise** (the same as Phase 11 + 12): the AST `self.*` count
overstated the actual class-bound surface. The method had 16 unique
self refs, but **10 were calls to wrapper methods that already routed
into extracted modules**:

| Self method | Routes to |
|---|---|
| `_build_low_load_sf2` | `low_load_layout.build_low_load_sf2` |
| `_build_np21_sf2_edit_area` | `np21_edit_area_builder.build_np21_sf2_edit_area` |
| `_emit_filter_cutoff_only_routine` | `np21_codegen.emit_filter_cutoff_only_routine` |
| `_emit_filter_split_copy_routine` | `np21_codegen.emit_filter_split_copy_routine` |
| `_emit_instr_column_copy_routine` | `np21_codegen.emit_instr_column_copy_routine` |
| `_emit_instr_copy_routine` | `np21_codegen.emit_instr_copy_routine` |
| `_emit_multipat_translator` | `np21_codegen.emit_multipat_translator` |
| `_emit_pulse_packed_copy_routine` | `np21_codegen.emit_pulse_packed_copy_routine` |
| `_emit_pulse_split_copy_routine` | `np21_codegen.emit_pulse_split_copy_routine` |
| `_emit_wave_split_copy_routine` | `np21_codegen.emit_wave_split_copy_routine` |

The actual class-bound state was just 5 attr writes:
`self.output`, `self._ch_seq_patches`, `self._ch_seq_patch_layout`,
`self._np21_file_off`, `self._wave_copy_jsr_offs`. Those plus
`skip_aux` for the low-load case became the `LaxityRawNp21Result`
dataclass.

After parameterising those + replacing the 10 self-method-call
sites with direct module-function calls, the function became a
pure `(data) → Optional[LaxityRawNp21Result]` builder.

**The transformation bugs** are worth recording because they show
exactly when the C2 reference suite earns its keep:

1. Missing `from . import laxity_raw_np21_builder` in
   `sf2_writer.py`. Caught immediately on the first conversion run.
2. Two `self.` prefix substitutions the body-rewrite regex missed:
   - `if self._build_low_load_sf2(...)` — the regex looked for the
     dedented form (no `self.` prefix) but the body had `self.` still
     attached. Fixed by hand-patching the call site.
   - `self.np21_edit_area_builder.build_np21_sf2_edit_area(...)` —
     half-substitution. The `_build_np21_sf2_edit_area` part got
     replaced with `np21_edit_area_builder.build_np21_sf2_edit_area`,
     but the leading `self.` got left in place, producing the broken
     `self.np21_edit_area_builder.` form. Fixed by removing the
     `self.` prefix in that single line.

Both surfaced on the first C2 regression run. The 14-file byte-
identical suite immediately failed every Laxity-path test with a
specific NameError, pointing at exactly the right line. That's the
test design we've relied on for 18 phases working as expected.

`sf2_writer.py`: 1633 → 710 lines (**-923**). The **largest single
release shrink in the entire decomposition**. Cumulative since
v3.5.27: **5832 → 710 lines (-88%)**.

**The decomposition is functionally complete**. SF2Writer is now
a thin orchestrator (`__init__` + `write()` + wrapper methods) over
16 focused modules totaling 6180 lines. The ratio is **8.7:1**
extracted-to-monolith.

| Module | Lines | Tests |
|---|---|---|
| `laxity_raw_np21_builder` | **1045** | **C2-covered** ⬅ new |
| `driver11_section_injectors` | 994 | C2 |
| `np21_edit_area_builder` | 778 | C2 |
| `np21_codegen` | 617 | 14 |
| `laxity_music_data_injector` | 501 | C2 |
| `sf2_diagnostics` | 401 | 14 |
| `sf2_aux_bodies` | 281 | 27 |
| `driver11_table_helpers` | 235 | 20 |
| `minimal_embed_builder` | 234 | 9 |
| `audio_gate` | 232 | 8 |
| `sf2_parser` | 222 | 18 |
| `low_load_layout` | 184 | 13 |
| `placeholder_edit_area` | 155 | 11 |
| `universal_211_workaround` | 152 | 7 |
| `sf2_template_finder` | 124 | 12 |
| `sf2_metadata_trailer` | 109 | 24 |
| **16 modules total** | **6464** | **177** |

1229 tests pass. All 14 C2 reference files byte-identical.

**The 19-phase decomposition has reduced `sf2_writer.py` by 88%.**
What started as a 5832-line monolith is now a 710-line orchestrator
over 16 focused modules. Every byte of the SF2 output is preserved.
Every architectural concern that could be lifted has been lifted.
The Phase 11 lesson — AST `self.*` unique-ref count is the leading
indicator of refactor feasibility — proved true even on the
"genuinely class-bound" 940-line giant: it was just deeper-wrapped
modular code than the surface count suggested.

### v3.5.53 — driver11 dispatcher + orphan removal (Phase 18) (2026-05-25)

The release that closes the driver11 template path. After Phases
13+17 moved all 11 section inject functions, only three small
pieces of driver11-template-path code remained in `sf2_writer.py`:

1. **The dispatcher** (`_inject_music_data_into_template`, 39 lines):
   parses the SF2 header, pre-allocates the buffer, calls each
   inject function in order. Moved to `driver11_section_injectors`
   as `inject_music_data_into_template(output, data, driver_info)
   → Optional[int]` (returns the load_address on success or None
   on parse failure). The function now does its own SF2 header
   parsing via `sf2_parser.parse_sf2_blocks` instead of calling
   back into `self._parse_sf2_header()`.

2. **The diagnostic** (`_print_extraction_summary`, 25 lines):
   pure read-only debug log. Moved as
   `print_extraction_summary(data) → None`.

3. **The orphan stub** (`_inject_silent_stub`, 26 lines): the
   v3.5.37 NotImplementedError raising stub kept as documentation
   for a failed approach. Removed — zero callers, the rationale
   is preserved in CHANGELOG/STORY/git history at the v3.5.37
   removal commit, and a 7-line recovery-pointer comment remains
   in place.

The dispatcher landing in `driver11_section_injectors.py` means the
entire driver11 template path now lives in one module — 13
functions covering parse + dispatch + 11 section injectors + the
debug summary. `sf2_writer.py` has zero remaining driver11-
template-path code beyond the thin wrapper methods that test files
still call.

`sf2_writer.py`: 1703 → 1633 lines (-70). Cumulative since v3.5.27:
**5832 → 1633 lines (-72%)**. 1229 tests still pass. All 14 C2
reference files byte-identical. `driver11_section_injectors.py`
grew from 873 → 994 lines.

**The 18-phase decomposition tally:**

| Phases | Cumulative shrink | New modules |
|---|---|---|
| v3.5.36–43 (Phases 1–9) | 5832 → 3954 (-32%) | +10 |
| v3.5.44–45 (Phase 10/10b) | 3954 → 3896 (-33%) | +1 |
| v3.5.46–48 (Phases 11–13) | 3896 → 2223 (-62%) | +3 |
| v3.5.49–51 (Phases 14–16) | 2223 → 1954 (-66.5%) | +0 (additions to existing) |
| v3.5.52–53 (Phases 17–18) | **1954 → 1633 (-72%)** | +0 (additions to existing) |

The final 6 releases (Phases 13–18) demonstrate the value of
choosing the right home for an extraction: 5 of those 6 added to
existing modules rather than spawning new ones, because the surface
they covered was a natural extension of an already-extracted theme
(driver11 sections, aux chain, helpers). The pattern of *"complete
an existing module's surface rather than fragment it"* is a useful
counterweight to the tempting "one extraction = one new file" rule.

### v3.5.52 — 7 more inject methods to driver11_section_injectors (Phase 17) (2026-05-25)

A follow-on to Phase 13 (v3.5.48). At v3.5.48 the cluster of 4
driver11-template-path inject methods (orderlists, sequences,
instruments, commands) moved to a new module. The 7 remaining
`_inject_*_table` methods (init, tempo, hr, pulse, filter, arp,
wave) stayed in `sf2_writer.py` because they were still entangled
with `self._addr_to_offset` calls.

Phase 10/10b (v3.5.44-45) had already refactored those 7 methods
to use `find_table` + `write_column_major` helpers — which meant
the `self.driver_info.table_addresses` lookups and column-major
writes were now indirected through pure module functions. With
that surface clean, all 7 had become genuinely `(output, data,
driver_info, load_address) → None` candidates.

Phase 17 batch-moved them in a single scripted pass:

| Method | Lines |
|---|---|
| `_inject_init_table` | 25 |
| `_inject_tempo_table` | 31 |
| `_inject_hr_table` | 21 |
| `_inject_pulse_table` | 33 |
| `_inject_filter_table` | 34 |
| `_inject_arp_table` | 63 |
| `_inject_wave_table` | 79 |
| **Total** | **286** |

`driver11_section_injectors.py` now hosts 11 inject functions (the
4 from Phase 13 + the 7 from Phase 17) and the module-level
`_addr_to_offset` helper. Grew from 575 → 873 lines (+298).

Two new imports needed: `driver11_table_helpers` for the `find_table`
+ `write_column_major` + `update_table_dimensions` adopters, plus
3 sequence extraction symbols (`extract_arpeggio_indices`,
`find_arpeggio_table_in_memory`, `build_sf2_arp_table`) for the
`_inject_arp_table` pattern extraction. The first test run failed
with NameError — the C2 reference suite caught the missing
imports on the first try, exactly like Phase 13's similar case.

No new focused unit tests for this one. The Phase 13 precedent
established that batch-moved methods with no new logic don't need
new tests — the existing `test_sf2_writer.py` exercises each
method via `self._inject_<name>()`, the wrappers preserve the call
surface, and C2 verifies byte output.

`sf2_writer.py`: 1954 → 1703 lines (-251) — biggest shrink since
Phase 12 (v3.5.47). Cumulative since v3.5.27:
**5832 → 1703 lines (-71%)**. 1229 tests still pass. All 14 C2
reference files byte-identical.

**Milestone**: `sf2_writer.py` is now at **29% of its v3.5.27
size**. Over 4000 lines have been lifted into 15 focused modules
across 17 phases. The decomposition has reached a clean structural
state: section injectors live with section injectors,
edit-area builders with edit-area builders, parsers with parsers,
helpers with helpers.

### v3.5.51 — aux chain assembly + injection (Phase 16) (2026-05-25)

Phase 16 finishes the auxiliary-data refactor that v3.5.39 started.
Back then, the two non-trivial body builders (`build_table_text_data`,
`build_description_data`) moved out to `sidm2/sf2_aux_bodies.py`, but
the chain framing and `$0FFB` pointer injection stayed inside
`_inject_auxiliary_data` because they were tightly entangled with
`self.output`.

That was two reasons to make the function not-quite-clean:

1. The TLV chain assembly (the bundled `[3, 2, 1, 4, 5, END]`
   ordering, the per-block `[u8 id][u16 LE param][u16 LE length]`
   framing, the hardcoded reference-bundled bodies for id=1/2/3)
   was still spelled out inline.
2. The `$0FFB` pointer injection — read by SF2II's
   `ParseAuxilaryData` at the constant `driver_info.h:
   AuxilaryDataPointerAddress` — used `self.output[0:2]` to get the
   PRG load address but otherwise was a pure transformation on a
   bytearray + the chain.

Phase 16 lifts both. The chain assembly becomes
`assemble_aux_chain(table_text_body, desc_body) → bytes` with the
ordering and framing handled internally and minimal bodies for
id=1/2/3 stored as module-level constants. The pointer injection
becomes `inject_aux_chain_into_sf2(output, aux_chain) → Optional[int]`
returning the placement address on success or None when the pointer
slot doesn't fit within the buffer (in which case the buffer is
NOT extended, so the caller's idempotency contract holds).

`_inject_auxiliary_data` becomes a 47-line orchestrator: skip-aux
gate at top, path-dependent name extraction, table ID lookup,
then 4 lines of delegation.

The 12 new focused unit tests are useful here because aux-chain
framing is the kind of thing that fails silently — SF2II will load
a chain with wrong TLV lengths but the contents will be garbage,
and there's no good way to test that end-to-end short of opening
the file in SF2II's editor. The dedicated unit tests pin the bytes
precisely: chain starts with block 3, ends with 5 zeros, includes
all 5 blocks (or omits id=5 when desc is None), block-3 body is
`01 00`, the table_text body lands inside the id=4 block at the
expected offset, the `$0FFB` pointer write happens at the right file
offset given the PRG load address.

`sf2_writer.py`: 2010 → 1954 lines (-56) — **under 2000 for the
first time**. Cumulative since v3.5.27: **5832 → 1954 lines (-66.5%)**.
1229 tests pass (+12). All 14 C2 reference files byte-identical.

**Phase 16 is the second "completion" release**: Phase 14 closed the
Block-3 table-operations trinity (lookup/emit/patch); Phase 16 closes
the aux-chain operations trinity (bodies, assembly, injection). Both
times, an existing module gained a third member that completed its
conceptual surface without spawning a new file.

### v3.5.50 — minimal_embed_builder extracted (Phase 15) (2026-05-25)

The 50th release in the v3.5.x series, and the second-largest inject
path lifted out of `sf2_writer.py`. Stage 8 Path A — the minimal-embed
SF2 builder for non-Laxity SIDs (Galway, Hubbard, NP20) — was 181
lines with only 4 unique self refs:

  - `self.data` (read-only, 6 references)
  - `self.output` (mutated to the final result)
  - `self._minimal_path` (set to True)
  - `self._build_low_load_sf2` (one inner method call, itself now
    just a wrapper)

After v3.5.46-48 lifted the bigger functions, Phase 15 took the
last of the well-defined inject paths. The cleanest extraction
shape was to introduce a small **`MinimalEmbedResult`** dataclass
carrying `(sf2_bytes, skip_aux)`, letting the caller drive the
state writes:

```python
result = minimal_embed_builder.build_minimal_embed_sf2(...)
if result is not None:
    self.output = bytearray(result.sf2_bytes)
    if result.skip_aux:
        self._skip_aux = True
```

The function dispatches three paths:
  1. `sid_la < $1000` → delegate to `low_load_layout.build_low_load_sf2`
     (skip_aux=True; binary spans $0FFB).
  2. High-load architectural infeasibility → raise `ConversionError`.
  3. Normal layout → build directly with placeholder edit area + 
     handler stubs + post-binary guard + compatibility trampoline.

Path 1 was previously a `self._build_low_load_sf2(...)` self-method
call. After Phase 4 had already extracted that method to
`low_load_layout.build_low_load_sf2`, the new module calls the
extracted function directly — no more self-method-call dependency.
This shows the value of the earlier extractions: once a function
is out of the class, downstream callers can reach it without
routing back through `self`.

9 focused unit tests pin the dispatch behavior (empty/high-load/
low-load/normal) and the byte-level invariants (handler stubs at
$0F90, trampoline only when sid_la >= $1007, binary embedded
byte-exact at sid_la). The trampoline test is the load-bearing
one — when sid_la == $1000, the binary occupies $1000 itself, so
a trampoline would corrupt the first byte; the test asserts that
sid_la=$1000 preserves the binary's first byte unchanged at $1000.

`sf2_writer.py`: 2165 → 2010 lines (-155) — **under 2100 lines for
the first time**. Cumulative since v3.5.27:
**5832 → 2010 lines (-66%)**. 1217 tests pass (+9). All 14 C2
reference files byte-identical. Fifteen extracted modules now
total 4599 lines with 165 focused unit tests.

**Looking back at the v3.5.46 → v3.5.50 sweep**: five consecutive
releases extracted 738 + 454 + 481 + 58 + 155 = **1886 lines** in
~30 minutes of work each. The Phase 11 lesson (AST `self.*` count
is the leading indicator) kept paying off; everything with low
unique-self-ref counts came out cleanly, and the remaining giant
in the file — `_inject_laxity_raw_np21` at ~940 lines with 16
unique self refs and 5 attr writes — is the only piece that
genuinely needs class-bound state.

### v3.5.49 — update_table_dimensions joined helpers (Phase 14) (2026-05-25)

A smaller follow-on release that adds a third helper to the existing
`sidm2/driver11_table_helpers.py` rather than creating a new module
file. The 65-line `_update_table_definitions` method walks the SF2
Block 3 table-descriptor chain and patches columns + rows fields
in-place for the Instruments (0x80) and Commands (0x81) descriptors.

It was a good fit for the existing helpers module because all three
functions now operate on Block 3 table descriptors with the same
layout assumptions:

```python
# sidm2/driver11_table_helpers.py
find_table(driver_info, name_substring, short_alias=None)
    → Optional[Tuple[addr, columns, rows]]                  # lookup
write_column_major(output, base_offset, entries, columns, rows)
    → None                                                  # emit
update_table_dimensions(output, driver_info)
    → None                                                  # patch
```

That's the "Block 3 table operations" trinity. The module now stands
at 218 lines covering the full surface — read existing descriptors,
write column-major payloads, patch dimensions on existing
descriptors.

The 6 new focused unit tests pin the patch behavior precisely.
The most useful one is `test_missing_address_entry_skips_update` —
it documents that if `driver_info.table_addresses` has no entry for
'Instruments', the descriptor for it is silently skipped (no
exception, no writes). That's the silent invariant that lets the
function be safely called on partially-populated driver_info.

`sf2_writer.py`: 2223 → 2165 lines. Cumulative since v3.5.27:
**5832 → 2165 lines (-63%)**. 1208 tests pass (+6). 14 modules
(unchanged) now total 4365 lines with 156 focused unit tests.

**The Phase 14 lesson**: not every extraction needs a new module
file. A function that fits an existing module's theme can just join
it. The judgment call is whether the new addition genuinely belongs
to the module's concept or whether it would be a stranger living
alongside unrelated functions. Here the trinity of lookup/emit/patch
is cohesive — the new function fits.

### v3.5.48 — driver11 section injectors cluster (Phase 13) (2026-05-25)

The third release in the three-release sweep. After Phase 11
extracted the 761-line NP21 edit-area builder and Phase 12 lifted
the 463-line Laxity music-data injector, the next biggest cluster
was the 4 remaining driver11-template-path section injectors:

| Method | Lines |
|---|---|
| `_inject_instruments` | 243 |
| `_inject_sequences` | 114 |
| `_inject_commands` | 83 |
| `_inject_orderlists` | 61 |
| **Total** | **501** |

These four functions all had the EXACT same shape:

  - Read `self.data` (ExtractedData)
  - Look up table addresses in `self.driver_info.table_addresses`
  - Convert C64 addresses to file offsets via `self._addr_to_offset(addr)`
  - Mutate `self.output` in place

No cross-function state, no other method calls. The natural
extraction shape: a module of pure functions with identical
signatures `(output, data, driver_info, load_address) → None`,
plus the `_addr_to_offset` helper lifted to module level.

New `sidm2/driver11_section_injectors.py` (575 lines):

```python
def inject_orderlists(output, data, driver_info, load_address) -> None: ...
def inject_sequences(output, data, driver_info, load_address) -> None: ...
def inject_instruments(output, data, driver_info, load_address) -> None: ...
def inject_commands(output, data, driver_info, load_address) -> None: ...

def _addr_to_offset(addr: int, load_address: int) -> int:
    return addr - load_address + 2
```

SF2Writer keeps 4 thin wrappers (~5 lines each) preserving the
existing call surface.

One practical hurdle: the extracted functions had inline references
to several sibling-module imports (`find_and_extract_wave_table`,
`extract_command_parameters`, `build_sf2_command_table`,
`transpose_instruments`, `LaxityConverter`). The first regression
run failed with a NameError; adding the imports to the new module
fixed it. The C2 reference suite was the right safety net here — it
caught the missing imports immediately rather than letting them ship.

**The three-release sweep totals**: v3.5.46 (-738L) + v3.5.47 (-454L)
+ v3.5.48 (-481L) = **1673 lines moved in 3 consecutive releases**.
`sf2_writer.py` is now at 2223 lines — **62% smaller than at v3.5.27**.
Half the original file has been lifted out in 3 releases.

| Metric | v3.5.46 | v3.5.47 | v3.5.48 |
|---|---|---|---|
| sf2_writer.py | 3158 | 2704 | **2223** |
| Cumulative shrink | -46% | -54% | **-62%** |
| Extracted modules | 12 | 13 | **14** |
| Total extracted code | 3227L | 3728L | **4303L** |

1202 tests pass throughout. All 14 C2 reference files byte-identical
at every step.

### v3.5.47 — laxity_music_data_injector extracted (Phase 12) (2026-05-25)

The Phase 11 lesson (AST `self.*` count is the leading indicator) had
an immediate payoff. After v3.5.46 pulled out the 761-line
`_build_np21_sf2_edit_area` whose AST scan revealed only 9 self refs,
the next biggest method in `sf2_writer.py` was the 463-line
`_inject_laxity_music_data`. AST scan: 92 `self.*` references — but
only **TWO unique ones**, `self.output` (67 refs, mutated) and
`self.data` (25 refs, read-only). No method calls. No other state.

That's the same shape as Phase 11 — high reference count is fine when
the references are all to ONE mutating-target and ONE read-only source.
Pass `output: bytearray` and `data` as parameters; the function
becomes pure.

The function is itself complex — it patches the Laxity driver
template (v1.6, `sf2driver_laxity_00.prg`) with INIT dispatch fix
at $0E00, 40 hardcoded pointer patches throughout the relocated
player, orderlist injection at $1900, sequences after, tables —
but every line of that complexity is **local** to the function. The
600 lines of patch logic don't reach out into other parts of the
writer's state.

New `sidm2/laxity_music_data_injector.py` (501 lines):

```python
def inject_laxity_music_data(output: bytearray, data) -> None:
    """Inject music data into the Laxity driver template (native format)."""
    # ... 463 lines of hardcoded patches ...
```

`sf2_writer.py:_inject_laxity_music_data` becomes an 8-line wrapper.

Same test-coverage decision as Phase 11: no new focused unit tests.
The C2 reference suite is the regression guard; building synthetic
fixtures to exercise 40 hardcoded pointer patches would be
months-long fixture work. The C2 audio comparison verifies every
byte of the output.

**A milestone hit**: `sf2_writer.py` is now at 2704 lines, and the
13 extracted modules total 3728 lines. **More code lives in extracted
modules than in `sf2_writer.py` itself** for the first time. The
architectural separation between "writer orchestration" and "pure
builders / encoders / validators / utilities" is structurally
complete for the easy-to-medium difficulty targets.

`sf2_writer.py`: 3158 → 2704 lines (-454). Cumulative since v3.5.27:
**5832 → 2704 lines (-54%)** — more than half the file is gone.
1202 tests still pass. All 14 C2 reference files byte-identical.

**The Phase 11-12 pattern**: two consecutive releases extracting
761 + 463 = 1224 lines, neither requiring new focused unit tests
because the C2 reference suite was already the right safety net.
Both functions were *intrinsically pure*, just trapped inside a
class. The cumulative effect since v3.5.27 — 5832 → 2704, -54% —
demonstrates that you can lift huge amounts of code out of a
monolith without writing new tests, **provided you have a
trustworthy end-to-end suite** as the regression guard.

### v3.5.46 — np21_edit_area_builder extracted (Phase 11) (2026-05-25)

**The biggest single extraction of the decomposition project.** A
761-line method, lifted out in one release, with zero behavior change
and zero new tests required.

The setup: after 10 phases of pulling small-to-medium concerns out of
`sf2_writer.py`, the remaining biggest method was
`_build_np21_sf2_edit_area`. At 761 lines it looked like an unmovable
monolith — the function that builds the entire SF2 edit-data area for
the raw-NP21 path, encoding 6 stages of work (ch_seq_ptr extraction,
pattern segmentation, byte-format conversion, orderlist building,
per-variant table emission, address layout).

The surprise: an AST scan looking for `self.*` references in the
function counted **9 total references**, all reads of
`self.data.header` (3 distinct fields: `copyright`, `init_address`,
`play_address`). No writes, no calls to other methods, no peeks at
`self.output`. The method was already 99.9% a pure function — it
just hadn't been parameterised.

Phase 11 extraction shape: pass the 3 header fields as keyword
arguments. The function becomes:

```python
def build_np21_sf2_edit_area(
    c64_data: bytes,
    sid_la: int,
    *,
    psid_copyright: str = '',
    init_addr: Optional[int] = None,
    play_addr: Optional[int] = None,
) -> Tuple[dict, bytes, List[int], List[Tuple], List[int]]:
```

`sf2_writer.py:_build_np21_sf2_edit_area` becomes a 22-line wrapper
that pulls the 3 header fields and forwards.

The extraction itself was mechanical but had two practical hurdles:

1. **761 lines is too big to copy-paste safely** with the Edit tool.
   The script-based approach: read the function via AST, transform the
   3 `self.data.header.*` references into parameter accesses, dedent
   from class-method indent (8 spaces) to module-function indent (4
   spaces), write to a new file. The script ran on first try; the only
   complication was getting the `init_addr` parameter naming to not
   collide with a local variable of the same name (renamed local to
   `_init`).

2. **No focused unit tests this time.** The function builds 6 stages
   of inter-dependent state — synthesizing a test fixture would mean
   either crafting a synthetic NP21 binary (weeks of work to exercise
   the per-variant detectors) or pulling in real Stinsen-class
   binaries (which then makes the tests fragile to changes in
   external detector modules). The decision: rely on the C2 reference
   suite as the regression guard. Every Laxity SF2 conversion routes
   through this function; the 14 byte-identical reference files
   verify every code path that matters. Adding equivalent focused
   tests would be a months-long fixture-building project for a
   purely structural refactor with zero behavior change.

`sf2_writer.py`: 3896 → 3158 lines. **A single release shrank the
file by 738 lines.** Cumulative since v3.5.27:
**5832 → 3158 lines (-46%)**. 1202 tests still pass. All 14 C2
reference files byte-identical. Twelve extracted modules now total
3227 lines.

**What remains in `sf2_writer.py`** is harder: the 940-line
`_inject_laxity_raw_np21` (consumes the edit-area builder's output
and orchestrates shadow-buffer pre-fill + ch_seq_ptr patching +
translator emission + audio gate), the 463-line
`_inject_laxity_music_data`, the 243-line `_inject_instruments`, and
the 166-line `write()` orchestrator. Those are entangled with
`self.output` mutation and inter-method shared state — they'd need
class-shaped refactors with proper test fixtures, not the
pure-function lift that worked here.

**The Phase 11 lesson**: the AST `self.*` count is the leading
indicator of refactor feasibility. A 761-line function with 9
references — all reads of the same dataclass field — is genuinely
0.9% bound to the writer's state. The 940-line `_inject_laxity_raw_np21`,
by contrast, has 5 `self.*` writes and dozens of reads scattered
through 940 lines. Function size ≠ extraction risk.

### v3.5.45 — Phase 10 helpers fully adopted (2026-05-25)

A short follow-up release that demonstrates the compounding value
of horizontal helpers. v3.5.44 introduced `find_table` and
`write_column_major` and refactored two methods (Filter, Pulse) to
use them — that saved 13 lines.

v3.5.45 takes the remaining four candidates (`_inject_init_table`,
`_inject_tempo_table`, `_inject_hr_table`, `_inject_arp_table`)
plus a cleanup pass on the v3.5.44 Pulse adopter (the previous
release had left the old per-method lookup loop in place as a
"kept for backward-compat" comment — now removed cleanly).

Each adoption shrinks the inject method's table-lookup block from
~8 lines to 4 lines. The biggest single win is `_inject_hr_table`,
which previously had two MANUAL column loops (one writing
`frames` to col 0, one writing `wave` to col 1). The new code is
one `write_column_major` call.

The 7th candidate, `_inject_wave_table`, was left alone — it uses
an exact-key dict lookup (`'Wave' not in driver_info.table_addresses`)
that's already 2 lines. Adopting `find_table` would add a line, not
remove one. The pattern only pays off where the legacy code did a
substring-match-loop.

**The compounding effect**: from 2 adopters in v3.5.44 to 6 in
v3.5.45, the cumulative line save is 58 (13 + 45) with zero behavior
change and zero new tests required. Each additional adoption is
essentially free — the helpers were already byte-tested in v3.5.44.

`sf2_writer.py`: 3941 → 3896 lines. Biggest single-release shrink
since Phase 4 (`low_load_layout`). Cumulative since v3.5.27:
**5832 → 3896 lines (-33%)**. 1202 tests still pass. All 14 C2
reference files byte-identical.

**The Phase 10/10b lesson**: vertical extractions (an algorithm to
its own module) and horizontal helpers (shared utilities for
in-place patterns) have different value curves. A vertical
extraction pays its full price up-front (you write the module,
its tests, and update the call site). A horizontal helper pays
upfront for the helper + tests but gets dividends with every
subsequent adoption — and you can ship the helper before you
adopt everywhere, letting subsequent low-risk adoptions land
incrementally.

### v3.5.44 — driver11 table helpers shared (Phase 10) (2026-05-25)

The driver11 template path has ~7 inject methods that all build
Block 3 column tables from extracted Laxity data — `Pulse`, `Filter`,
`Wave`, `Arp`, `Tempo`, `Init`, `HR`, plus `Commands`. They share two
repeated patterns:

1. **Find table by name substring**: walk
   `driver_info.table_addresses`, return on a `'Filter' in name` or
   `name == 'F'` match. ~8 lines per method.
2. **Write column-major**: iterate columns then rows, writing
   `entries[i][col]` to `base_offset + col * rows + i`, bounds-checking
   both buffer length and per-entry tuple length. ~7 lines per method.

That's ~15 duplicated lines × 7 methods = ~105 lines of pure pattern
repetition.

Phase 10 lifts both into `sidm2/driver11_table_helpers.py` (98 lines):

  - `find_table(driver_info, name_substring, short_alias=None)
       → Optional[(addr, columns, rows)]`
  - `write_column_major(output, base_offset, entries, columns, rows,
                        max_columns=4) → None`

In this release, `_inject_filter_table` and `_inject_pulse_table`
adopt them. The other 5 methods are left for future incremental
refactors — each adoption is a ~10-line save with no risk because
the helpers are byte-equivalent to the inline loops they replace,
and they have dedicated tests.

The 14 tests pin both helpers' contracts precisely. The most
load-bearing one is `test_short_entry_tuple_skips_columns` — it
documents that if a table descriptor declares 6 columns but the
extracted entries are only 4-tuples, only 4 columns are written
and cols 4-5 are untouched. That's the silent invariant that lets
us run the same `write_column_major` against tables with different
column counts.

`sf2_writer.py`: 3954 → 3941 lines (-13). The win compounds as
more inject methods adopt the helpers. Cumulative since v3.5.27:
**5832 → 3941 lines (-32%)**. 1202 tests pass (+14). All 14 C2
reference files byte-identical. Eleven extracted modules now total
2449 lines with 150 focused unit tests.

**The Phase 10 lesson**: not every refactor is a vertical
extraction. Sometimes the win is a horizontal helper that absorbs
a pattern repeated across multiple in-place methods. Each adoption
is small (~10 lines), but the cumulative effect across 7 methods
+ the dedicated test coverage of the previously-untested duplicated
logic makes it a meaningful structural improvement.

### v3.5.43 — file-finders extracted (Phase 9) (2026-05-25)

The smallest extraction of the session, and it crosses a symbolic
milestone: `sf2_writer.py` falls **under 4000 lines** for the first
time. The biggest win is structural — the converter is no longer
opening files via methods that live alongside the writer logic.

Two pure read-only filesystem-lookup utilities:

  - `_find_template(driver_type)` — dispatches a per-driver-type
    search list. `driver11` prefers the bundled SF2 example
    (correct table addresses) and falls back to .prg drivers
    (wrong addresses but they parse). The `d11` and `11` aliases
    map to `driver11`. `np20` and `laxity` have their own lists.
  - `_find_driver()` — locates the v1.6 driver (sf2driver16_01.prg).

Both go to `sidm2/sf2_template_finder.py` (124 lines).

The 12 tests use `unittest.mock.patch('os.path.exists')` to make
path-ordering invariants deterministic. The load-bearing one is
"SF2 examples are checked before .prg drivers" — both file types
parse, but only the .sf2 example files have correct table
addresses, so we always want them first. A future refactor
accidentally swapping the order would still parse and load, but
silently use wrong addresses. The dedicated test catches that
class of regression before it ships.

`sf2_writer.py`: 4009 → 3954 lines. **First time under 4000.**
Cumulative since v3.5.27: 5832 → 3954 lines (**-32%**). 1188 tests
pass (+12). All 14 C2 reference files byte-identical. Ten
extracted modules now total 2351 lines with 136 focused unit
tests.

### v3.5.42 — placeholder edit-area deduplicated (Phase 8) (2026-05-25)

The Phase 4 (`low_load_layout`) and Phase 7 (`metadata_trailer`)
extractions each pulled out a self-contained concept. Phase 8 is
different: it finds a **40-line block of code that was duplicated
in two of the already-extracted modules** and lifts it into a third
shared module.

When `low_load_layout` was extracted in v3.5.38, the placeholder
edit-area builder (OL ptr tables + seq ptr tables + 3 placeholder
orderlists + 1 sequence + F1-F5 + Arp/Tempo/HR/Init tables) came
along for the ride because it was tightly woven into the low-load
flow. But the exact same 40-line block also lived in
`sf2_writer._inject_player_raw_minimal` — the minimal-embed path
for non-Laxity SIDs. Same construction, same field assignments
on SF2HeaderGenerator, same byte layout.

The pattern was hiding in plain sight: any code path that needs an
empty editor view (because the source SID's player format can't be
decoded into SIDM2's F1-F5 representation) emits the same byte
sequence. There's only ONE shape of "empty editor view that SF2II
loads without crashing" — the 3-tracks × 1-pattern placeholder
verified against the Stinsen reference back at v3.4.1.

Phase 8 lifts it into `sidm2/placeholder_edit_area.py` (155 lines):

```python
def build_placeholder_edit_area(
    sf2_data_base: int,
    gen: SF2HeaderGenerator,
) -> Tuple[bytes, dict]:
    """Build the empty-editor-view edit area; mutate gen with addrs."""
```

Both call sites become ~25 lines each. `low_load_layout.py` shrinks
from 211 to 184 lines; `sf2_writer.py:_inject_player_raw_minimal`
loses ~80 lines.

Tests pin the exact byte layout (total 1414 bytes), the orderlist
signature (`$A0 $00 $FE $FF×253` per voice), the all-0x7F
end-of-sequence sequence, the zero-fill of the F1-F5 + editor-only
tables, and the gen field population order (instr < wave < pulse
< filter < arp < tempo < hr < init).

Also in this phase: the orphaned `SF2_FILE_ID` / `BLOCK_*` class
constants on `SF2Writer` (left behind when Phase 6 extracted the
parser) are deleted. Zero callers. The parser module is the single
source of truth now.

`sf2_writer.py`: 4093 → 4009 lines. Cumulative since v3.5.27:
**5832 → 4009 lines (-31%)**. 1176 tests pass (+11). All 14 C2
reference files byte-identical, including all 6 recovered low-load
files (Annelouise, Axel_F, Beat_the_Shit_3, Crap_5, Force_Tune,
Shit). Nine extracted modules now total 2254 lines with 124 focused
unit tests.

**The Phase 8 lesson**: refactoring isn't a one-pass operation.
After lifting a function into a module, look at whether that
function still duplicates work that lives in another module — the
deduplication that wasn't possible before becomes obvious once
both sides are out of the monolith.

### v3.5.41 — META trailer encode/decode unified (Phase 7) (2026-05-25)

A different kind of refactor — not about shrinking `sf2_writer.py`,
but about consolidating a format contract that previously spanned
two files with two independent implementations.

Since v3.5.17, SIDM2 has appended a small trailer past the SF2
content so SID → SF2 → SID round-trips preserve all three PSID
metadata fields:

    [b"META"] [pascal title] [pascal author] [pascal copyright]

Where each pascal string is `[u8 length][length bytes latin-1]`.
SF2II ignores the trailer because its C64 memory landing spot lies
past the SF2 file's natural end and isn't referenced by any of its
handlers. The encoder lived in `sf2_writer.py:_append_metadata_trailer`;
the decoder lived in `scripts/sf2_to_sid.py:_extract_metadata`. Same
format spec, two implementations, **no shared test**. One typo away
from breaking metadata round-trip silently — the C2 reference tests
verify SF2 byte-output but don't exercise SF2→SID at all.

Phase 7 unifies them in `sidm2/sf2_metadata_trailer.py` (109 lines)
exposing:

  - `encode_metadata_trailer(title, author, copyright) → bytes`
  - `decode_metadata_trailer(sf2_bytes) → Optional[Tuple[str, str, str]]`

Both writers now thin-wrap the module. The decoder gracefully
returns `None` on missing/truncated/malformed trailers instead of
raising — this matches the original behavior (`logger.debug` then
fall through) and keeps the caller simple.

The high-value addition is the **24 focused unit tests** that span
both halves of the contract:

- Encoder edge cases: whitespace strip, latin-1 with non-ASCII,
  unencodable chars replaced with `?`, 400-char string truncated
  to 255 (the pascal-length cap).
- Decoder edge cases: empty input, no magic, truncated string,
  missing third string, rightmost-wins when multiple `b"META"`
  appear, tail-window enforcement (trailer >2KB from end ignored).
- **Round-trip symmetry** (5 tests): `decode(encode(x)) == x`
  modulo the documented strip + truncation. This is the load-
  bearing property — it catches drift between the two halves
  before it can break a real round-trip in production.

`sf2_writer.py` stays at 4097 lines (the wrapper is the same size
as the original method, so no shrink in that file specifically).
But `scripts/sf2_to_sid.py` lost ~25 lines, and the format spec
that was duplicated across both files now lives in exactly one
place. 1165 tests pass (+24). All 14 C2 reference files
byte-identical. Eight extracted modules now total 2099 lines with
113 focused unit tests.

The lesson: refactoring isn't only about cutting lines from a
monolith. Sometimes it's about pulling apart a format contract
that's been silently duplicated and writing the round-trip test
that should always have existed.

### v3.5.40 — SF2 block-parsing extracted (Phase 6) (2026-05-25)

SF2 files are a TLV block chain terminated by `0xFF`. To convert a
template-style SF2 (the "Driver 11 Test - Arpeggio.sf2" reference,
say, or another SIDM2-produced SF2 being reopened), the converter
needs to parse the existing block chain to learn the driver name,
the music-data layout, and the table addresses for instruments /
commands / wave / pulse / filter / arp / tempo. That parsing logic
lived as four methods inside `sf2_writer.py` — about 191 lines that
were structurally read-only against the SF2 file (reads
`self.output`, writes `self.driver_info`) but tangled with the
writer's class because they used `self.SF2_FILE_ID` / `self.BLOCK_*`
constants and `self.driver_info.*` field accesses.

Phase 6 lifts them into `sidm2/sf2_parser.py` (222 lines):

  - `parse_sf2_blocks(sf2_bytes, driver_info) → Optional[int]`
    Top-level walk. Returns load address on success, `None` on
    invalid magic or empty file.
  - `parse_descriptor_block(data, driver_info)` — Block 1
  - `parse_music_data_block(data, driver_info)` — Block 5
  - `parse_tables_block(data, driver_info)` — Block 3

All four are best-effort: malformed bodies silently skip rather than
raise. This is intentional — SF2 files in the wild may have garbage
in unreachable bytes, and the parser shouldn't refuse to load just
because some `text_field_size` byte looks wrong.

The format constants now live at module level:

```python
SF2_FILE_ID = 0x1337
BLOCK_DESCRIPTOR = 1
BLOCK_DRIVER_TABLES = 3
BLOCK_MUSIC_DATA = 5
BLOCK_END = 0xFF
```

These pin SF2II's parser contract — any drift would break F10-load.
A dedicated test (`TestConstants.test_constants_match_sf2ii`) is now
the canary.

SF2Writer keeps thin wrapper methods preserving the original
`True/False` signatures for backwards-compat with the 5 legacy
tests in `pyscript/test_sf2_writer.py`.

18 new focused unit tests in `pyscript/test_sf2_parser.py` exercise
the walk dispatch, terminator handling (a ghost block past `0xFF`
must NOT be parsed), first-letter aliasing for all 5 letter tables
(W → Wave, P → Pulse, F → Filter, A → Arp, T → Tempo), and the
defaults-preserved-on-undersized-body invariant.

`sf2_writer.py`: 4214 → 4097 lines. Cumulative since v3.5.27:
**5832 → 4097 lines (-30%)** — we cracked the 4000-line floor.
1141 tests pass (+18). All 14 C2 reference files byte-identical;
legacy parser tests still pass via wrappers. Seven extracted modules
now total 1990 lines with 89 focused unit tests.

### v3.5.39 — aux-body builders extracted (Phase 5) (2026-05-25)

The auxiliary-data chain is one of the trickier corners of the SF2
format: a TLV-encoded sidecar (located via a HARDCODED pointer at
C64 `$0FFB`) carrying up to 5 block types — editor preferences,
play markers, hardware prefs, table text (instrument + command
names), and song description. SF2II's parser walks each body's
bytes literally; any encoding drift past the expected boundaries
either silently breaks F10-load or corrupts the heap.

Two of the bodies (id=4 TableText and id=5 Songs) had small but
nontrivial encoders inside `sf2_writer.py` — pascal strings, `u16`
LE text counts, `u32` LE table IDs, padding rules to match the
Block 3 row counts. Both functions were already pure (no `self.*`
state writes) but bundled with the inject orchestrator.

Phase 5 lifts them into `sidm2/sf2_aux_bodies.py` (155 lines)
exposing:

  - `build_description_data(song_name) → bytes`
  - `build_table_text_data(instrument_names, command_names,
                            instr_table_id, cmd_table_id) → bytes`

The SF2Writer wrappers are 8 lines each — pull the song name from
`self.data.header.name`, return `bytearray` for backwards-compat
with the existing `_inject_auxiliary_data` orchestration.

The format rationale (decoded from SF2II's
`auxilary_data_*.cpp:RestoreFromSaveData`) moves into the module
docstring, so future readers can grep for "TableText" or
"AuxilaryDataSongs" and find the exact byte layout in one place.

15 new focused unit tests — these encoders are perfect candidates
because the byte output is precisely-defined and small drifts have
catastrophic downstream effects. Tests pin:
  - default fallbacks for missing/empty/whitespace song names
  - 16-char Songs truncation, 255-byte TableText truncation
  - latin-1 encoding behavior (non-ASCII chars preserved,
    unencodable chars → '?')
  - the critical "excess names truncated to row count" invariant
    that prevents heap corruption (if the parser sees text_count
    > actual texts, it walks past the buffer)
  - the four module constants that pin SF2II's Block 3 layout

`sf2_writer.py`: 4284 → 4214 lines. Cumulative since v3.5.27:
**5832 → 4214 lines (-28%)**. 1123 tests pass (+15). All 14 C2
reference files byte-identical. Six extracted modules now total
1768 lines with 71 focused unit tests.

### v3.5.38 — low-load layout extracted (Phase 4) (2026-05-25)

The v3.5.36 refactor stopped at four modules because that was where
the easy extractions clustered: pure-function 6502 emitters,
self-contained audio gate, single-function #211 workaround, observer-
only diagnostics. v3.5.38 takes the next candidate from
`sf2_writer.py`: **`_build_low_load_sf2`**, the 148-line method that
handles the alternate PRG layout for binaries that load below $1000.

This one's interesting because the algorithm is genuinely tricky —
the function has to thread between zeropage, stack, BASIC/KERNAL
buffers, screen RAM, the embedded binary's own scratch space, and
SF2II's HARDCODED $0FFB aux-pointer address. All of that knowledge
was inline-commented in `sf2_writer.py`, which made the rest of the
file harder to read without giving the low-load logic the prominence
it deserved.

Extraction strategy: the function has only two `self.*` writes
(`self.output`, `self._skip_aux`). Move it to a new module
`sidm2/low_load_layout.py` as a pure function returning
`Optional[(bytes, skip_aux)]`; the wrapper in SF2Writer copies the
result into `self.output` and `self._skip_aux`. The module docstring
captures the architecture rationale (~50 lines of "why" up front
instead of scattered comments) so future readers can understand the
constraints without spelunking.

13 focused unit tests in `test_low_load_layout.py` exercise the
function with synthetic inputs: structure assertions (load_base,
magic, embedded binary, handler stubs, #211 scan bait), infeasibility
cases ($0400 below floor, oversized binary), parametric layouts for
$0F00 / $0900 / $0800. Tighter than the C2 end-to-end tests, which
verify byte-identical output but only on the 14 reference files.

`sf2_writer.py`: 4408 → 4284 lines. Cumulative since v3.5.27:
**5832 → 4284 lines (-26%)**. 1108 tests pass (+13). All 14 C2
reference files byte-identical, including all 6 recovered low-load
files (Annelouise, Axel_F, Beat_the_Shit_3, Crap_5, Force_Tune,
Shit). Five extracted modules now total 1613 lines with 56 focused
unit tests — the structural high cards are all lifted out of the
monolith.

### v3.5.37 — dead-code cleanup post-refactor (2026-05-24)

Housekeeping. After the v3.5.36 four-module extraction, AST analysis
of the SF2Writer class surfaced 8 unused private methods. 4 were
safely removable without touching tests or external callers:

- `_try_block2_native_redirect` + `_restore_block2` (5 lines combined) —
  wrappers around `audio_gate` functions never called by anything,
  because `audio_gate` calls the module functions directly.
- `_emit_wave_copy_routine` (4 lines) — wrapper around
  `np21_codegen.emit_wave_copy_routine` with zero callers anywhere.
- `_inject_silent_stub` (116 lines) — the 2026-03 "ATTEMPTED, NOT
  WORKING" silent-stub fallback. Body removed; replaced with a
  `NotImplementedError` stub + docstring pointer to git history.
  Recoverable from the v3.5.37 commit's parent if anyone ever wants to
  revisit it (Action_Biker test cases included).

The remaining 4 unused wrappers
(`_emit_pulse_copy_routine`, `_emit_sf2_to_np21_translator`,
`_log_block3_structure`, `_log_block5_structure`) stay because legacy
test files exercise them as wrapper-delegation contracts. Migrating
those tests would gain nothing (the module functions already have
dedicated tests).

Also added the focused unit-test coverage missing from v3.5.36:
22 new tests in `test_audio_gate.py` (8) and `test_sf2_diagnostics.py`
(14). All four extracted modules now have dedicated unit-test
coverage — **43 tests on 1402 extracted lines**.

| Module | Lines | Tests |
|---|---|---|
| np21_codegen.py | 617 | 14 |
| audio_gate.py | 232 | 8 |
| universal_211_workaround.py | 152 | 7 |
| sf2_diagnostics.py | 401 | 14 |

`sf2_writer.py`: 4510 → 4408 lines. Cumulative since the C2 push
started at v3.5.27: **5832 → 4408 lines (-24%)**. 1095 tests pass
(unchanged — the dead code had zero coverage, the new tests are
additive). Zero behavior change.

### v3.5.36 — sf2_writer.py refactor (Phase 1-3) (2026-05-23)

After the C2 push reached 99% byte-identical and the architecture
stabilized, the 5832-line `sf2_writer.py` became the structural
liability. It accreted ~3000 lines over the C2 work: gates, codegen
emitters, diagnostics, four inject paths, music data builder. Each
addition was correct in isolation; the file as a whole was a wall of
text where you couldn't tell where one concern ended and another
began.

The refactor strategy: **extract pure functions first, then thin
delegating wrappers stay behind to preserve `self.x_y_z()` call sites.**
Each extraction step is verified byte-identical against the 14-file
C2 reference regression suite. If any C2 file's SF2 output changes
by one byte, the extraction is wrong — revert and try again.

Four modules came out cleanly:

- **`sidm2/np21_codegen.py`** (617 lines): 11 pure 6502 emitters
  (`emit_sf2_to_np21_translator`, `emit_wave_copy_routine`,
  `emit_wave_split_copy_routine`, etc.). All 11 had ZERO `self.*`
  references — they read pure parameter inputs and emit bytes. Moved
  directly as module functions.

- **`sidm2/audio_gate.py`** (232 lines): the post-build zig64 gate.
  `run_post_build_audio_gate` orchestrates the 4-step progressive
  revert (ch_seq_ptr revert → wave-copy NOP → both → Block 2 native
  redirect). `try_block2_native_redirect` / `restore_block2` operate
  on the SF2 buffer.

- **`sidm2/universal_211_workaround.py`** (152 lines): the SF2II #211
  protection stamp. Two paths: stamp `9D 00 D4` at $1006 (trampoline
  layouts) or append a stub + patch Block 1 (Digidag fallback).

- **`sidm2/sf2_diagnostics.py`** (401 lines): logging + post-write
  validation. `log_sf2_structure`, `log_block3_structure`,
  `log_block5_structure`, `validate_sf2_file`.

`sf2_writer.py`: 5832 → 4510 lines (-23% in one push). 1052 → 1073
tests pass (21 new focused unit tests on the codegen + #211 modules
followed up immediately so a future emitter regression wouldn't have
to wait for the slower C2 end-to-end suite to surface it). All 14 C2
reference files byte-identical at every extraction step. The
remaining file isn't beautiful, but the structural high cards
(codegen, gates, diagnostics) are now lifted into testable units.

### v3.5.35 — Block 2 native-redirect (Exorcist_preview recovered) (2026-05-23)

The last non-architectural C2 audio residual. Exorcist_preview's
embedded binary at `$9000+` is byte-identical to the SID, but tracing
the SF2 via Block 2's declared `$0F90/$0F94` (wrapper handlers) gives
50 extra register writes per 60 frames — wrapper-init cycle drift,
unfixable through any patch revert. **But** tracing the SF2 at native
`$9000/$9006` directly gives 0 diffs.

Added the 4th gate fallback: **rewrite Block 2's declared init/play
addresses to the PSID-native entry points**. zig64 and SF2II both read
Block 2 init/play to invoke the player; pointing them at native
bypasses the wrapper layer entirely. Tradeoff: F1-F5 edit propagation
goes through the translator at `$0F9E` (called via `$0F94`), so
redirecting Block 2 means edits won't reach the player. For files that
already couldn't propagate (ch_seq_ptr was skipped), this is a clean
audio win with no editor regression.

**Exorcist_preview: 916-diff → byte-identical 1612 writes.** C2
corpus 282/286 → 283/286 (99%). **Every file the converter produces
a SF2 for now has byte-identical audio.** Zero non-architectural
audio residuals. Cost: ~30ms extra per file when the gate's
trace-revert chain reaches step 4 (rare; only Exorcist_preview-class
wrapper-init issues).

### v3.5.34 — clean architectural-limit errors for high-load CONV_FAIL files (2026-05-23)

Diagnostics polish. Crosswords (load=`$F000`, 3363B) and Magic_Sound
(load=`$F000`, 2613B) were failing with a cryptic
`struct.pack 'H' format requires 0 <= number <= 65535` deep in
`sf2_header_generator.create_tables_block()`. Root cause: when the
binary loads near `$F000` and is 2-3KB, only ~700 bytes remain to
`$FFFF` — not enough for the SF2 edit area (orderlists + sequences +
F2/F3/F4/F5 tables + shadow buffer; minimum ~$800 bytes; Block 3
column addresses are 16-bit). Added a guard at the top of both
`_inject_laxity_raw_np21` and `_inject_player_raw_minimal`: when
`sid_la + len(c64_data) + 0x800 > 0x10000`, raise a clean
`ConversionError` with `stage="...inject (high-load)"` and a
human-readable reason. Echo_Beat had the symmetric low-load
architectural error since v3.5.25; now all three CONV_FAIL files are
documented architectural infeasibility, not bugs. C2 corpus
unchanged; failure mode is now diagnostic. 1032 tests still pass.

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
