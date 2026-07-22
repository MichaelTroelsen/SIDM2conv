"""Blackbird Stage-B per-frame simulator (validated byte-exact against real
hardware 2026-07-19, see docs/players/BLACKBIRD.md's "Stage B synth engine"
section -- 14,673/14,673 (Fargo) and 18,332/18,332 (Glyptodont) register
writes over 1200 real frames, exact order+value match against VICE traces).

Copied verbatim (this session) from the scratch path this doc names
(`blackbird_everyframe_sim.py`) into the repo, co-located with
bin/build_blackbird_native_song.py, which uses it as its formula oracle for
translating Blackbird's wave/pulse/filter/fx programs into the shared native
driver's table format -- see that module's docstring for how each engine is
driven (directly seeding VoiceState + calling `everyframe()` in isolation,
bypassing the prepare1/2/3 dispatch, since the 3 sub-engines this module
implements are pure per-voice/global state steppers with no dependency on
the note-stream dispatch cadence).

Ports player.s's playroutine dispatch + prepare1/2/3 + execute + everyframe
literally, instruction-by-instruction, driven by the already-decoded
per-voice note-event byte streams from sidm2.blackbird_parser.decode_streams()
(reused verbatim -- decompression is NOT reimplemented here, only consumed).

6502 arithmetic (ADC/SBC/CMP carry + overflow) is emulated with small helper
functions rather than hand-derived per callsite, to avoid transcription bugs.
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sidm2.blackbird_parser import locate_blackbird, load_sid, decode_streams  # noqa: E402


# ---------------------------------------------------------------------------
# 6502 arithmetic helpers (binary mode only; Blackbird never uses decimal)
# ---------------------------------------------------------------------------
def adc(a, operand, carry_in):
    total = a + operand + carry_in
    result = total & 0xFF
    carry_out = 1 if total > 0xFF else 0
    overflow = bool((~(a ^ operand)) & (a ^ result) & 0x80)
    return result, carry_out, overflow


def cmp_carry(a, operand):
    """CMP/CPX/CPY: carry = 1 if a >= operand (unsigned)."""
    return 1 if (a & 0xFF) >= (operand & 0xFF) else 0


def asl(a):
    result = (a << 1) & 0xFF
    carry_out = 1 if (a & 0x80) else 0
    return result, carry_out


def ror(a, carry_in):
    result = ((carry_in << 7) | (a >> 1)) & 0xFF
    carry_out = a & 1
    return result, carry_out


def lsr(a):
    result = (a >> 1) & 0xFF
    carry_out = a & 1
    return result, carry_out


# ---------------------------------------------------------------------------
class VoiceState:
    __slots__ = ('trtimer', 'pendnote', 'pendfx', 'pendins', 'wavemask',
                 'fxpos', 'currfx', 'currins', 'basepitch', 'wavepos',
                 'pwidth', 'rpos')

    def __init__(self):
        self.trtimer = 0xFF
        self.pendnote = 0
        self.pendfx = 0
        self.pendins = 0
        self.wavemask = 0xFE
        self.fxpos = 0
        self.currfx = 0
        self.currins = 0
        self.basepitch = 0
        self.wavepos = 0
        self.pwidth = 0
        self.rpos = 0


class BlackbirdSim:
    """Real-per-frame simulator. voice index i in {0,1,2} <-> SID offset X=7*i
    (0=voice0/osc1, 1=voice1/osc2, 2=voice2/osc3), matching player.s's X."""

    def __init__(self, lay, d, la, streams, ins_restart, ins_restart2,
                 tempo_debug=None, snapshot_cb=None):
        self.lay = lay
        self.d = d
        self.la = la
        self.streams = streams  # 3 full decoded byte arrays (bytes-like)
        self.ins_restart = ins_restart
        self.ins_restart2 = ins_restart2
        self.tempo_debug = tempo_debug if tempo_debug is not None else []
        # B7 (part-boundary priming, see docs/players/BLACKBIRD.md's "B7"
        # section): optional hook invoked once per real_frame() call, AFTER
        # execute() has committed this frame's pending note/instrument state
        # (if any) but BEFORE everyframe() has stepped the wave/pulse/fx/
        # filter engines forward -- i.e. exactly the engine state a NEW part
        # starting at this real frame needs to prime its own do_init with.
        # Purely additive: when None (the default, used by every EXISTING
        # caller/test), this changes nothing about real_frame()'s own
        # behavior or the regs/write_log it produces.
        self.snapshot_cb = snapshot_cb

        self.v = [VoiceState() for _ in range(3)]
        self.zp_filtpos = 0
        self.filt_owner = 0     # B7: which filt_start (0 = the song's own
                                 # default program) currently governs
                                 # zp_filtpos -- see execute()'s own
                                 # `if fv != 0: self.zp_filtpos = fv` below,
                                 # where fv IS a real filt_start value by
                                 # construction (ins_filt[y-1]). Bookkeeping
                                 # only -- never read by any EXISTING code
                                 # path, so this cannot change simulated
                                 # output.
        self.zp_master = 3 * 7  # initroutine: lda #3*7; sta zp_master
        self.zp_tempo = 0       # never explicitly init'd in initroutine -> zero page reset default
        self.m_groove = 0
        self.zp_pendoob = 0
        self.preparejmp = 1     # 1/2/3 = which prepare stage runs on the next unpack dispatch
        self.m_cutoff = 0x80    # initroutine: lda #$80; sta m_cutoff

        self.regs = [0] * 25    # $D400-$D418 shadow (persists frame to frame)
        self.write_log = []     # flat ordered (frame_no, reg, value) event log
        self.frame_no = -1      # bumped by real_frame() before each dispatch

        po = lay.play_base - la

        # fixed template offsets (confirmed this session, see BLACKBIRD.md/task)
        # NOT truncated 96-byte lists: `lda freq_lsb+24,y` is normal 16-bit
        # 6502 addressing (base+24 folded at assemble time, y up to 127 added
        # at runtime) -- it happily reads past the nominal 96-byte table
        # extent into whatever memory follows (freq_msb/freq_lsb physically
        # overlap by 15 bytes per player.s's own comment at line 692, and
        # freq_lsb's tail runs into pwprepare's region for the largest valid
        # y). A fixed-length list here caused an IndexError on Glyptodont
        # (never manifested on Fargo's first 600 frames, purely because its
        # y values happened to stay smaller) -- read the raw memory image
        # directly instead, exactly like wavetable/filttable/fxtable.
        self.freq_msb_addr = lay.play_base + 817
        self.freq_lsb_addr = lay.play_base + 913
        self.pwprepare = list(d[po + 1024:po + 1024 + 256])

        # 2-voice init priming (voice1 then voice0), preparejmp disabled during it.
        # We don't need to replicate the RTS-patch trick -- our getbyte cursor
        # starts at rpos=0 for all voices and only prepare1/2/3 (which we only
        # invoke from real dispatch frames) ever advance it, so simply doing
        # nothing extra here is equivalent: the "priming" in player.s exists to
        # pre-fill the *compressed-data ring buffer*, which decode_streams()
        # already fully resolved into `streams` ahead of time.

    def w(self, reg, value):
        value &= 0xFF
        self.regs[reg] = value
        self.write_log.append((self.frame_no, reg, value))

    # -- raw table readers (absolute C64 address -> byte) -------------------
    def rb(self, addr):
        off = addr - self.la
        if 0 <= off < len(self.d):
            return self.d[off]
        return 0

    def filttable(self, idx):
        return self.rb(self.lay.filttable + (idx & 0xFF))

    def fxtable(self, idx):
        return self.rb(self.lay.fxtable + (idx & 0xFF))

    def wavetable(self, idx):
        return self.rb(self.lay.wavetable + (idx & 0xFF))

    # Instrument/fx tables: raw memory reads, NOT truncated `nins`/`nfx`-length
    # lists -- same fix as freq_lsb/freq_msb below. A REPEAT=1 file's own
    # compressed note stream can genuinely reference an instrument index
    # beyond the located `nins` extent (confirmed: Crank_Crank_Airwolf
    # references instrument #7 while only 5 instrument slots were located,
    # yet `nins_consistent` still holds -- `nins` reflects the compiled
    # table's own evenly-spaced geometry correctly, the SONG just uses an
    # index past it). Real hardware's `lda ins_filt,y`-style indexed
    # addressing has no bounds check either -- it just reads whatever byte
    # sits there (the start of the NEXT table, typically), so a Python list
    # sized to `nins` raises IndexError where real hardware would not.
    def ins_ad(self, idx):
        return self.rb(self.lay.ins_ad + idx)

    def ins_sr(self, idx):
        return self.rb(self.lay.ins_sr + idx)

    def ins_wave(self, idx):
        return self.rb(self.lay.ins_wave + idx)

    def ins_filt(self, idx):
        return self.rb(self.lay.ins_filt + idx)

    def fx_start(self, idx):
        return self.rb(self.lay.fx_start + idx)

    def freq_lsb(self, idx):
        return self.rb(self.freq_lsb_addr + idx)

    def freq_msb(self, idx):
        return self.rb(self.freq_msb_addr + idx)

    # -- per-voice byte stream cursor (mirrors (zp_bufs,x) + inc zp_bufs,x) -
    def getbyte(self, vi):
        s = self.streams[vi]
        p = self.v[vi].rpos
        b = s[p] if p < len(s) else 0xC0
        self.v[vi].rpos += 1
        return b

    def ungetbyte(self, vi):
        self.v[vi].rpos -= 1

    def peekbyte(self, vi):
        s = self.streams[vi]
        p = self.v[vi].rpos
        return s[p] if p < len(s) else 0xC0

    # =========================================================================
    # prepare1 (player.s lines 80-110): per-voice trtimer inc + oob/fx fetch
    # =========================================================================
    def prepare1(self):
        for x in (2, 1, 0):
            vs = self.v[x]
            vs.trtimer = (vs.trtimer + 1) & 0xFF
            if vs.trtimer & 0x80:
                continue  # vskip
            # `lda (zp_bufs,x)` is a PEEK -- the pointer is only actually
            # advanced (`inc zp_bufs,x`) conditionally, below. A first draft
            # of this function consumed unconditionally here, which silently
            # ate the very next voice byte (an instrument-select in the case
            # that first caught this, via real-trace comparison) whenever it
            # was neither an OOB marker nor an fx byte -- desyncing the
            # voice's cursor by exactly 1 byte for the rest of the song.
            b = self.peekbyte(x)
            if b >= 0xF9:
                self.zp_pendoob = b
                self.getbyte(x)             # consume the oob byte
                tested = self.peekbyte(x)   # peek (not consume) the next byte
            else:
                tested = b
            if tested < 0xC8:
                continue  # bcc no_fx -- leave `tested` byte unconsumed
            self.getbyte(x)  # consume the fx byte
            result = (tested - 0xC8) & 0xFF
            vs.currfx = result
            vs.pendfx = result

    # =========================================================================
    # prepare2 (player.s lines 117-160): gate-off/legato/instrument fetch
    # =========================================================================
    def prepare2(self):
        for x in (2, 1, 0):
            vs = self.v[x]
            if vs.trtimer & 0x80:
                continue  # vskip
            b = self.peekbyte(x)
            if b < 0x80:
                # got_note: reuse currins as pendins (implicit repeat-instrument)
                self._pr2_noteback(x, vs.currins)
                continue
            if b >= 0xB8:
                continue  # vskip, not consumed (delay/arp-etc, prepare3's job)
            self.getbyte(x)  # inc zp_bufs,x -- consume
            # sbc #$82-1 = sbc #$81, carry=0 (from `cmp #$b8` with b<$b8 -> carry=0)
            result = (b - 0x81 - 1) & 0xFF
            is_neg = bool(result & 0x80)  # bmi got_special
            if is_neg:
                vs.pendins = result  # $FE=gate-off, $FF=legato
                continue
            vs.currins = result
            self._pr2_noteback(x, result)

    def _pr2_noteback(self, x, ins_value):
        vs = self.v[x]
        vs.pendins = ins_value
        carry = cmp_carry(ins_value, self.ins_restart + 1)
        if not carry:  # bcc norestart (ins_value < INS_RESTART+1, i.e. <= INS_RESTART)
            return
        self.w(6 + 7 * x, 0)  # $d406,x = 0
        vs.wavemask = 0xFE

    # =========================================================================
    # prepare3 (player.s lines 167-200): note/delay fetch, sets v_trtimer
    # =========================================================================
    def prepare3(self):
        for x in (2, 1, 0):
            vs = self.v[x]
            if vs.trtimer & 0x80:
                continue  # vskip
            b = self.peekbyte(x)
            if b >= 0x80:
                # got_delay: A = $ff after `rol` on carry=1 -- see below
                new_timer = 0xF0 | b  # ora #$f0 applied to b itself (delay path: A=b, `ora #$f0`)
            else:
                self.getbyte(x)  # consume the note byte (inc happens at vskip regardless -- see note)
                note = b >> 1  # lsr
                vs.pendnote = note
                if vs.pendins == 0:  # gate-off($fe)/legato($ff) both nonzero -> "alreadyins"
                    vs.pendins = vs.currins
                vs.pendfx = vs.currfx
                # lda #$ff; rol  -- A=$ff, rotate left through carry.
                # carry going into this ROL is whatever LDA left (LDA doesn't
                # touch carry) -- i.e. carry-in = leftover from note's `lsr`
                # (the bit shifted out = the note byte's own LSB, the "delay
                # bit"). rol($ff, carry_in) = ((0xff<<1)|carry_in) & 0xff
                #                            = 0xfe | carry_in
                carry_in = b & 1
                a = (0xFE | carry_in) & 0xFF
                new_timer = 0xF0 | a  # got_delay: ora #$f0 (fallthrough)
            vs.trtimer = new_timer & 0xFF
            # `inc zp_bufs,x` at vskip -- but the note path already consumed
            # via self.getbyte(x) above (its own separate `inc`). The delay
            # path (b>=0x80, peeked not consumed) needs its own explicit
            # consume here, matching the shared `inc zp_bufs,x` at label
            # `vskip` that BOTH the note and delay paths fall through to
            # in the real asm (see note below __init__ / report).
            if b >= 0x80:
                self.getbyte(x)

    # =========================================================================
    # execute (player.s lines 365-517): commit pending -> actual every tick
    # =========================================================================
    def execute(self):
        pend = self.zp_pendoob
        bit = pend & 1
        pend >>= 1
        if bit:
            pass  # sync -- not modelled (zp_extsync toggler; no SID register effect)
        bit = pend & 1
        pend >>= 1
        if bit:
            # tempo: 2 literal bytes read directly from the physical stream,
            # NOT from any per-voice buffer -- already consumed/validated by
            # decode_streams() itself (pend_oob & 2 -> rd.next(); rd.next()).
            # We don't have the raw compressed stream pointer position here
            # (streams are pre-decoded), so pull the *next pending tempo
            # record* recorded by our own decode pass instead (see driver
            # code: tempo_debug is populated by re-deriving records from
            # decode_streams()'s own OOB detections up front).
            if self.tempo_debug:
                new_tempo, new_groove = self.tempo_debug.pop(0)
                self.zp_tempo = new_tempo
                self.m_groove = new_groove
        bit = pend & 1
        pend >>= 1
        if bit:
            pass  # eos -- not modelled (loop-rewind path; REPEAT-only, non-loop build has no effect here)
        self.zp_pendoob = 0

        for x in (2, 1, 0):
            vs = self.v[x]
            vs.basepitch = (vs.pendnote << 2) & 0xFF

            y = vs.pendfx
            if y != 0:
                vs.fxpos = self.fx_start(y - 1) & 0xFF

            y = vs.pendins
            if y != 0:
                if y & 0x80:
                    # special: $fe=gate-off, $ff=legato
                    if y == 0xFE:
                        vs.wavemask = 0xFE
                    # $ff (legato): no register effect here
                else:
                    # genuine instrument select, y = 1..nins
                    carry = cmp_carry(y, self.ins_restart2 + 1)
                    if carry:  # y >= INS_RESTART2+1
                        self.w(6 + 7 * x, 0x0F)  # $d406,x = $0f  (restart2 pre-step)
                    vs.wavemask = 0xFF
                    fv = self.ins_filt(y - 1)
                    if fv != 0:
                        self.zp_filtpos = fv
                        self.filt_owner = fv  # B7: bookkeeping only, see __init__
                    vs.wavepos = self.ins_wave(y - 1)
                    carry = cmp_carry(y, self.ins_restart + 1)
                    if carry:  # y >= INS_RESTART+1 (hard restart 1)
                        self.w(5 + 7 * x, 0x00)  # $d405,x = 0
                        self.w(4 + 7 * x, 0x01)  # $d404,x = 1 (gate on, no waveform)
                    self.w(5 + 7 * x, self.ins_ad(y - 1))
                    self.w(6 + 7 * x, self.ins_sr(y - 1))
            vs.pendfx = 0
            vs.pendins = 0

        self.zp_master = self.zp_tempo
        self.m_groove_apply()
        self.preparejmp = 1  # reset to prepare1

    def m_groove_apply(self):
        self.zp_tempo = (self.zp_tempo ^ self.m_groove) & 0xFF

    # =========================================================================
    # everyframe (player.s lines 207-355): runs every single real frame
    # =========================================================================
    def everyframe(self):
        # player.s's `vloop` (lines 210-317) is a SINGLE combined loop: for
        # each voice x in (14,7,0), it runs the fx/freq engine THEN the
        # wave/pulse engine for that SAME voice, before moving to the next
        # voice -- NOT two separate all-voices passes. (First draft of this
        # simulator had this as two separate loops; real-trace comparison
        # caught the resulting write-order mismatch immediately -- values
        # were byte-identical, only the interleaving was wrong.) The filter
        # engine (lines 323-353) is a true separate `.()` block run once
        # after the voice loop, per real player.s structure.
        for x in (2, 1, 0):
            vs = self.v[x]
            # --- fx / pitch interpolator for this voice ---
            y = vs.fxpos
            row1 = self.fxtable(y + 1)
            a = row1 if (row1 & 0x80) else 0
            # sec; adc v_fxpos,x  -> new_fxpos = old_fxpos + a + 1
            new_fxpos = (vs.fxpos + a + 1) & 0xFF
            vs.fxpos = new_fxpos
            s = self.fxtable(y)  # NOTE: still old y
            if s == 0:
                self.w(0 + 7 * x, 0xFF)
                self.w(1 + 7 * x, 0xFF)
            else:
                a2, cout, _ = adc(s, vs.basepitch, 0)  # clc; adc v_basepitch,x
                t = a2
                a3, carry_new = ror(t, 1 if cout else 0)
                if carry_new == 0:
                    # fractional_x0
                    a4, carry3 = lsr(a3)
                    yidx = a4
                    if carry3:
                        # fractional_10: +12/+13, carry-in=1 (deliberate bias)
                        lsb, c_lsb, _ = adc(self.freq_lsb(yidx + 12),
                                             self.freq_lsb(yidx + 13), 1)
                        msb, _, _ = adc(self.freq_msb(yidx + 12),
                                        self.freq_msb(yidx + 13), c_lsb)
                    else:
                        # fractional_00: direct, no add
                        lsb = self.freq_lsb(yidx + 24)
                        msb = self.freq_msb(yidx + 24)
                else:
                    # fractional_x1
                    a4, carry2 = lsr(a3)
                    yidx = a4
                    if carry2:
                        # fractional_11: +0/+20, carry-in=1 (deliberate bias)
                        lsb, c_lsb, _ = adc(self.freq_lsb(yidx),
                                             self.freq_lsb(yidx + 20), 1)
                        msb, _, _ = adc(self.freq_msb(yidx),
                                        self.freq_msb(yidx + 20), c_lsb)
                    else:
                        # fractional_01: +19/+1, carry-in=0
                        lsb, c_lsb, _ = adc(self.freq_lsb(yidx + 19),
                                             self.freq_lsb(yidx + 1), 0)
                        msb, _, _ = adc(self.freq_msb(yidx + 19),
                                        self.freq_msb(yidx + 1), c_lsb)
                self.w(0 + 7 * x, lsb & 0xFF)
                self.w(1 + 7 * x, msb & 0xFF)

            # --- wave / pulse stepper for this SAME voice ---
            y = vs.wavepos
            w = self.wavetable(y)
            if w >= 0xC0:
                # adc v_wavepos,x with carry=1 (from `cmp #$c0` since w>=$c0)
                y = (w + vs.wavepos + 1) & 0xFF
                w = self.wavetable(y)
            d404v = w & vs.wavemask
            self.w(4 + 7 * x, d404v)
            shifted, carry_bit6 = asl(d404v)
            if not (shifted & 0x80):
                # nopulse: bit6 of d404v was clear
                vs.wavepos = (y + 1) & 0xFF
                continue
            # pulse row (bit6 of d404v set)
            new_wavepos, c_from_wp, _ = adc(y, 2, carry_bit6)
            vs.wavepos = new_wavepos
            pdelta = self.wavetable(y + 1)
            if pdelta & 0x80:
                # absolute set -- REAL asl executes
                pw, _ = asl(pdelta)
            else:
                # relative add -- asl is SKIPPED via the .byt $80 NOP-eats-ASL
                # trick; carry-in inherited from the wavepos ADC above
                pw, _, _ = adc(pdelta, vs.pwidth, c_from_wp)
            vs.pwidth = pw
            pulse_byte = self.pwprepare[pw]
            self.w(2 + 7 * x, pulse_byte)
            self.w(3 + 7 * x, pulse_byte)

        # --- global filter program stepper (once, not per-voice) ---
        y = self.zp_filtpos
        row3 = self.filttable(y + 3)
        if row3 & 0x80:
            new_filtpos = (self.zp_filtpos + row3 + 1) & 0xFF
        else:
            new_filtpos = (self.zp_filtpos + 2 + 1) & 0xFF  # lda #2; sec; adc
        self.zp_filtpos = new_filtpos

        self.w(24, self.filttable(y))  # $d418
        self.w(23, self.filttable(y + 1))  # $d417
        c = self.filttable(y + 2)
        c_shifted, c_top = asl(c)
        if c_top:
            # coset: absolute set
            self.m_cutoff = c_shifted
            self.w(22, (self.m_cutoff ^ 0x80) & 0xFF)  # $d416
        else:
            # add mode: sign-extend low 7 bits of c to a signed 8-bit delta
            carry_cmp = 1 if c_shifted >= 0x80 else 0  # cmp #$80
            delta, _ = ror(c_shifted, carry_cmp)
            result, _, overflow = adc(delta, self.m_cutoff, 0)
            if not overflow:
                self.m_cutoff = result
                self.w(22, (self.m_cutoff ^ 0x80) & 0xFF)  # $d416
            # else: filtdone -- $d416 (and m_cutoff) left untouched this frame

    # =========================================================================
    # playroutine dispatch (player.s lines 55-73): ONE call per real frame
    # =========================================================================
    def real_frame(self):
        """Returns dict of the register writes/state to compare, and runs
        exactly what one real IRQ-driven call to playroutine does."""
        self.frame_no += 1
        if self.zp_master == 0:
            self.execute()
        else:
            newm = (self.zp_master - 7) & 0xFF
            self.zp_master = newm
            if cmp_carry(newm, 3 * 7):  # newm >= 21 -> nounpack
                pass
            else:
                # unpackvoice(X=newm) -- the buffer-refill part is a no-op for
                # us (streams are pre-decoded); dispatch whichever prepare
                # stage preparejmp currently points to, across ALL voices.
                if self.preparejmp == 1:
                    self.prepare1()
                    self.preparejmp = 2
                elif self.preparejmp == 2:
                    self.prepare2()
                    self.preparejmp = 3
                elif self.preparejmp == 3:
                    self.prepare3()
                    # no reset -- stays at 3 until next execute()
        if self.snapshot_cb is not None:
            self.snapshot_cb(self)   # B7: post-execute(), pre-everyframe() hook
        self.everyframe()
        return list(self.regs)


def find_tempo_records(lay, d, la):
    """Re-derive the tempo/groove OOB byte-pair sequence directly, by walking
    voice2's OWN decoded stream in true order and, for every OOB byte with
    bit1 set, reading the 2 stream-literal bytes that immediately follow it
    in PHYSICAL/decode order. We get this for free by re-running
    decode_streams() with piece logging and cross-referencing -- but the
    simplest robust way is to re-run the same _Reader/_emit_piece primitives
    that decode_streams() itself uses, which already extract these for the
    tempo-model doc (BLACKBIRD.md's "Independent triangulation"). We reuse
    decode_streams()'s internal helpers directly (not reimplemented) via the
    module's private API, exactly mirroring its own frame loop, purely to
    also capture the 2 literal bytes read at each tempo OOB (which
    decode_streams() consumes but does not return)."""
    import sidm2.blackbird_parser as bp

    variant = getattr(lay, 'variant', 'v1.2')
    rd = bp._Reader(d, la, lay.streamstart)
    voices = [bp._Voice(), bp._Voice(), bp._Voice()]
    pieces = []

    def need_refill(i):
        v = voices[i]
        return (len(v.out) - v.rpos) < 128

    bp._emit_piece(rd, voices[1], 1, pieces, variant=variant)
    bp._emit_piece(rd, voices[0], 0, pieces, variant=variant)

    records = []
    for frame in range(20000):
        if rd.frozen:
            break
        pend_oob = [0]
        if need_refill(2):
            bp._emit_piece(rd, voices[2], 2, pieces, variant=variant)
        for i in (2, 1, 0):
            bp._run_prep1(voices[i], i, pend_oob)
        if need_refill(1):
            bp._emit_piece(rd, voices[1], 1, pieces, variant=variant)
        for i in (2, 1, 0):
            bp._run_prep2(voices[i])
        if need_refill(0):
            bp._emit_piece(rd, voices[0], 0, pieces, variant=variant)
        for i in (2, 1, 0):
            bp._run_prep3(voices[i])
        if pend_oob[0] & 0x02:
            b1 = rd.next()
            b2 = rd.next()
            # execute()'s code: ldy #2; lda (zp_inptr),y -> zp_tempo (b at +2)
            #                    dey; lda (zp_inptr),y -> m_groove (b at +1)
            # zp_inptr was rewound by 2 first, so y=2 is the byte 2 above the
            # rewound pointer = the SECOND byte read backward = b1 (first
            # rd.next() call, since rd.next() decrements ptr AFTER reading).
            # y=1 -> the byte 1 above rewound ptr = b2.
            # i.e. zp_tempo=b1, m_groove=b2. (validated against decode result
            # below by cross-checking the very first pair against
            # BLACKBIRD.md's documented (35,28) triangulation.)
            records.append((b1, b2))
    return records


def run_sim(sid_path, nframes):
    lay = locate_blackbird(sid_path)
    d, la, h = load_sid(sid_path)
    result = decode_streams(d, la, lay.streamstart, max_frames=20000,
                            variant=getattr(lay, 'variant', 'v1.2'))
    streams = result.voices

    po = lay.play_base - la
    ins_restart = d[po + 93] - 1
    ins_restart2 = d[po + 512] - 1

    tempo_records = find_tempo_records(lay, d, la)

    sim = BlackbirdSim(lay, d, la, streams, ins_restart, ins_restart2,
                        tempo_debug=tempo_records)

    frames_out = []
    for f in range(nframes):
        regs = sim.real_frame()
        frames_out.append(regs)
    return sim, frames_out, tempo_records


if __name__ == '__main__':
    for name in ("Fargo", "Glyptodont"):
        path = os.path.join(ROOT, "SID", "LFT", f"{name}.sid")
        sim, frames, recs = run_sim(path, 20)
        print(name, "first tempo/groove records:", recs[:5])
        for i in range(5):
            print(f"  frame{i}: d400-d418=", frames[i])
