========================================================================================================================
SF2 DRIVER LIMITATIONS & CAVEATS REPORT
========================================================================================================================

Driver 11
------------------------------------------------------------------------------------------------------------------------
Version: SF2 Standard

Memory Requirements:
  * Code Size: 6656 bytes
  * Data Size: 2048 bytes
  * Max Tables: 5 bytes
  * Min Free: 512 bytes

Known Limitations:
  * No Laxity NewPlayer v21 specific features
  * Filter format incompatible with Laxity
  * Arpeggio implementation differs from Laxity

Table Formats Supported:
  * sequence       : 2 bytes per entry
  * instrument     : 8 bytes per entry, 32 max
  * wave           : 2 bytes per entry, 128 max
  * pulse          : 4 bytes per entry, 64 max
  * filter         : 4 bytes per entry, 32 max

Expected Conversion Accuracy: 100%


Laxity NewPlayer v21
------------------------------------------------------------------------------------------------------------------------
Version: v21

Memory Requirements:
  * Code Size: 2500 bytes
  * Data Size: 3000 bytes
  * Max Tables: 5 bytes
  * Min Free: 512 bytes

Known Limitations:
  * SF2 format conversion lossy
  * Filter format unique to Laxity
  * Advanced effects may not convert

Table Formats Supported:
  * sequence       : 2 bytes per entry
  * instrument     : 8 bytes per entry, 32 max
  * wave           : 2 bytes per entry, 128 max (row-major)
  * pulse          : 4 bytes per entry, 64 max (Y*4 indexing)
  * filter         : 4 bytes per entry, 32 max (Y*4 indexing)

Expected Conversion Accuracy: 70%


JCH NewPlayer v20
------------------------------------------------------------------------------------------------------------------------
Version: NP20

Memory Requirements:
  * Code Size: 5376 bytes
  * Data Size: 2048 bytes
  * Max Tables: 5 bytes
  * Min Free: 512 bytes

Known Limitations:
  * Smaller code size than Driver 11
  * Limited effect support
  * Filter format incompatible with Laxity

Table Formats Supported:
  * sequence       : 2 bytes per entry
  * instrument     : 8 bytes per entry, 32 max
  * wave           : 2 bytes per entry, 128 max
  * pulse          : 4 bytes per entry, 64 max
  * filter         : 4 bytes per entry, 32 max

Expected Conversion Accuracy: 95%


========================================================================================================================