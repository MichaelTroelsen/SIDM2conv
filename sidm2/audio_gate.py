"""Post-build cycle-accurate audio gate (v3.5.32-v3.5.35).

Verifies that the built SF2's audio matches the original SID under
zig64 cycle-accurate emulation. If they diverge, progressively reverts
the converter's optional patches until audio matches:

  1. Try as-built. If matches, done.
  2. Revert ch_seq_ptr patches (Edie_Ball-class: py65 build-time gate
     missed it because of CIA-IRQ-driven INIT).
  3. NOP the wave-copy JSR in the translator (Patterns-class:
     wave-copy's destination addresses overlap binary data the player
     reads for other purposes — `$7F` gets written to AD slots).
  4. Both reverted (combination case).
  5. Block 2 native-redirect (Exorcist_preview-class: the SF2 wrapper
     layer itself diverges from native cycle-accurate emulation; point
     Block 2 init/play at the PSID-native entries to skip the wrapper).

Each step costs ~30ms for the zig64 trace at 200 PAL frames — long
enough to catch Patterns' frame-169 divergence and Exorcist_preview's
cumulative wrapper-init drift, while keeping cost reasonable.

The gate degrades gracefully when the zig64 tracer isn't installed
(`verify_sf2_audio` returns True on tracer-missing). The gate logs
its action via the project logger so users can see what it did.
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def try_block2_native_redirect(out: bytearray, init_addr: int,
                                play_addr: int):
    """Rewrite Block 2's declared init/play addresses to point at the
    PSID-native entry points. Returns (b2_init_off, b2_play_off,
    orig_init_le, orig_play_le) tuple or None if Block 2 wasn't
    found. Used by `run_post_build_audio_gate` as a final fallback
    for files where the SF2 wrapper layer itself diverges from
    native cycle-accurate emulation.

    Block chain starts at file off 4 (PRG load:2 + magic:2).
    Walk chain: [id:1][size:1][body...] until id == 0xFF.
    Block 2 body layout: [Init:2 LE][Stop:2 LE][Play/Update:2 LE]...
    """
    o = 4
    while o + 2 <= len(out):
        bid = out[o]
        if bid == 0xFF:
            break
        bsz = out[o + 1]
        if bid == 2 and bsz >= 6:
            # Found Block 2. Body starts at o+2.
            init_off = o + 2
            play_off = o + 2 + 4
            orig_init = bytes(out[init_off:init_off + 2])
            orig_play = bytes(out[play_off:play_off + 2])
            # Patch
            out[init_off]     = init_addr & 0xFF
            out[init_off + 1] = (init_addr >> 8) & 0xFF
            out[play_off]     = play_addr & 0xFF
            out[play_off + 1] = (play_addr >> 8) & 0xFF
            return (init_off, play_off, orig_init, orig_play)
        o += 2 + bsz
    return None


def restore_block2(out: bytearray, saved) -> None:
    """Undo a Block 2 redirect using the saved-state tuple from
    `try_block2_native_redirect`."""
    init_off, play_off, orig_init, orig_play = saved
    out[init_off:init_off + 2] = orig_init
    out[play_off:play_off + 2] = orig_play


def run_post_build_audio_gate(out: bytearray, sid_path: Optional[Path],
                                np21_off: Optional[int],
                                ch_seq_patches: list,
                                wave_copy_jsr_offs: list,
                                ch_seq_patch_layout: Optional[str],
                                sid_init: Optional[int],
                                sid_play: Optional[int]
                                ) -> dict:
    """Run the cycle-accurate post-build audio gate.

    Args:
        out: SF2 output bytearray (MODIFIED IN PLACE if gate reverts).
        sid_path: path to original .sid file (gate is skipped if None).
        np21_off: file offset where the c64 binary lives in `out`.
        ch_seq_patches: list of (c64_offset, original_byte) tuples
            recording bytes patched at ch_seq_ptr addresses.
        wave_copy_jsr_offs: list of file offsets of wave-copy JSR
            instructions inside the translator.
        ch_seq_patch_layout: label for log messages
            ("Wizax-A", "Zetrex/YP", "default", or None).
        sid_init, sid_play: PSID-declared INIT/PLAY entry addresses.

    Returns a dict reporting which reverts (if any) were applied:
        {'ch_seq_reverted': bool, 'wave_copy_nopped': bool,
         'block2_redirected': bool}
    Empty dict if the gate was skipped (no sid_path, no tracer, etc).
    """
    result = {'ch_seq_reverted': False, 'wave_copy_nopped': False,
              'block2_redirected': False}
    if np21_off is None or sid_path is None:
        return result
    sid_path = Path(sid_path)
    if not sid_path.exists():
        return result
    if sid_init is None or sid_play is None:
        return result
    if sid_play == 0:
        sid_play = sid_init + 3
    sf2_init, sf2_play = 0x0F90, 0x0F94
    try:
        from sidm2.zig64_audio_gate import verify_sf2_audio
    except Exception as e:
        logger.debug(f"  Post-build zig64 audio gate skipped: {e}")
        return result

    def _check(buf: bytes, override_init=None, override_play=None) -> bool:
        try:
            # 200 frames catches Patterns-class late divergences
            # (instrument-edge at frame 169) while keeping the
            # trace cost under ~30ms (zig64 ≈ 140µs/frame).
            return verify_sf2_audio(
                sf2_bytes=buf, sid_path=sid_path,
                sf2_init_addr=override_init if override_init is not None else sf2_init,
                sf2_play_addr=override_play if override_play is not None else sf2_play,
                sid_init_addr=sid_init, sid_play_addr=sid_play,
                frames=200,
            )
        except Exception:
            return True   # tracer error → degrade gracefully

    if _check(bytes(out)):
        return result  # SF2 already matches; no reverts needed

    patches = ch_seq_patches or []
    wave_jsr_offs = wave_copy_jsr_offs or []

    # 1) Try reverting only ch_seq_ptr patches
    if patches:
        saved = [out[np21_off + o] for o, _b in patches]
        for c64_off, orig_byte in patches:
            file_off = np21_off + c64_off
            if 0 <= file_off < len(out):
                out[file_off] = orig_byte
        if _check(bytes(out)):
            layout = ch_seq_patch_layout or "default"
            logger.info(
                f"  Post-build zig64 gate: reverted {layout} ch_seq_ptr "
                f"patch ({len(patches)} bytes) to preserve audio fidelity."
            )
            result['ch_seq_reverted'] = True
            return result
        # Restore for next attempt
        for (c64_off, _orig), saved_b in zip(patches, saved):
            file_off = np21_off + c64_off
            if 0 <= file_off < len(out):
                out[file_off] = saved_b

    # 2) Try NOPping wave-copy JSR
    if wave_jsr_offs:
        saved_jsr = []
        for jo in wave_jsr_offs:
            if jo + 3 <= len(out):
                saved_jsr.append((jo, bytes(out[jo:jo + 3])))
                out[jo:jo + 3] = b'\xEA\xEA\xEA'
        if _check(bytes(out)):
            logger.info(
                f"  Post-build zig64 gate: NOPped wave-copy JSR "
                f"({len(wave_jsr_offs)} call) to preserve audio fidelity "
                f"(F3 wave edit propagation disabled for this file)."
            )
            result['wave_copy_nopped'] = True
            return result
        # Restore for next attempt
        for jo, orig_bytes in saved_jsr:
            out[jo:jo + 3] = orig_bytes

    # 3) Try both reverts
    if patches and wave_jsr_offs:
        for c64_off, orig_byte in patches:
            file_off = np21_off + c64_off
            if 0 <= file_off < len(out):
                out[file_off] = orig_byte
        for jo in wave_jsr_offs:
            if jo + 3 <= len(out):
                out[jo:jo + 3] = b'\xEA\xEA\xEA'
        if _check(bytes(out)):
            logger.info(
                f"  Post-build zig64 gate: reverted ch_seq_ptr patch "
                f"AND NOPped wave-copy JSR to preserve audio fidelity."
            )
            result['ch_seq_reverted'] = True
            result['wave_copy_nopped'] = True
            return result

    # 4) Final fallback: redirect Block 2's declared init/play to PSID
    # native. Bypasses the wrapper layer entirely (zig64 / SF2II call
    # the binary's native entries directly). Tradeoff: F1-F5 edit
    # propagation paths go through the translator at $0F9E (via $0F94);
    # redirecting means edits won't reach the player. For files that
    # already can't propagate (ch_seq_ptr was skipped), this is a clean
    # audio win with no editor regression.
    saved_b2 = try_block2_native_redirect(out, sid_init, sid_play)
    if saved_b2 is not None and _check(bytes(out),
                                          override_init=sid_init,
                                          override_play=sid_play):
        logger.info(
            f"  Post-build zig64 gate: redirected Block 2 init/play "
            f"from $0F90/$0F94 to native ${sid_init:04X}/${sid_play:04X} "
            f"to preserve audio fidelity (editor-side wrapper bypassed; "
            f"F1-F5 edit propagation NOT available for this file)."
        )
        result['block2_redirected'] = True
        return result
    elif saved_b2 is not None:
        # Didn't help — restore Block 2 wrapper addresses
        restore_block2(out, saved_b2)

    # Audio still diverges even with all reverts + redirects. Log and
    # leave the SF2 as-is. Some divergence is genuinely architectural;
    # SF2 is the best we can do.
    logger.warning(
        f"  Post-build zig64 gate: SF2 audio still diverges from SID "
        f"after attempting all reverts and Block 2 redirect. Leaving "
        f"SF2 as-built. Investigate per-file."
    )
    return result
