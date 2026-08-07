"""SID accuracy calculation module.

This module provides reusable accuracy calculation for comparing
original and exported SID files based on register-level comparison.

Can work with:
- Pre-generated siddump output files (for pipeline integration)
- Live SID files (runs siddump automatically)

Version: 1.4.1 (baseline)
Date: 2025-12-12

Usage:
    # From existing dump files (pipeline integration)
    accuracy = calculate_accuracy_from_dumps(
        'output/file_original.dump',
        'output/file_exported.dump'
    )

    # From SID files directly
    accuracy = calculate_accuracy_from_sids(
        'original.sid',
        'exported.sid',
        duration=30
    )
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import logging

from sidm2.fidelity_common import score_pct

logger = logging.getLogger(__name__)


class SIDRegisterCapture:
    """Captures SID register writes frame by frame.

    Can capture from:
    - Siddump output text (for reusing existing dumps)
    - SID file directly (runs siddump)
    """

    # SID register names
    REGISTER_NAMES = {
        0x00: "Voice1_FreqLo", 0x01: "Voice1_FreqHi",
        0x02: "Voice1_PulseLo", 0x03: "Voice1_PulseHi",
        0x04: "Voice1_Control", 0x05: "Voice1_Attack_Decay",
        0x06: "Voice1_Sustain_Release",
        0x07: "Voice2_FreqLo", 0x08: "Voice2_FreqHi",
        0x09: "Voice2_PulseLo", 0x0A: "Voice2_PulseHi",
        0x0B: "Voice2_Control", 0x0C: "Voice2_Attack_Decay",
        0x0D: "Voice2_Sustain_Release",
        0x0E: "Voice3_FreqLo", 0x0F: "Voice3_FreqHi",
        0x10: "Voice3_PulseLo", 0x11: "Voice3_PulseHi",
        0x12: "Voice3_Control", 0x13: "Voice3_Attack_Decay",
        0x14: "Voice3_Sustain_Release",
        0x15: "FilterCutoffLo", 0x16: "FilterCutoffHi",
        0x17: "FilterResonance_Routing", 0x18: "FilterMode_Volume"
    }

    def __init__(self, sid_path: Optional[str] = None,
                 siddump_text: Optional[str] = None,
                 duration: int = 30):
        """Initialize register capture.

        Args:
            sid_path: Path to SID file (for live capture)
            siddump_text: Pre-generated siddump output text
            duration: Duration in seconds for live capture
        """
        self.sid_path = Path(sid_path) if sid_path else None
        self.duration = duration
        self.frames = []
        self.register_history = {i: [] for i in range(0x19)}
        self.stats = {
            'total_frames': 0,
            'total_writes': 0,
            'voice_activity': {1: 0, 2: 0, 3: 0}
        }

        # If siddump text provided, parse it immediately
        if siddump_text:
            self._parse_siddump_output(siddump_text)

    def capture_from_file(self, dump_path: str) -> bool:
        """Capture from existing siddump file.

        Args:
            dump_path: Path to .dump file

        Returns:
            True if successful
        """
        try:
            dump_file = Path(dump_path)
            if not dump_file.exists():
                return False

            siddump_text = dump_file.read_text(encoding='utf-8', errors='ignore')
            self._parse_siddump_output(siddump_text)
            return True
        except Exception:
            return False

    def capture_from_sid(self) -> bool:
        """Capture by running siddump on SID file.

        Returns:
            True if successful
        """
        if not self.sid_path or not self.sid_path.exists():
            logger.error(
                f"SID file does not exist: {self.sid_path}\n"
                f"  Suggestion: Verify file path is correct\n"
                f"  Check: Ensure file has .sid extension\n"
                f"  Try: Use absolute path instead of relative path\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#file-not-found-issues"
            )
            return False

        # Try Python siddump first (preferred)
        try:
            import sys
            import io
            from pyscript.siddump_complete import main as siddump_main

            # Capture stdout from Python siddump
            old_stdout = sys.stdout
            old_argv = sys.argv
            sys.stdout = captured_output = io.StringIO()

            try:
                sys.argv = ['siddump', str(self.sid_path), '-z', f'-t{self.duration}']
                siddump_main()
                output = captured_output.getvalue()
            finally:
                sys.stdout = old_stdout
                sys.argv = old_argv

            self._parse_siddump_output(output)
            return True

        except Exception as e:
            logger.warning(f"Python siddump failed: {e}, trying C exe fallback")

            # Fallback to C exe if Python siddump fails
            siddump_exe = Path('tools/siddump.exe')
            if not siddump_exe.exists():
                logger.error(
                    f"Siddump exe not found: {siddump_exe}\n"
                    f"  Suggestion: Python siddump should work without C exe\n"
                    f"  Check: Verify Python siddump installation is working\n"
                    f"  Try: python pyscript/siddump_complete.py {self.sid_path}\n"
                    f"  See: docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md"
                )
                return False

            try:
                result = subprocess.run(
                    [str(siddump_exe.absolute()),
                     str(self.sid_path.absolute()),
                     '-z',
                     f'-t{self.duration}'],
                    capture_output=True,
                    text=True,
                    timeout=self.duration + 10
                )

                if result.returncode != 0:
                    logger.error(
                        f"Siddump exe failed with return code: {result.returncode}\n"
                        f"  Suggestion: Use Python siddump instead (more reliable)\n"
                        f"  Check: Verify SID file is valid\n"
                        f"  Try: python pyscript/siddump_complete.py {self.sid_path}\n"
                        f"  See: docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md"
                    )
                    return False

                self._parse_siddump_output(result.stdout)
                return True
            except Exception as e:
                logger.error(
                    f"Siddump exe exception: {e}\n"
                    f"  Suggestion: siddump.exe failed to execute\n"
                    f"  Check: Verify siddump.exe is available in tools/ directory\n"
                    f"  Try: Use Python siddump instead (use_python=True)\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#siddump-exceptions"
                )
                return False

    def _parse_siddump_output(self, output: str):
        """Parse siddump table format into frame data."""
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('+') or '| Frame |' in line:
                continue

            if line.startswith('|'):
                parts = [p.strip() for p in line.split('|')[1:]]
                if len(parts) < 5:
                    continue

                try:
                    frame_num = int(parts[0])
                    frame_data = {}

                    # Parse 3 voices
                    for voice_idx in range(3):
                        voice_data = parts[1 + voice_idx].split()
                        if len(voice_data) >= 5:
                            # Frequency
                            freq_str = voice_data[0]
                            if freq_str != '....':
                                try:
                                    freq = int(freq_str, 16)
                                    reg_base = voice_idx * 7
                                    frame_data[reg_base + 0] = freq & 0xFF
                                    frame_data[reg_base + 1] = (freq >> 8) & 0xFF
                                except ValueError:
                                    pass

                            # Waveform, ADSR, Pulse width
                            wf_idx, adsr_idx, pw_idx = 3, 4, 5

                            if wf_idx < len(voice_data):
                                wf_str = voice_data[wf_idx]
                                if wf_str not in ('.', '..', '....'):
                                    try:
                                        wf = int(wf_str, 16)
                                        frame_data[voice_idx * 7 + 4] = wf
                                    except ValueError:
                                        pass

                            if adsr_idx < len(voice_data):
                                adsr_str = voice_data[adsr_idx]
                                if adsr_str != '....':
                                    try:
                                        if len(adsr_str) == 4:
                                            ad = int(adsr_str[:2], 16)
                                            sr = int(adsr_str[2:], 16)
                                            frame_data[voice_idx * 7 + 5] = ad
                                            frame_data[voice_idx * 7 + 6] = sr
                                    except ValueError:
                                        pass

                            if pw_idx < len(voice_data):
                                pw_str = voice_data[pw_idx]
                                if pw_str not in ('...', '....'):
                                    try:
                                        pw = int(pw_str, 16)
                                        frame_data[voice_idx * 7 + 2] = pw & 0xFF
                                        frame_data[voice_idx * 7 + 3] = (pw >> 8) & 0x0F
                                    except ValueError:
                                        pass

                    # Parse filter
                    if len(parts) > 4:
                        filter_data = parts[4].split()
                        if len(filter_data) >= 4:
                            # Cutoff
                            fcut_str = filter_data[0]
                            if fcut_str != '....':
                                try:
                                    fcut = int(fcut_str, 16)
                                    frame_data[0x15] = fcut & 0xFF
                                    frame_data[0x16] = (fcut >> 8) & 0x07
                                except ValueError:
                                    pass

                            # Resonance
                            if len(filter_data) > 1:
                                rc_str = filter_data[1]
                                if rc_str != '..':
                                    try:
                                        frame_data[0x17] = int(rc_str, 16)
                                    except ValueError:
                                        pass

                            # Volume
                            if len(filter_data) > 3:
                                vol_str = filter_data[3]
                                if vol_str != '.':
                                    try:
                                        frame_data[0x18] = int(vol_str, 16)
                                    except ValueError:
                                        pass

                    # Store frame
                    self.frames.append(frame_data)
                    self.stats['total_frames'] += 1

                    # Update register history
                    for reg, value in frame_data.items():
                        self.register_history[reg].append({
                            'frame': frame_num,
                            'value': value
                        })
                        self.stats['total_writes'] += 1

                except (ValueError, IndexError):
                    continue


class SIDComparator:
    """Compares two SID register captures for accuracy."""

    def __init__(self, original: SIDRegisterCapture, exported: SIDRegisterCapture):
        self.original = original
        self.exported = exported

    def compare(self) -> Dict:
        """Compare captures and calculate accuracy metrics.

        Returns:
            Dict with accuracy percentages and detailed results
        """
        # None, not 0.0: with nothing compared yet these are "no evidence", and
        # the zero-frame early return below hands them straight back. Scoring an
        # empty comparison as 0% is the same class of lie as scoring it 100%.
        results = {
            'frame_accuracy': None,
            'voice_accuracy': {},
            'register_accuracy': {},
            'filter_accuracy': None,
            'overall_accuracy': None
        }

        # Frame-by-frame comparison
        max_frames = min(len(self.original.frames), len(self.exported.frames))
        if max_frames == 0:
            return results

        matching_frames = sum(
            1 for i in range(max_frames)
            if self._frames_match(self.original.frames[i], self.exported.frames[i])
        )
        results['frame_accuracy'] = (matching_frames / max_frames * 100)

        # Voice accuracy -- frame-aligned, not "frames where both bytes happened
        # to be co-written" (see _timeline).
        for voice in range(1, 4):
            freq_acc = self._agreement(
                self._get_frequencies(self.original, voice, max_frames),
                self._get_frequencies(self.exported, voice, max_frames))
            wave_acc = self._agreement(
                self._get_waveforms(self.original, voice, max_frames),
                self._get_waveforms(self.exported, voice, max_frames))

            results['voice_accuracy'][f'voice{voice}'] = {
                'frequency': freq_acc,
                'waveform': wave_acc
            }

        # Register accuracy
        for reg in range(0x19):
            orig_hist = self.original.register_history[reg]
            exp_hist = self.exported.register_history[reg]

            if not orig_hist and not exp_hist:
                continue

            matches = sum(
                1 for i in range(min(len(orig_hist), len(exp_hist)))
                if orig_hist[i]['value'] == exp_hist[i]['value']
            )
            total = max(len(orig_hist), len(exp_hist))

            if total > 0:
                reg_name = SIDRegisterCapture.REGISTER_NAMES.get(reg, f"Reg_{reg:02X}")
                results['register_accuracy'][reg_name] = (matches / total * 100)

        # Filter accuracy -- None (not 0.0) when NEITHER side ever touches the
        # filter. The old code left the 0.0 initialiser in place in that case and
        # then weighted it 10% into overall_accuracy, so a file was docked ten
        # points for *correctly* not using a filter. Rob Hubbard's players never
        # write the cutoff at all (docs/players/HUBBARD.md), so that entire
        # family was capped at 90% for being faithful. Note HUBBARD.md also
        # records the mirror-image bug -- a validator scoring 0 == 0 as "filter
        # 100%" -- so both directions of the same vacuous comparison have now
        # been live in this repo simultaneously.
        results['filter_accuracy'] = self._agreement(
            self._get_filter_values(self.original, max_frames),
            self._get_filter_values(self.exported, max_frames))

        # Overall accuracy: weighted mean over the dimensions that HAVE evidence,
        # renormalised by their own weights. An unmeasured dimension is dropped
        # rather than folded in as a zero -- that is the whole point of _agreement
        # returning None. Frame accuracy is always present (max_frames > 0 here).
        voice_scores = [s for v in results['voice_accuracy'].values()
                        for s in (v['frequency'], v['waveform']) if s is not None]
        avg_voice = sum(voice_scores) / len(voice_scores) if voice_scores else None

        reg_scores = list(results['register_accuracy'].values())
        avg_register = sum(reg_scores) / len(reg_scores) if reg_scores else None

        weighted = [(results['frame_accuracy'], 0.4), (avg_voice, 0.3),
                    (avg_register, 0.2), (results['filter_accuracy'], 0.1)]
        live = [(v, w) for v, w in weighted if v is not None]
        results['overall_accuracy'] = (
            sum(v * w for v, w in live) / sum(w for _, w in live) if live else None)

        return results

    def _frames_match(self, frame1: Dict, frame2: Dict) -> bool:
        """
        Check if two frames represent the same state.

        Since SID players only write registers that change (sparse frames),
        we compare only registers that appear in BOTH frames. Registers
        that don't appear haven't changed from their previous value.

        This fixes the 0.07% discrepancy caused by different sparse patterns
        in original vs exported SIDs.
        """
        # Get common registers (registers in both frames)
        common_regs = set(frame1.keys()) & set(frame2.keys())

        # If no common registers, frames are equivalent only if both are empty
        if not common_regs:
            return len(frame1) == len(frame2) == 0

        # Compare values of common registers
        # Frames match if all written values match (sparse pattern doesn't matter)
        return all(frame1[reg] == frame2[reg] for reg in common_regs)

    @staticmethod
    def _timeline(capture: SIDRegisterCapture, regs, nframes: int) -> List[Optional[Tuple]]:
        """Per-frame fill-forwarded tuple of `regs`, or None before any write.

        siddump prints a register only on the frame it is WRITTEN: absence means
        *held*, not zero. Two bugs followed from ignoring that, and this one
        function replaces both:

        - `_get_frequencies` used to append a value only on frames where freq_lo
          and freq_hi were *both* present, then `compare()` paired the two sides
          with `zip`. The lists were therefore not frame-aligned -- they were
          "frames where both bytes happened to be co-written". A player writing
          lo-only (any fine vibrato or slide) contributed nothing, and a single
          extra or missing dual-write near the start silently misaligned every
          later comparison. That fed 30% of `overall_accuracy`.
        - `_get_filter_values` used `frame.get(0x15, 0)`, which defaulted a HELD
          register to 0, so on a frame writing only $D415 the cutoff-hi read 0
          and the tuple was a value that never existed on the hardware.

        None (rather than 0) until a register is first written, so a caller can
        drop frames where NEITHER side has evidence instead of scoring 0 == 0 --
        the vacuous comparison `score_pct` exists to make impossible.
        """
        cur = {r: None for r in regs}
        out = []
        for i in range(nframes):
            frame = capture.frames[i]
            for r in regs:
                if r in frame:
                    cur[r] = frame[r]
            out.append(None if all(v is None for v in cur.values())
                       else tuple((cur[r] or 0) for r in regs))
        return out

    @staticmethod
    def _agreement(a: List[Optional[Tuple]], b: List[Optional[Tuple]]) -> Optional[float]:
        """Frame-aligned agreement of two timelines, or None if neither ever wrote.

        Frames where BOTH sides are still None are dropped from the denominator:
        they are "no test ran", not "agreed". Returning None rather than 0.0 or
        100.0 for an all-empty comparison is what stops a player that never uses
        a register from being scored on it at all -- see `score_pct`.
        """
        ok = tot = 0
        for x, y in zip(a, b):
            if x is None and y is None:
                continue
            tot += 1
            if x == y:
                ok += 1
        return score_pct(ok, tot)

    def _get_frequencies(self, capture: SIDRegisterCapture, voice: int,
                         nframes: int) -> List[Optional[Tuple]]:
        """Per-frame (freq_lo, freq_hi) for a voice, fill-forwarded."""
        base = (voice - 1) * 7
        return self._timeline(capture, (0x00 + base, 0x01 + base), nframes)

    def _get_waveforms(self, capture: SIDRegisterCapture, voice: int,
                       nframes: int) -> List[Optional[Tuple]]:
        """Per-frame control byte for a voice, fill-forwarded."""
        return self._timeline(capture, (0x04 + (voice - 1) * 7,), nframes)

    def _get_filter_values(self, capture: SIDRegisterCapture,
                           nframes: int) -> List[Optional[Tuple]]:
        """Per-frame (cutoff_lo, cutoff_hi, resonance, mode), fill-forwarded.

        Held registers carry forward instead of defaulting to 0 -- the old
        `frame.get(0x15, 0)` fabricated a cutoff of 0 on any frame that wrote
        only $D416, a value the hardware never held. Raw bytes are compared
        rather than the packed 11-bit cutoff so a $D416-only write is still
        visible as a change.
        """
        return self._timeline(capture, (0x15, 0x16, 0x17, 0x18), nframes)


def calculate_accuracy_from_dumps(original_dump: str, exported_dump: str) -> Optional[Dict]:
    """Calculate accuracy from existing siddump files.

    Args:
        original_dump: Path to original SID dump file
        exported_dump: Path to exported SID dump file

    Returns:
        Dict with accuracy metrics, or None if failed
    """
    try:
        original_capture = SIDRegisterCapture()
        if not original_capture.capture_from_file(original_dump):
            return None

        exported_capture = SIDRegisterCapture()
        if not exported_capture.capture_from_file(exported_dump):
            return None

        comparator = SIDComparator(original_capture, exported_capture)
        return comparator.compare()

    except Exception:
        return None


def calculate_accuracy_from_sids(original_sid: str, exported_sid: str,
                                 duration: int = 30) -> Optional[Dict]:
    """Calculate accuracy by running siddump on SID files.

    Args:
        original_sid: Path to original SID file
        exported_sid: Path to exported SID file
        duration: Capture duration in seconds

    Returns:
        Dict with accuracy metrics, or None if failed
    """
    try:
        original_capture = SIDRegisterCapture(sid_path=original_sid, duration=duration)
        if not original_capture.capture_from_sid():
            logger.error(
                f"Failed to capture registers from original SID: {original_sid}\n"
                f"  Suggestion: Cannot capture SID register data from original file\n"
                f"  Check: Verify SID file is valid and playable\n"
                f"  Try: Test SID file in VICE emulator first\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#register-capture-failures"
            )
            return None

        exported_capture = SIDRegisterCapture(sid_path=exported_sid, duration=duration)
        if not exported_capture.capture_from_sid():
            logger.error(
                f"Failed to capture registers from exported SID: {exported_sid}\n"
                f"  Suggestion: Cannot capture SID register data from exported file\n"
                f"  Check: Verify exported SID file is valid\n"
                f"  Try: Reconvert with different driver if export failed\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#register-capture-failures"
            )
            return None

        comparator = SIDComparator(original_capture, exported_capture)
        return comparator.compare()

    except Exception as e:
        logger.error(
            f"Accuracy calculation exception: {e}\n"
            f"  Suggestion: Unexpected error during accuracy calculation\n"
            f"  Check: Verify both SID files are valid and playable\n"
            f"  Try: Enable debug logging for detailed error trace\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#accuracy-calculation-errors",
            exc_info=True
        )
        return None
