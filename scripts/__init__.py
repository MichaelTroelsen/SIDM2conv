"""
SIDM2 Scripts Package

This package contains all conversion, validation, and utility scripts for the SIDM2 project.

Main scripts:
- sid_to_sf2: Main SID to SF2 converter
- sf2_to_sid: SF2 to SID exporter
- convert_all: Batch conversion script

Test scripts:
- test_converter: Unit tests for converter
- test_sf2_format: SF2 format validation tests
- test_roundtrip: Round-trip validation tests
- test_complete_pipeline: Pipeline validation tests

Utility scripts:
- extract_addresses: Extract data structure addresses from SID files
- disassemble_sid: 6502 disassembler for SID files
- format_tables: Generate hex table views
- laxity_parser: Laxity player parser
- validate_psid: PSID header validation
- validate_sid_accuracy: SID accuracy validation
- generate_info: Info.txt generation
- generate_validation_report: Validation report generator
"""

__version__ = "0.7.1"
