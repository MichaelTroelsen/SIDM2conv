"""
Output Organizer for SID Conversion Pipeline - Phase 4

Organizes all analysis outputs into a clean, structured directory layout.
Integrated into the conversion pipeline as Step 20 (FINAL TOOL).

Usage:
    from sidm2.output_organizer import OutputOrganizer

    organizer = OutputOrganizer(
        analysis_dir=Path("output/analysis")
    )
    result = organizer.organize()
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import shutil
import logging

logger = logging.getLogger(__name__)


class OutputOrganizer:
    """Organizes analysis outputs into structured directories"""

    # File categories and their target subdirectories
    CATEGORIES = {
        'disassembly': {
            'suffixes': ['.asm'],
            'patterns': ['_init.asm', '_play.asm'],
            'description': '6502 disassembly files'
        },
        'reports': {
            'suffixes': ['.txt', '.dump'],
            'patterns': ['_memmap.txt', '_patterns.txt', '_callgraph.txt',
                        '_trace.txt', '_REPORT.txt', '_accuracy.txt', '.dump'],
            'description': 'Analysis reports, traces, and siddump outputs'
        },
        'audio': {
            'suffixes': ['.wav', '.mp3', '.ogg'],
            'patterns': ['.wav'],
            'description': 'Audio exports'
        },
        'binary': {
            'suffixes': ['.prg', '.bin', '.dat', '.sid'],
            'patterns': ['.prg', '.sid'],
            'description': 'Binary files (SID files, PRG files)'
        }
    }

    def __init__(self, analysis_dir: Path):
        """
        Initialize output organizer.

        Args:
            analysis_dir: Directory containing analysis outputs
        """
        self.analysis_dir = Path(analysis_dir)
        self.organized_files = {}

    def _categorize_file(self, file_path: Path) -> Optional[str]:
        """
        Determine category for a file.

        Args:
            file_path: Path to file

        Returns:
            Category name or None if no match
        """
        file_name = file_path.name.lower()
        file_suffix = file_path.suffix.lower()

        # Check each category
        for category, config in self.CATEGORIES.items():
            # Check patterns first (more specific)
            for pattern in config.get('patterns', []):
                if file_name.endswith(pattern.lower()):
                    return category

            # Check suffixes
            if file_suffix in config.get('suffixes', []):
                return category

        return None

    def _scan_files(self) -> Dict[str, List[Path]]:
        """
        Scan analysis directory and categorize files.

        Returns:
            Dictionary mapping category to list of files
        """
        if not self.analysis_dir.exists():
            return {}

        categorized = {category: [] for category in self.CATEGORIES.keys()}
        categorized['uncategorized'] = []

        # Scan all files (non-recursive for now)
        for file_path in self.analysis_dir.iterdir():
            if file_path.is_file():
                # Skip INDEX.txt and README.md (these are organizer-generated files)
                if file_path.name in ['INDEX.txt', 'README.md']:
                    continue

                category = self._categorize_file(file_path)
                if category:
                    categorized[category].append(file_path)
                else:
                    categorized['uncategorized'].append(file_path)

        return categorized

    def _create_directory_structure(self, dry_run: bool = False) -> Dict[str, Path]:
        """
        Create organized directory structure.

        Args:
            dry_run: If True, don't actually create directories

        Returns:
            Dictionary mapping category to directory path
        """
        directories = {}

        for category in self.CATEGORIES.keys():
            category_dir = self.analysis_dir / category
            directories[category] = category_dir

            if not dry_run and not category_dir.exists():
                category_dir.mkdir(parents=True, exist_ok=True)

        return directories

    def _move_files(
        self,
        categorized: Dict[str, List[Path]],
        directories: Dict[str, Path],
        dry_run: bool = False,
        verbose: int = 0
    ) -> Dict[str, int]:
        """
        Move files to their categorized directories.

        Args:
            categorized: Dictionary of categorized files
            directories: Dictionary of target directories
            dry_run: If True, don't actually move files
            verbose: Verbosity level

        Returns:
            Dictionary with move statistics
        """
        stats = {
            'moved': 0,
            'skipped': 0,
            'errors': 0
        }

        for category, files in categorized.items():
            if category == 'uncategorized' or not files:
                continue

            target_dir = directories.get(category)
            if not target_dir:
                continue

            for file_path in files:
                try:
                    target_path = target_dir / file_path.name

                    # Skip if already in target directory
                    if file_path.parent == target_dir:
                        stats['skipped'] += 1
                        continue

                    # Skip if target already exists
                    if target_path.exists():
                        if verbose > 0:
                            logger.warning(f"Target exists, skipping: {target_path.name}")
                        stats['skipped'] += 1
                        continue

                    if not dry_run:
                        shutil.move(str(file_path), str(target_path))
                        stats['moved'] += 1

                        if verbose > 1:
                            print(f"  Moved: {file_path.name} -> {category}/")

                except Exception as e:
                    error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                    logger.error(f"Failed to move {file_path.name}: {error_msg}")
                    stats['errors'] += 1

        return stats

    def _create_index(
        self,
        categorized: Dict[str, List[Path]],
        directories: Dict[str, Path],
        output_file: Path,
        verbose: int = 0
    ) -> bool:
        """
        Create index file listing all organized files.

        Args:
            categorized: Dictionary of categorized files
            directories: Dictionary of target directories
            output_file: Path to index file
            verbose: Verbosity level

        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Header
                f.write("=" * 70 + "\n")
                f.write("ANALYSIS OUTPUT INDEX\n")
                f.write("=" * 70 + "\n\n")

                # Generation info
                f.write("ORGANIZATION INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"Generated:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Directory:   {self.analysis_dir}\n")
                f.write("\n")

                # Summary
                total_files = sum(len(files) for files in categorized.values())
                f.write("SUMMARY\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total files:       {total_files}\n")
                f.write(f"Categories:        {len([c for c in categorized if categorized[c]])}\n")
                f.write("\n")

                # Categories
                f.write("FILE ORGANIZATION\n")
                f.write("-" * 70 + "\n\n")

                for category, files in sorted(categorized.items()):
                    if not files:
                        continue

                    # Category header
                    category_title = category.upper()
                    description = self.CATEGORIES.get(category, {}).get('description', '')

                    f.write(f"{category_title}\n")
                    if description:
                        f.write(f"  {description}\n")
                    f.write(f"  Location: {category}/\n")
                    f.write(f"  Files:    {len(files)}\n\n")

                    # File list
                    for file_path in sorted(files, key=lambda p: p.name):
                        size = file_path.stat().st_size if file_path.exists() else 0
                        f.write(f"    {file_path.name:<40} ({size:,} bytes)\n")

                    f.write("\n")

                # Uncategorized files
                if categorized.get('uncategorized'):
                    f.write("UNCATEGORIZED FILES\n")
                    f.write("-" * 70 + "\n")
                    for file_path in sorted(categorized['uncategorized'], key=lambda p: p.name):
                        size = file_path.stat().st_size if file_path.exists() else 0
                        f.write(f"  {file_path.name:<40} ({size:,} bytes)\n")
                    f.write("\n")

                # Footer
                f.write("=" * 70 + "\n")
                f.write("End of index\n")
                f.write("=" * 70 + "\n")

            return True

        except Exception as e:
            error_msg = str(e).encode('ascii', 'replace').decode('ascii')
            logger.error(f"Failed to create index: {error_msg}")
            return False

    def _create_readme(
        self,
        categorized: Dict[str, List[Path]],
        output_file: Path,
        tool_stats: Optional[Dict[str, Any]] = None,
        verbose: int = 0
    ) -> bool:
        """
        Create README file with usage instructions.

        Args:
            categorized: Dictionary of categorized files
            output_file: Path to README file
            tool_stats: Optional dictionary with tool execution statistics
            verbose: Verbosity level

        Returns:
            True if successful
        """
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# Analysis Output Directory\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                f.write("## Directory Structure\n\n")
                f.write("Files have been organized into the following categories:\n\n")

                for category, config in self.CATEGORIES.items():
                    if categorized.get(category):
                        f.write(f"### `{category}/`\n")
                        f.write(f"{config['description']}\n\n")
                        f.write(f"- **File count**: {len(categorized[category])}\n")
                        f.write(f"- **File types**: {', '.join(config['suffixes'])}\n\n")

                # Add tool execution statistics if provided
                if tool_stats:
                    f.write("## Analysis Tools Used\n\n")
                    f.write("The following tools were used to generate these files:\n\n")

                    total_time = 0.0
                    for tool_name, stats in sorted(tool_stats.items()):
                        if stats.get('executed'):
                            status = "✅" if stats.get('success') else "⚠️"
                            duration = stats.get('duration', 0.0)
                            total_time += duration

                            f.write(f"- **{tool_name}** {status}\n")
                            f.write(f"  - Execution time: {duration:.2f}s\n")
                            if stats.get('files_generated'):
                                f.write(f"  - Files generated: {stats['files_generated']}\n")
                            f.write("\n")

                    f.write(f"**Total analysis time**: {total_time:.2f}s\n\n")

                f.write("## File Descriptions\n\n")

                f.write("### Binary Files\n")
                f.write("- `*.sid` - Original SID file and exported SID from SF2\n\n")

                f.write("### Disassembly Files\n")
                f.write("- `*_init.asm` - Disassembly of initialization routine\n")
                f.write("- `*_play.asm` - Disassembly of play routine\n\n")

                f.write("### Report Files\n")
                f.write("- `*_memmap.txt` - Memory map analysis\n")
                f.write("- `*_patterns.txt` - Pattern recognition analysis\n")
                f.write("- `*_callgraph.txt` - Subroutine call graph\n")
                f.write("- `*_trace.txt` - SID register trace\n")
                f.write("- `*_REPORT.txt` - Consolidated analysis report\n")
                f.write("- `*.dump` - Siddump frame-by-frame analysis\n")
                f.write("- `*_accuracy.txt` - Accuracy validation report\n")
                f.write("- `info.txt` - Conversion metadata and driver information\n\n")

                f.write("### Audio Files\n")
                f.write("- `*.wav` - Audio export for reference listening\n\n")

                f.write("## Quick Start\n\n")
                f.write("1. Start with `*_REPORT.txt` for an overview of all analyses\n")
                f.write("2. Check `audio/*.wav` to hear the music\n")
                f.write("3. Review `reports/*_memmap.txt` for memory layout\n")
                f.write("4. Examine `disassembly/*.asm` for code details\n")
                f.write("5. Use `binary/*.sid` files for playback in SID players\n\n")

                f.write("## Additional Information\n\n")
                f.write("For detailed file listings, see `INDEX.txt`\n\n")
                f.write("Generated by SIDM2 Output Organizer v" + __version__ + "\n")

            return True

        except Exception as e:
            error_msg = str(e).encode('ascii', 'replace').decode('ascii')
            logger.error(f"Failed to create README: {error_msg}")
            return False

    def organize(
        self,
        dry_run: bool = False,
        create_index: bool = True,
        create_readme: bool = True,
        tool_stats: Optional[Dict[str, Any]] = None,
        verbose: int = 0
    ) -> Dict[str, Any]:
        """
        Organize analysis outputs into structured directories.

        Args:
            dry_run: If True, simulate organization without moving files
            create_index: Create INDEX.txt file
            create_readme: Create README.md file
            tool_stats: Optional dictionary with tool execution statistics
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with organization results
        """
        try:
            if not self.analysis_dir.exists():
                return {
                    'success': False,
                    'error': f'Analysis directory does not exist: {self.analysis_dir}'
                }

            # Scan and categorize files
            categorized = self._scan_files()
            total_files = sum(len(files) for files in categorized.values())

            if total_files == 0:
                if verbose > 0:
                    logger.warning("No files found to organize")
                return {
                    'success': False,
                    'error': 'No files found to organize'
                }

            # Create directory structure
            directories = self._create_directory_structure(dry_run=dry_run)

            # Move files
            move_stats = self._move_files(categorized, directories, dry_run=dry_run, verbose=verbose)

            # Create index
            index_success = False
            if create_index and not dry_run:
                index_file = self.analysis_dir / "INDEX.txt"
                index_success = self._create_index(categorized, directories, index_file, verbose=verbose)

            # Create README
            readme_success = False
            if create_readme and not dry_run:
                readme_file = self.analysis_dir / "README.md"
                readme_success = self._create_readme(categorized, readme_file, tool_stats=tool_stats, verbose=verbose)

            result = {
                'success': True,
                'dry_run': dry_run,
                'total_files': total_files,
                'moved': move_stats['moved'],
                'skipped': move_stats['skipped'],
                'errors': move_stats['errors'],
                'categories': {cat: len(files) for cat, files in categorized.items() if files},
                'index_created': index_success,
                'readme_created': readme_success
            }

            if verbose > 0:
                mode = "DRY RUN" if dry_run else "ORGANIZED"
                print(f"  Output {mode.lower()}")
                print(f"    Total files:  {total_files}")
                print(f"    Moved:        {move_stats['moved']}")
                print(f"    Skipped:      {move_stats['skipped']}")
                print(f"    Errors:       {move_stats['errors']}")
                if create_index and index_success:
                    print(f"    Index:        INDEX.txt")
                if create_readme and readme_success:
                    print(f"    README:       README.md")

            return result

        except Exception as e:
            error_msg = str(e).encode('ascii', 'replace').decode('ascii')
            if verbose > 0:
                logger.error(f"Organization failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience function
def organize_output(
    analysis_dir: Path,
    dry_run: bool = False,
    create_index: bool = True,
    create_readme: bool = True,
    tool_stats: Optional[Dict[str, Any]] = None,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for organizing output files.

    Args:
        analysis_dir: Directory containing analysis outputs
        dry_run: If True, simulate organization
        create_index: Create INDEX.txt file
        create_readme: Create README.md file
        tool_stats: Optional dictionary with tool execution statistics
        verbose: Verbosity level

    Returns:
        Organization result dictionary or None on error
    """
    organizer = OutputOrganizer(analysis_dir)
    return organizer.organize(
        dry_run=dry_run,
        create_index=create_index,
        create_readme=create_readme,
        tool_stats=tool_stats,
        verbose=verbose
    )
