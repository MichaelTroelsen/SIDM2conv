"""
Constants for SID to SF2 conversion.
"""

# SID chip register base address
SID_BASE = 0xD400

# SID register offsets
SID_FREQ_LO_1 = 0x00
SID_FREQ_HI_1 = 0x01
SID_PW_LO_1 = 0x02
SID_PW_HI_1 = 0x03
SID_CTRL_1 = 0x04
SID_AD_1 = 0x05
SID_SR_1 = 0x06

SID_FREQ_LO_2 = 0x07
SID_FREQ_HI_2 = 0x08
SID_PW_LO_2 = 0x09
SID_PW_HI_2 = 0x0A
SID_CTRL_2 = 0x0B
SID_AD_2 = 0x0C
SID_SR_2 = 0x0D

SID_FREQ_LO_3 = 0x0E
SID_FREQ_HI_3 = 0x0F
SID_PW_LO_3 = 0x10
SID_PW_HI_3 = 0x11
SID_CTRL_3 = 0x12
SID_AD_3 = 0x13
SID_SR_3 = 0x14

SID_FC_LO = 0x15
SID_FC_HI = 0x16
SID_RES_FILT = 0x17
SID_MODE_VOL = 0x18

# Waveform values
WAVEFORM_GATE = 0x01
WAVEFORM_SYNC = 0x02
WAVEFORM_RING = 0x04
WAVEFORM_TEST = 0x08
WAVEFORM_TRIANGLE = 0x10
WAVEFORM_SAWTOOTH = 0x20
WAVEFORM_PULSE = 0x40
WAVEFORM_NOISE = 0x80

# Valid waveform bytes for extraction
VALID_WAVEFORMS = {
    0x01,        # Gate only (used for hard restart)
    0x10, 0x11,  # Triangle, Triangle+Gate
    0x20, 0x21,  # Saw, Saw+Gate
    0x40, 0x41,  # Pulse, Pulse+Gate
    0x80, 0x81,  # Noise, Noise+Gate
    0x30, 0x31,  # Tri+Saw, Tri+Saw+Gate
    0x50, 0x51,  # Tri+Pulse, Tri+Pulse+Gate
    0x14, 0x15,  # Tri+Ring, Tri+Ring+Gate
    0x34, 0x35,  # Tri+Saw+Ring, Tri+Saw+Ring+Gate
    0x2E,        # Saw+Ring+Sync
    0xF0,        # All oscillators combined
}

# Extended waveform set for wave table extraction
WAVE_TABLE_WAVEFORMS = {
    0x01, 0x08, 0x0B, 0x0D, 0x10, 0x11, 0x15,
    0x20, 0x21, 0x2E, 0x40, 0x41, 0x80, 0x81, 0xF0, 0x00
}

# Table control bytes
TABLE_END = 0x7F
TABLE_LOOP = 0x7E
SEQUENCE_END = 0xFF

# Table sizes
MAX_INSTRUMENTS = 32
MAX_WAVE_ENTRIES = 128
MAX_PULSE_ENTRIES = 128
MAX_FILTER_ENTRIES = 128
MAX_SEQUENCES = 128
INSTRUMENT_SIZE = 8  # Bytes per instrument

# Memory layout
TYPICAL_LOAD_ADDRESS = 0x1000
PLAYER_CODE_SIZE = 0x800  # First 2KB typically player code
MEMORY_SIZE = 65536  # 64KB

# Search ranges for table finding
SEARCH_START_OFFSET = 0x800  # Offset from load_addr (after player code)
SEARCH_END_OFFSET = 0xC00    # Offset from load_addr

# Scoring thresholds
INSTRUMENT_SCORE_THRESHOLD = 6
MIN_VALID_INSTRUMENTS = 4
WAVE_TABLE_MIN_ENTRIES = 4
WAVE_TABLE_MIN_SCORE = 4

# Typical table address ranges
WAVE_TABLE_ADDR_MIN = 0x1900
WAVE_TABLE_ADDR_MAX = 0x1B00
PULSE_TABLE_ADDR_MIN = 0x1A38
PULSE_TABLE_ADDR_MAX = 0x1A50

# 6502 opcodes to avoid in instrument detection
OPCODE_BYTES = {
    0xAD, 0xBD, 0x8D, 0x9D, 0xA9, 0xA2, 0xA0, 0x4C, 0x20, 0x60,
    0xE8, 0xCA, 0xC8, 0x88, 0xAA, 0xA8, 0x8A, 0x98, 0xEA
}

# Common ADSR values
COMMON_AD_VALUES = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0F}
COMMON_SR_VALUES = {0xF8, 0xA8, 0x88, 0xDD, 0xF9, 0x9D, 0xCA, 0xCD, 0x7A, 0x9B}

# Valid filter settings
VALID_FILTER_SETTINGS = {0x00, 0xF1, 0xF0, 0x10, 0x20, 0x40, 0x80, 0x11, 0x21, 0x41, 0x01, 0x07}

# Valid restart options
VALID_RESTART_OPTIONS = {0x00, 0x10, 0x11, 0x12, 0x40, 0x80, 0x90}

# SF2 file format constants
SF2_FILE_ID = 0x1337
SF2_DRIVER_VERSION = 11

# SF2 header block IDs
BLOCK_DESCRIPTOR = 1
BLOCK_DRIVER_COMMON = 2
BLOCK_DRIVER_TABLES = 3
BLOCK_INSTRUMENT_DESC = 4
BLOCK_MUSIC_DATA = 5
BLOCK_END = 0xFF
