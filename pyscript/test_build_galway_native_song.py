"""MAIN_VOL: the Galway builder's master-volume plumbing.

WHY THIS FILE EXISTS. `drivers_src/common/sf2_native_driver.asm` used to write
`ora #$0f` -- full master volume, unconditionally. Measured over all 40 Galway
originals the $D418 low nibble is $F on 39 and $C on exactly one,
`MicroProse_Soccer_intro`, which therefore shipped a quarter too loud. The fix
routes the song's own value through `MAIN_VOL` in `layout.inc`, the way
`drivers_src/mon/romuzak_driver.asm` already did.

These tests are SOURCE-LEVEL on purpose. Calling `gen_includes_song` writes
`drivers_src/galway/layout.inc`, a path concurrent builds share (PATTERNS F12),
so a test that exercised it for real would race a build for no extra coverage.
"""
import inspect
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
for _d in ("bin",):
    _p = os.path.join(ROOT, _d)
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class TestMainVolPlumbing(unittest.TestCase):

    def test_gen_includes_song_takes_main_vol_and_defaults_to_full_volume(self):
        """The default must be $0F, or every OTHER caller changes output.

        `build_galway_native_song.main()` and any future caller pass nothing;
        they have to keep producing exactly what they produced before, so the
        default is not a style choice -- it is what makes this change safe.
        """
        import build_galway_native_song as N
        sig = inspect.signature(N.gen_includes_song)
        self.assertIn("main_vol", sig.parameters,
                      "gen_includes_song lost its main_vol parameter")
        self.assertEqual(sig.parameters["main_vol"].default, 0x0F,
                         "the default must stay $0F -- callers that pass nothing "
                         "must keep building byte-identical artifacts")

    def test_the_layout_writer_emits_MAIN_VOL_masked_to_a_nibble(self):
        """$D418's low nibble is 4 bits; the high bits are the filter mode."""
        import build_galway_native_song as N
        src = inspect.getsource(N.gen_includes_song)
        self.assertIn("MAIN_VOL = {main_vol & 0x0F}", src,
                      "layout.inc must carry MAIN_VOL, masked -- an unmasked value "
                      "would spill into $D418's filter-mode bits")

    def test_the_shared_engine_reads_the_SYMBOL_not_a_hardcoded_nibble(self):
        asm = _read("drivers_src", "common", "sf2_native_driver.asm")
        self.assertIn("ora #MAIN_VOL", asm)
        self.assertNotIn("ora #$0f", asm,
                         "the hardcoded full-volume write is back; "
                         "MicroProse_Soccer_intro plays a quarter too loud with it")

    def test_EVERY_layout_inc_that_assembles_with_the_shared_engine_defines_MAIN_VOL(self):
        """THE LOAD-BEARING ONE, and the reason this file is worth its runtime.

        `drivers_src/common/sf2_native_driver.asm` is `.include`d by BOTH
        `drivers_src/galway/galway_driver.asm` and
        `drivers_src/romuzak/romuzak_driver.asm`. Once the engine reads
        `MAIN_VOL`, any layout.inc paired with it that does NOT define the
        symbol fails to assemble -- so this is a two-corpus invariant, not a
        Galway one. romuzak/layout.inc already defined `MAIN_VOL = 15` before
        this change, which is exactly why that corpus stays byte-identical.
        """
        for driver in ("galway", "romuzak"):
            asm = _read("drivers_src", driver, "%s_driver.asm" % driver)
            self.assertIn("common/sf2_native_driver.asm", asm,
                          "%s no longer includes the shared engine -- re-check "
                          "whether this invariant still applies" % driver)
            inc = _read("drivers_src", driver, "layout.inc")
            self.assertIn("MAIN_VOL", inc,
                          "drivers_src/%s/layout.inc does not define MAIN_VOL, but its "
                          "driver includes the shared engine, which now reads it -- "
                          "this build cannot assemble" % driver)

    def test_the_trace_builder_takes_the_MODAL_value_NOT_frame_zero(self):
        """Measured 2026-09-04, and the second row is why `modal` is not optional:

            MicroProse_Soccer_intro   modal $C   1 distinct value  (1000/1000)
            Neverending_Story         modal $F  16 distinct values (615/1000 are $F)
            Wizball                   modal $F   1 distinct value  (1000/1000)

        Neverending_Story MODULATES master volume, so no static MAIN_VOL
        expresses it; its modal $F is what ships today and must not regress. A
        frame-0 read is exactly how it would -- the identical shape to the
        INIT_PASSBAND seed bug fixed in 8c3fd8e, where seeding from frame 0
        swapped a wrong `off` for a wrong `LP` and measured as no change at all.
        """
        src = _read("bin", "build_galway_trace_song.py")
        self.assertIn("max(set(_lo), key=_lo.count)", src,
                      "the MAIN_VOL seed is no longer the MODAL value")
        self.assertIn("main_vol=main_vol", src,
                      "the measured value is not reaching gen_includes_song")
        self.assertIn("main_vol = 0x0F", src,
                      "a siddump failure must fall back to $0F rather than "
                      "silently changing a build")


if __name__ == "__main__":
    unittest.main()
