# SF2 Driver Binary / Descriptor Format — Stage B0 findings

**Created:** 2026-05-29 | **For:** `GALWAY_SF2_DRIVER_PLAN.md` Stage B (native
Galway driver). Source of truth: SID Factory II C++
(`~/Downloads/sidfactory2-master/.../editor/driver/driver_info.{h,cpp}`,
`driver_architecture_sidfactory2.*`).

## Headline feasibility result

**SF2II is generic over the driver descriptor — authoring a new driver needs NO
SF2II source change.** The editor parses a descriptor embedded in the driver
`.prg` (header blocks, serialized into the `.sf2`) and drives *any* binary that:
1. uses descriptor **type `0x00`** (`DriverArchitectureSidFactory2`),
2. exposes init / stop / update(play) entry points at declared addresses,
3. maintains the **playback-state variables** the editor reads (below) at
   declared addresses, and
4. reads its music data + editable tables from declared addresses.

So a native Galway driver is a pure 6502 + descriptor artifact loadable by stock
SF2II. The cost is the 6502 driver itself (multi-week), not editor changes.

## Descriptor structure (`DriverInfo`, driver_info.h)

File ID `0x1337`; aux-data pointer at `$0FFB`. Header block IDs (Block N):
1=Descriptor, 2=DriverCommon, 3=Tables, 4=InstrumentDescriptor, 5=MusicData,
6=ColorRules, 7=Insert/Delete, 8=Action, 9=InstrumentDataDescriptor, 255=end.

**Descriptor (Block 1):** `m_DriverType` (0x00=SF2 arch), `m_DriverSize`,
`m_DriverName`, `m_DriverCodeTop`, `m_DriverCodeSize`, version major/minor/rev.

**DriverCommon (Block 2)** — the driver↔editor contract:
- `m_InitAddress`, `m_StopAddress`, `m_UpdateAddress` (= play/tick).
- `m_SIDChannelOffsetAddress`.
- Playback-state the editor reads to draw the cursor / play markers:
  `m_DriverStateAddress`, `m_TickCounterAddress`, `m_OrderListIndexAddress`,
  `m_SequenceIndexAddress`, `m_SequenceInUseAddress`, `m_CurrentSequenceAddress`,
  `m_CurrentTransposeAddress`, `m_CurrentSequenceEventDurationAddress`,
  `m_NextInstrumentAddress`, `m_NextCommandAddress`, `m_NextNoteAddress`,
  `m_NextNoteIsTiedAddress`, `m_TempoCounterAddress`.
- `m_TriggerSyncAddress` + `m_NoteEventTriggerSyncValue` (note-event sync).

**MusicData (Block 5):** track count; orderlist ptr lo/hi addrs; sequence count;
sequence ptr lo/hi addrs; orderlist size + track1 addr; sequence size + seq00
addr. (Same fields the Stage A emitter already writes.)

**TableDefinition (Block 3):** per-table Type/ID/TextFieldSize/Name/DataLayout
(RowMajor|ColumnMajor)/properties(insert-delete, vertical, continuous)/rule IDs/
Address/Columns/Rows/VisibleRows. Already replicated in
`sidm2/sf2_header_generator.py` (`ParseDriverTables`, driver_info.cpp:347).

**InstrumentDescriptor (Block 4):** instrument cell layout for the editor.

## Driver 11 internals already RE'd (Stage A debugging — reusable)

- SF2 PRG standalone entry `SYS4093` (`$0FFD`) → bootstrap `$2A2A`: `JSR init
  $1000`, install raster IRQ → `$2A4A`.
- `$1000` = `JMP init`, `$1003` = `JMP play` are STUBS that only set a command
  flag (`$16CC`; play→`$40`). Real per-frame dispatcher is `$1006` (reads the
  flag). This is why headless tracing via the simple init+play CLI fails.
- Tables (template `Driver 11 Test - Arpeggio.sf2`, load `$0D7E`): Instruments
  `$1784` (col-major 6×32), Wave `$1924` (col-major 2×256), Pulse `$1B24` (3×256),
  Filter `$1E24` (3×256), Arp `$2124`, Tempo `$2224`, HR `$1904`, Init `$1744`;
  orderlists from `$242A`, sequences packed from `$272A`.

## Two build approaches for the Galway driver

- **(A) Graft onto Driver 11.** Disassemble `sf2driver11_00.prg`, keep its
  sequencer + the state-variable contract, replace the per-voice synth
  (waveform/pulse/ADSR/FM) with Galway's `SOUNDn`/`FILTER`. Pro: SF2 contract
  already correct. Con: RE a 6502 binary we have no source for.
- **(B) New driver from scratch.** Write a type-`0x00` SF2 driver in 6502 ASM:
  an SF2-format sequencer maintaining the Block-2 state variables + Galway's
  synth (we HAVE his source: `galway_src/wizball.asm`). Pro: clean, source-driven
  synth. Con: must implement the full state contract correctly.

Recommendation: **(B)**, because we have Galway's synth source and only need to
RE the *contract* (Block 2 semantics), not Driver 11's whole sequencer. Needs a
6502 assembler (ACME or 64tass).

## Next (B1)

Stand up the assembler + a skeleton type-`0x00` driver that loads in SF2II
(descriptor parses, plays silence), validated by F10-load. Then B2: port Galway
`SOUNDn`/`FILTER`/freq tables; B3: SF2 sequencer honoring the Block-2 contract;
B4: converter emits Galway-driver SF2; B5: validation; B6: integrate.

## Related
`GALWAY_SF2_DRIVER_PLAN.md`, `GALWAY_TO_DRIVER11_MAPPING.md` (Stage A),
`GALWAY_1STGEN_ENGINE.md` (synth source map), `sidm2/sf2_header_generator.py`.
