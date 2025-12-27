#!/usr/bin/env python3
"""
SID to SID Factory II (.sf2) Converter - Command Line Interface

This is a thin CLI wrapper that imports business logic from sidm2.conversion_pipeline.
The conversion pipeline supports multiple conversion strategies with automatic driver
selection for optimal accuracy.

For business logic implementation, see: sidm2/conversion_pipeline.py

Usage:
    python scripts/sid_to_sf2.py input.sid output.sf2
    python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
    python scripts/sid_to_sf2.py input.sid output.sf2 --both

Note: This is a complex reverse-engineering task. Results may require manual
refinement in SID Factory II.
"""

__version__ = "0.7.1"
__build_date__ = "2025-12-07"

import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path so sidm2 module can be found
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import configuration system
from sidm2.config import ConversionConfig

# Import enhanced logging system
from sidm2.logging_config import setup_logging, configure_from_args, PerformanceLogger

# Import error handling module
from sidm2 import errors as sidm2_errors

# Import ALL business logic from conversion pipeline module
from sidm2.conversion_pipeline import (
    # Core conversion functions
    detect_player_type,
    print_success_summary,
    analyze_sid_file,
    convert_laxity_to_sf2,
    convert_galway_to_sf2,
    convert_sid_to_sf2,
    convert_sid_to_both_drivers,
    # Availability flags
    LAXITY_CONVERTER_AVAILABLE,
    GALWAY_CONVERTER_AVAILABLE,
    SIDWINDER_INTEGRATION_AVAILABLE,
    DISASSEMBLER_INTEGRATION_AVAILABLE,
    AUDIO_EXPORT_INTEGRATION_AVAILABLE,
    MEMMAP_ANALYZER_AVAILABLE,
    PATTERN_RECOGNIZER_AVAILABLE,
    SUBROUTINE_TRACER_AVAILABLE,
    REPORT_GENERATOR_AVAILABLE,
    OUTPUT_ORGANIZER_AVAILABLE,
    SIDDUMP_INTEGRATION_AVAILABLE,
    ACCURACY_INTEGRATION_AVAILABLE,
)

# Import optional integrations (for CLI tool orchestration)
if SIDWINDER_INTEGRATION_AVAILABLE:
    from sidm2.sidwinder_wrapper import SIDwinderIntegration

if DISASSEMBLER_INTEGRATION_AVAILABLE:
    from sidm2.disasm_wrapper import DisassemblerIntegration

if AUDIO_EXPORT_INTEGRATION_AVAILABLE:
    from sidm2.audio_export_wrapper import AudioExportIntegration

if MEMMAP_ANALYZER_AVAILABLE:
    from sidm2.memmap_analyzer import MemoryMapAnalyzer

if PATTERN_RECOGNIZER_AVAILABLE:
    from sidm2.pattern_recognizer import PatternRecognizer

if SUBROUTINE_TRACER_AVAILABLE:
    from sidm2.subroutine_tracer import SubroutineTracer

if REPORT_GENERATOR_AVAILABLE:
    from sidm2.report_generator import ReportGenerator

if OUTPUT_ORGANIZER_AVAILABLE:
    from sidm2.output_organizer import OutputOrganizer

if SIDDUMP_INTEGRATION_AVAILABLE:
    from sidm2.siddump_integration import SiddumpIntegration

if ACCURACY_INTEGRATION_AVAILABLE:
    from sidm2.accuracy_integration import AccuracyIntegration

# Get module logger (will be configured in main())
from sidm2.logging_config import get_logger
logger = get_logger(__name__)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='SID to SF2 Converter - Convert Laxity SID files to SID Factory II format',
        epilog='''Examples:
  # Auto-detect driver (recommended)
  %(prog)s music.sid output.sf2

  # Use specific driver
  %(prog)s music.sid output.sf2 --driver laxity

  # Quiet mode for scripts
  %(prog)s music.sid output.sf2 --quiet

  # With analysis tools
  %(prog)s music.sid output.sf2 --trace --disasm

For more help, see README.md or docs/guides/''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('input', help='Input SID file')
    parser.add_argument('output', nargs='?', help='Output SF2 file (default: input name with .sf2)')

    # Configuration
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path (JSON format, see sidm2_config.example.json)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing output files'
    )

    # Driver selection - mutually exclusive
    driver_group = parser.add_mutually_exclusive_group()
    driver_group.add_argument(
        '--driver', '-d',
        choices=['np20', 'driver11', 'laxity', 'galway'],
        help='''Target driver type (default: auto-detected).

Recommended drivers by source:
  laxity    - Laxity NewPlayer v21 (99.93%% accuracy) [BEST]
  driver11  - SF2-exported SIDs (100%% accuracy)
  np20      - NewPlayer 20.G4 (70-90%% accuracy)
  galway    - Martin Galway players

Example: --driver laxity'''
    )
    driver_group.add_argument(
        '--both', '-b',
        action='store_true',
        help='Generate both NP20 (_g4.sf2) and Driver 11 (_d11.sf2) versions'
    )

    parser.add_argument(
        '--output-dir', '-o',
        help='Output directory for --both mode (default: from config or same as input)'
    )
    parser.add_argument(
        '--sf2-reference', '-r',
        help='Path to original SF2 file (for SF2-exported SIDs, enables accurate sequence extraction)'
    )
    parser.add_argument(
        '--use-midi',
        action='store_true',
        help='Use MIDI-based sequence extraction (Python emulator, high accuracy)'
    )

    # Optional analysis tools (enhanced pipeline v2.0.0)
    parser.add_argument(
        '--trace',
        action='store_true',
        help='Enable SIDwinder trace generation (Step 7.5 - detailed frame-by-frame register tracing)'
    )
    parser.add_argument(
        '--trace-frames',
        type=int,
        default=1500,
        help='Number of frames for SIDwinder trace (default: 1500 = 30s @ 50Hz PAL)'
    )
    parser.add_argument(
        '--disasm',
        action='store_true',
        help='Enable 6502 disassembly (Step 8.5 - disassemble init and play routines to .asm files)'
    )
    parser.add_argument(
        '--audio-export',
        action='store_true',
        help='Export to WAV audio (Step 16 - generate reference audio for listening). Note: PSID files only, RSID not supported by SID2WAV v1.8'
    )
    parser.add_argument(
        '--audio-duration',
        type=int,
        default=30,
        help='Audio export duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--memmap',
        action='store_true',
        help='Generate memory map analysis (Step 12.5 - analyze memory layout and regions)'
    )
    parser.add_argument(
        '--patterns',
        action='store_true',
        help='Generate pattern analysis (Step 17 - identify repeating patterns and optimization opportunities)'
    )
    parser.add_argument(
        '--callgraph',
        action='store_true',
        help='Generate call graph analysis (Step 18 - trace subroutine calls and build call graph)'
    )
    parser.add_argument(
        '--siddump',
        action='store_true',
        help='Generate siddump frame analysis for original and exported SIDs (Step 7.6)'
    )

    parser.add_argument(
        '--siddump-duration',
        type=int,
        default=30,
        metavar='SECONDS',
        help='Duration for siddump analysis in seconds (default: 30)'
    )

    parser.add_argument(
        '--validate-accuracy',
        action='store_true',
        help='Validate conversion accuracy by comparing original vs exported SID (Step 21)'
    )

    parser.add_argument(
        '--organize',
        action='store_true',
        help='Organize analysis outputs into structured directories (Step 20 - final organization)'
    )

    # Logging arguments (enhanced logging system v2.0.0)
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=2,
        help='Increase verbosity (-v=INFO, -vv=DEBUG). Default: INFO level'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode for automation (minimal output, errors only). Exit code: 0=success, 1=failure'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode (maximum verbosity, same as -vv)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Write logs to file (with automatic rotation)'
    )
    parser.add_argument(
        '--log-json',
        action='store_true',
        help='Use JSON log format (for log aggregation tools)'
    )

    args = parser.parse_args()

    # Load configuration
    if args.config:
        if not os.path.exists(args.config):
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)
        try:
            config = ConversionConfig.load(args.config)
        except Exception as e:
            print(f"Error: Failed to load configuration: {e}")
            sys.exit(1)
    else:
        config = ConversionConfig()

    # Apply config overrides from CLI args
    if args.overwrite:
        config.output.overwrite = True

    # Configure logging system from CLI args (Enhanced Logging System v2.0.0)
    configure_from_args(args)

    try:
        # Validate input file
        input_file = args.input
        if not os.path.exists(input_file):
            raise sidm2_errors.FileNotFoundError(
                path=input_file,
                context="input SID file",
                suggestions=[
                    f"Check the file path: {sys.argv[0]} --help",
                    "Use absolute path instead of relative",
                    f"List files in directory: dir {os.path.dirname(input_file) or '.'}"
                ],
                docs_link="README.md#usage"
            )

        # Handle both drivers mode
        if args.both:
            # Both drivers mode
            output_dir = args.output_dir
            with PerformanceLogger(logger, f"SID to SF2 conversion (both drivers): {input_file}"):
                convert_sid_to_both_drivers(input_file, output_dir, config=config)
        else:
            # Single driver mode
            if args.output:
                output_file = args.output
            else:
                # Generate output filename
                base = os.path.splitext(input_file)[0]
                output_file = base + ".sf2"

            # Use CLI driver arg or fall back to config
            driver_type = args.driver
            sf2_reference = args.sf2_reference if hasattr(args, 'sf2_reference') else None
            use_midi = args.use_midi if hasattr(args, 'use_midi') else False

            with PerformanceLogger(logger, f"SID to SF2 conversion ({driver_type}): {input_file}"):
                convert_sid_to_sf2(input_file, output_file, driver_type=driver_type, config=config, sf2_reference_path=sf2_reference, use_midi=use_midi, quiet=args.quiet)

        # Initialize tool statistics tracking
        tool_stats = {}

        # PHASE 5 Enhancement: Optional SIDwinder trace (Step 7.5)
        if args.trace and SIDWINDER_INTEGRATION_AVAILABLE:
            # Run optional SIDwinder tracing after conversion
            # Determine output directory for trace file
            if args.both:
                trace_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                trace_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = trace_output_dir / "analysis"

            logger.info("")
            logger.info("=" * 60)
            logger.info("[Phase 5] Running optional analysis tools...")
            logger.info("=" * 60)

            start_time = time.time()
            trace_result = SIDwinderIntegration.trace_sid(
                sid_file=Path(input_file),
                output_dir=analysis_dir,
                frames=args.trace_frames,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['SIDwinder Tracer'] = {
                'executed': True,
                'success': trace_result and trace_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if trace_result and trace_result['success'] else 0
            }

            if trace_result and trace_result['success']:
                logger.info(f"[Step 7.5] SIDwinder trace complete:")
                logger.info(f"  Trace file: {trace_result['trace_file']}")
                logger.info(f"  Frames:     {trace_result['frames']}")
                logger.info(f"  Cycles:     {trace_result['cycles']:,}")
                logger.info(f"  Writes:     {trace_result['writes']:,}")
                logger.info(f"  Size:       {trace_result['file_size']:,} bytes")
            elif args.trace:
                logger.warning("[Step 7.5] SIDwinder trace failed (continuing anyway)")

        # PHASE 2 Enhancement: Optional 6502 disassembly (Step 8.5)
        if args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE:
            # Run optional disassembly after conversion
            # Determine output directory for .asm files
            if args.both:
                disasm_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                disasm_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = disasm_output_dir / "analysis"

            # Only print header if we didn't already print it for trace
            if not (args.trace and SIDWINDER_INTEGRATION_AVAILABLE):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            start_time = time.time()
            disasm_result = DisassemblerIntegration.disassemble_sid(
                sid_file=Path(input_file),
                output_dir=analysis_dir,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['6502 Disassembler'] = {
                'executed': True,
                'success': disasm_result and disasm_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 2 if disasm_result and disasm_result['success'] else 0
            }

            if disasm_result and disasm_result['success']:
                logger.info(f"[Step 8.5] 6502 disassembly complete:")
                logger.info(f"  Init file:  {disasm_result['init_file'].name} ({disasm_result['init_lines']} instructions)")
                logger.info(f"  Play file:  {disasm_result['play_file'].name} ({disasm_result['play_lines']} instructions)")
                logger.info(f"  Init addr:  ${disasm_result['init_addr']:04X}")
                logger.info(f"  Play addr:  ${disasm_result['play_addr']:04X}")
            elif args.disasm:
                logger.warning("[Step 8.5] 6502 disassembly failed (continuing anyway)")

        # PHASE 2 Enhancement: Optional audio export (Step 16)
        if args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE:
            # Determine output directory for WAV files
            if args.both:
                audio_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                audio_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = audio_output_dir / "analysis"

            # Only print header if we didn't already print it for trace or disasm
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate WAV filename
            wav_file = analysis_dir / f"{Path(input_file).stem}.wav"

            start_time = time.time()
            audio_result = AudioExportIntegration.export_to_wav(
                sid_file=Path(input_file),
                output_file=wav_file,
                duration=args.audio_duration,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['Audio Exporter'] = {
                'executed': True,
                'success': audio_result and audio_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if audio_result and audio_result['success'] else 0
            }

            if audio_result and audio_result['success']:
                logger.info(f"[Step 16] Audio export complete:")
                logger.info(f"  WAV file:   {audio_result['output_file'].name}")
                logger.info(f"  Duration:   {audio_result['duration']}s")
                logger.info(f"  Format:     {audio_result['frequency']}Hz, {audio_result['bit_depth']}-bit, {'stereo' if audio_result['stereo'] else 'mono'}")
                logger.info(f"  Size:       {audio_result['file_size']:,} bytes")
            elif audio_result and not audio_result['success']:
                logger.warning(f"[Step 16] Audio export failed: {audio_result.get('error', 'Unknown error')}")
                logger.warning("  Note: SID2WAV v1.8 only supports PSID files, not RSID files")
            elif args.audio_export:
                logger.warning("[Step 16] Audio export not available (SID2WAV.EXE not found)")

        # PHASE 3 Enhancement: Optional memory map analysis (Step 12.5)
        if args.memmap and MEMMAP_ANALYZER_AVAILABLE:
            # Determine output directory for memory map
            if args.both:
                memmap_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                memmap_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = memmap_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate memory map filename
            memmap_file = analysis_dir / f"{Path(input_file).stem}_memmap.txt"

            # Create analyzer and run analysis
            analyzer = MemoryMapAnalyzer(Path(input_file))
            start_time = time.time()
            memmap_result = analyzer.analyze(verbose=1 if not args.quiet else 0)
            tool_stats['Memory Map Analyzer'] = {
                'executed': True,
                'success': memmap_result and memmap_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if memmap_result and memmap_result['success'] else 0
            }

            if memmap_result and memmap_result['success']:
                # Generate report
                report_success = analyzer.generate_report(memmap_result, memmap_file)

                if report_success:
                    logger.info(f"[Step 12.5] Memory map analysis complete:")
                    logger.info(f"  Report file: {memmap_file.name}")
                    logger.info(f"  Load addr:   ${memmap_result['load_addr']:04X}")
                    logger.info(f"  End addr:    ${memmap_result['end_addr']:04X}")
                    logger.info(f"  Total size:  {memmap_result['total_size']} bytes")
                    logger.info(f"  Code:        {memmap_result['code_size']} bytes ({memmap_result['code_size']*100//memmap_result['total_size'] if memmap_result['total_size'] > 0 else 0}%)")
                    logger.info(f"  Data:        {memmap_result['data_size']} bytes ({memmap_result['data_size']*100//memmap_result['total_size'] if memmap_result['total_size'] > 0 else 0}%)")
                else:
                    logger.warning("[Step 12.5] Memory map report generation failed")
            elif args.memmap:
                logger.warning("[Step 12.5] Memory map analysis failed (continuing anyway)")

        # PHASE 3 Enhancement: Optional pattern analysis (Step 17)
        if args.patterns and PATTERN_RECOGNIZER_AVAILABLE:
            # Determine output directory for pattern analysis
            if args.both:
                patterns_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                patterns_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = patterns_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate pattern analysis filename
            patterns_file = analysis_dir / f"{Path(input_file).stem}_patterns.txt"

            # Create recognizer and run analysis
            recognizer = PatternRecognizer(Path(input_file))
            start_time = time.time()
            patterns_result = recognizer.analyze(verbose=1 if not args.quiet else 0)
            tool_stats['Pattern Recognizer'] = {
                'executed': True,
                'success': patterns_result and patterns_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if patterns_result and patterns_result['success'] else 0
            }

            if patterns_result and patterns_result['success']:
                # Generate report
                report_success = recognizer.generate_report(patterns_result, patterns_file)

                if report_success:
                    logger.info(f"[Step 17] Pattern analysis complete:")
                    logger.info(f"  Report file: {patterns_file.name}")
                    logger.info(f"  Patterns:    {patterns_result['pattern_count']}")
                    logger.info(f"  Repeats:     {patterns_result['repeat_count']}")
                    logger.info(f"  Savings:     {patterns_result['potential_savings']} bytes ({patterns_result['potential_savings']*100//patterns_result['total_size'] if patterns_result['total_size'] > 0 else 0}%)")
                else:
                    logger.warning("[Step 17] Pattern analysis report generation failed")
            elif args.patterns:
                logger.warning("[Step 17] Pattern analysis failed (continuing anyway)")

        # PHASE 3 Enhancement: Optional call graph analysis (Step 18)
        if args.callgraph and SUBROUTINE_TRACER_AVAILABLE:
            # Determine output directory for call graph
            if args.both:
                callgraph_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                callgraph_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = callgraph_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE) or
                    (args.patterns and PATTERN_RECOGNIZER_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            # Generate call graph filename
            callgraph_file = analysis_dir / f"{Path(input_file).stem}_callgraph.txt"

            # Create tracer and run analysis
            tracer = SubroutineTracer(Path(input_file))
            start_time = time.time()
            callgraph_result = tracer.trace(verbose=1 if not args.quiet else 0)
            tool_stats['Subroutine Tracer'] = {
                'executed': True,
                'success': callgraph_result and callgraph_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if callgraph_result and callgraph_result['success'] else 0
            }

            if callgraph_result and callgraph_result['success']:
                # Generate report
                report_success = tracer.generate_report(callgraph_result, callgraph_file)

                if report_success:
                    logger.info(f"[Step 18] Call graph analysis complete:")
                    logger.info(f"  Report file:   {callgraph_file.name}")
                    logger.info(f"  Subroutines:   {callgraph_result['subroutine_count']}")
                    logger.info(f"  Calls:         {callgraph_result['call_count']}")
                    logger.info(f"  Max depth:     {callgraph_result['max_depth']}")
                    logger.info(f"  Entry points:  {callgraph_result['entry_points']}")
                else:
                    logger.warning("[Step 18] Call graph report generation failed")
            elif args.callgraph:
                logger.warning("[Step 18] Call graph analysis failed (continuing anyway)")

        # PHASE 4 Enhancement: Optional siddump analysis (Step 7.6)
        if args.siddump and SIDDUMP_INTEGRATION_AVAILABLE:
            # Determine output directory for siddump analysis
            if args.both:
                siddump_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                siddump_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = siddump_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE) or
                    (args.patterns and PATTERN_RECOGNIZER_AVAILABLE) or
                    (args.callgraph and SUBROUTINE_TRACER_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            start_time = time.time()
            siddump_result = SiddumpIntegration.analyze_sid(
                sid_file=Path(input_file),
                output_dir=analysis_dir,
                duration=args.siddump_duration,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['Siddump Analyzer'] = {
                'executed': True,
                'success': siddump_result and siddump_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 2 if siddump_result and siddump_result['success'] else 0
            }

            if siddump_result and siddump_result['success']:
                logger.info(f"[Step 7.6] Siddump analysis complete:")
                logger.info(f"  Original:   {siddump_result['original_file'].name} ({siddump_result['original_frames']} frames)")
                logger.info(f"  Exported:   {siddump_result['exported_file'].name} ({siddump_result['exported_frames']} frames)")
                logger.info(f"  Duration:   {args.siddump_duration}s")
            elif args.siddump:
                logger.warning("[Step 7.6] Siddump analysis failed (continuing anyway)")

        # PHASE 4 Enhancement: Optional accuracy validation (Step 21)
        if args.validate_accuracy and ACCURACY_INTEGRATION_AVAILABLE:
            # Determine output directory for accuracy report
            if args.both:
                accuracy_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                accuracy_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = accuracy_output_dir / "analysis"

            # Only print header if we didn't already print it for other tools
            if not ((args.trace and SIDWINDER_INTEGRATION_AVAILABLE) or
                    (args.disasm and DISASSEMBLER_INTEGRATION_AVAILABLE) or
                    (args.audio_export and AUDIO_EXPORT_INTEGRATION_AVAILABLE) or
                    (args.memmap and MEMMAP_ANALYZER_AVAILABLE) or
                    (args.patterns and PATTERN_RECOGNIZER_AVAILABLE) or
                    (args.callgraph and SUBROUTINE_TRACER_AVAILABLE) or
                    (args.siddump and SIDDUMP_INTEGRATION_AVAILABLE)):
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            start_time = time.time()
            accuracy_result = AccuracyIntegration.validate_conversion(
                original_sid=Path(input_file),
                output_dir=analysis_dir,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['Accuracy Validator'] = {
                'executed': True,
                'success': accuracy_result and accuracy_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 1 if accuracy_result and accuracy_result['success'] else 0
            }

            if accuracy_result and accuracy_result['success']:
                logger.info(f"[Step 21] Accuracy validation complete:")
                logger.info(f"  Report file:  {accuracy_result['report_file'].name}")
                logger.info(f"  Accuracy:     {accuracy_result['accuracy']:.2f}%")
                logger.info(f"  Matches:      {accuracy_result['matches']:,}/{accuracy_result['total']:,} frames")
                logger.info(f"  Duration:     {accuracy_result['duration']}s")
            elif args.validate_accuracy:
                logger.warning("[Step 21] Accuracy validation failed (continuing anyway)")

        # PHASE 5 Enhancement: Optional output organization (Step 20)
        if args.organize and OUTPUT_ORGANIZER_AVAILABLE:
            # Determine output directory for organization
            if args.both:
                organize_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                organize_output_dir = Path(output_file).parent

            # Only print header if we didn't already print it for other tools
            if not (tool_stats):  # If no other tools ran
                logger.info("")
                logger.info("=" * 60)
                logger.info("[Phase 5] Running optional analysis tools...")
                logger.info("=" * 60)

            start_time = time.time()
            organize_result = OutputOrganizer.organize_outputs(
                output_dir=organize_output_dir,
                verbose=1 if not args.quiet else 0
            )
            tool_stats['Output Organizer'] = {
                'executed': True,
                'success': organize_result and organize_result['success'],
                'duration': time.time() - start_time,
                'files_generated': 0  # Moves files, doesn't generate new ones
            }

            if organize_result and organize_result['success']:
                logger.info(f"[Step 20] Output organization complete:")
                logger.info(f"  Files moved:   {organize_result['files_moved']}")
                logger.info(f"  Directories:   {organize_result['directories_created']}")
                logger.info(f"  Output dir:    {organize_result['output_dir']}")
            elif args.organize:
                logger.warning("[Step 20] Output organization failed (continuing anyway)")

        # PHASE 5 Enhancement: Report generation (Step 19)
        if tool_stats and REPORT_GENERATOR_AVAILABLE:
            # Generate consolidated report
            if args.both:
                report_output_dir = Path(args.output_dir) if args.output_dir else Path(input_file).parent
            else:
                report_output_dir = Path(output_file).parent

            # Create analysis subdirectory
            analysis_dir = report_output_dir / "analysis"
            analysis_dir.mkdir(exist_ok=True)

            logger.info("")
            logger.info("=" * 60)
            logger.info("[Phase 6] Generating consolidated analysis report...")
            logger.info("=" * 60)

            report_file = analysis_dir / f"{Path(input_file).stem}_report.txt"
            report_generator = ReportGenerator()
            report_success = report_generator.generate_consolidated_report(
                input_file=Path(input_file),
                tool_stats=tool_stats,
                output_file=report_file,
                verbose=1 if not args.quiet else 0
            )

            if report_success:
                logger.info(f"[Step 19] Consolidated report generated:")
                logger.info(f"  Report file: {report_file.name}")
                logger.info(f"  Tools run:   {len([t for t in tool_stats.values() if t.get('executed')])}")
                logger.info(f"  Successful:  {len([t for t in tool_stats.values() if t.get('success')])}")
                logger.info(f"  Total time:  {sum(t.get('duration', 0) for t in tool_stats.values()):.2f}s")
            else:
                logger.warning("[Step 19] Consolidated report generation failed")

        # Exit with success
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except sidm2_errors.SIDMError as e:
        # Our custom errors already have helpful formatted messages
        if not args.quiet:
            print(f"\n{e}\n", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        # Unexpected errors
        logger.error(
            f"Unexpected error: {e}\n"
            f"  Suggestion: SID to SF2 conversion encountered unexpected error\n"
            f"  Check: Review error trace for specific issue\n"
            f"  Try: Enable debug mode (--debug) for detailed logging\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#unexpected-errors"
        )
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
