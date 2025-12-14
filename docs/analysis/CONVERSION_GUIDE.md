========================================================================================================================
SID TO SF2 CONVERSION GUIDE
========================================================================================================================

CONVERSION RECOMMENDATIONS BY SOURCE FORMAT:
------------------------------------------------------------------------------------------------------------------------

LAXITY NEWPLAYER V21 SOURCE FILES:

  OPTION 1: Use Custom Laxity Driver
    Pros:
      * 70-90% conversion accuracy
      * Uses original Laxity player code
      * Full feature preservation
    Cons:
      * Requires custom driver installation
      * Larger resulting SF2 file
    Recommended for: Maximum accuracy, important compositions

  OPTION 2: Use Driver 11 (Standard SF2)
    Pros:
      * Works in all SF2 editors
      * No custom driver needed
    Cons:
      * 1-8% conversion accuracy
      * Filter format not compatible
      * Requires manual correction
    Recommended for: Quick edits, simple compositions

  OPTION 3: Use NP20 (JCH NewPlayer v20)
    Pros:
      * Slightly smaller than Driver 11
      * Good compatibility
    Cons:
      * 1-8% conversion accuracy
      * Limited effect support
    Recommended for: Space-constrained projects


DRIVER 11 / SF2-EXPORTED SOURCE FILES:

  Best choice: Driver 11
    * 100% accuracy expected
    * No conversion needed - use SF2 format directly
    * Full feature preservation


CONVERSION BEST PRACTICES:
------------------------------------------------------------------------------------------------------------------------

1. ANALYZE SOURCE FORMAT
   * Identify player type (Laxity, Driver11, NP20, etc.)
   * Check for custom features or advanced effects
   * Review table sizes and memory layout

2. VALIDATE EXTRACTION
   * Check completeness (all expected tables found)
   * Verify consistency (valid addresses, no overlaps)
   * Confirm integrity (data structure is sound)

3. CHOOSE APPROPRIATE DRIVER
   * If Laxity: Choose Laxity driver for accuracy
   * If Driver11: Choose Driver 11 (100% compatible)
   * Consider memory constraints
   * Consider feature requirements

4. VALIDATE CONVERSION
   * Generate WAV files and compare
   * Check register trace output
   * Verify in multiple players (VICE, siddump, SID2WAV)
   * Manual correction if needed

5. TEST IN SF2 EDITOR
   * Load in SID Factory II
   * Test playback
   * Verify table editing (if supported)
   * Check audio quality


ACCURACY EXPECTATIONS:
------------------------------------------------------------------------------------------------------------------------

Source Format             -> Driver 11   -> NP20       -> Laxity Driver
------------------------------------------------------------------------------------------------------------------------
Laxity NewPlayer v21      1-8%         1-8%        70-90%
Driver 11                 100%         ~95%        N/A
JCH NewPlayer v20         ~95%         100%        N/A
SF2 Exported              100%         95%         N/A

========================================================================================================================