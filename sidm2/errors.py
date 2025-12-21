"""
User-friendly error messages with troubleshooting guidance.

This module provides enhanced exception classes that include:
- Clear error explanations
- Common causes
- Step-by-step solutions
- Documentation links
- Alternative approaches

Example usage:
    from sidm2.errors import FileNotFoundError

    if not os.path.exists(input_path):
        raise FileNotFoundError(
            path=input_path,
            context="input SID file",
            suggestions=[
                "Check the file path with --help",
                "Use absolute path",
                "List files: ls SID/"
            ],
            docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md"
        )

Version: 1.0.0
"""

import os
import sys
import difflib
from pathlib import Path
from typing import List, Optional, Dict, Any


# Color codes for terminal output (optional, graceful degradation)
class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def is_enabled() -> bool:
        """Check if colors should be enabled (not on Windows without ANSICON)."""
        return sys.platform != 'win32' or 'ANSICON' in os.environ


def colorize(text: str, color: str) -> str:
    """Colorize text if colors are enabled."""
    if Colors.is_enabled():
        return f"{color}{text}{Colors.ENDC}"
    return text


class SIDMError(Exception):
    """
    Base exception for SIDM2 converter with rich formatting.

    All SIDM2 errors should inherit from this class to ensure
    consistent, user-friendly error messages.

    Args:
        message: Brief error title (e.g., "Input File Not Found")
        what_happened: Detailed explanation of what went wrong
        why_happened: List of common causes
        how_to_fix: List of step-by-step solutions
        docs_link: Relative path to documentation (will be made absolute)
        alternatives: List of alternative approaches
        technical_details: Optional technical details for debugging
    """

    def __init__(
        self,
        message: str,
        what_happened: Optional[str] = None,
        why_happened: Optional[List[str]] = None,
        how_to_fix: Optional[List[str]] = None,
        docs_link: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        technical_details: Optional[str] = None
    ):
        self.message = message
        self.what_happened = what_happened
        self.why_happened = why_happened or []
        self.how_to_fix = how_to_fix or []
        self.docs_link = docs_link
        self.alternatives = alternatives or []
        self.technical_details = technical_details

        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Format error message with troubleshooting guidance."""
        lines = []

        # Header with color
        header = f"ERROR: {self.message}"
        lines.append(f"\n{colorize(header, Colors.FAIL + Colors.BOLD)}\n")

        # What happened
        if self.what_happened:
            lines.append("What happened:")
            lines.append(f"  {self.what_happened}\n")

        # Why it happened
        if self.why_happened:
            lines.append("Why this happened:")
            for reason in self.why_happened:
                lines.append(f"  • {reason}")
            lines.append("")

        # How to fix
        if self.how_to_fix:
            lines.append(colorize("How to fix:", Colors.OKGREEN))
            for i, solution in enumerate(self.how_to_fix, 1):
                lines.append(f"  {i}. {solution}")
            lines.append("")

        # Alternatives
        if self.alternatives:
            lines.append("Alternative:")
            for alt in self.alternatives:
                if isinstance(alt, str):
                    lines.append(f"  {alt}")
                else:
                    lines.append(f"  • {alt}")
            lines.append("")

        # Documentation and help
        if self.docs_link or True:  # Always show help section
            lines.append(colorize("Need help?", Colors.OKCYAN))

            if self.docs_link:
                doc_url = self._make_doc_url(self.docs_link)
                lines.append(f"  * Documentation: {doc_url}")

            repo_url = "https://github.com/MichaelTroelsen/SIDM2conv"
            lines.append(f"  * Issues: {repo_url}/issues")
            lines.append(f"  * README: {repo_url}#readme\n")

        # Technical details (for debugging)
        if self.technical_details:
            lines.append(colorize("Technical details:", Colors.WARNING))
            lines.append(f"  {self.technical_details}\n")

        return "\n".join(lines)

    @staticmethod
    def _make_doc_url(relative_path: str) -> str:
        """Convert relative doc path to GitHub URL."""
        base_url = "https://github.com/MichaelTroelsen/SIDM2conv/blob/master"
        # Handle both docs/ and root paths
        if not relative_path.startswith('docs/') and not relative_path.startswith('README'):
            relative_path = f"docs/{relative_path}"
        return f"{base_url}/{relative_path}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/serialization."""
        return {
            'type': self.__class__.__name__,
            'message': self.message,
            'what_happened': self.what_happened,
            'why_happened': self.why_happened,
            'how_to_fix': self.how_to_fix,
            'docs_link': self.docs_link,
            'alternatives': self.alternatives,
            'technical_details': self.technical_details
        }


class FileNotFoundError(SIDMError):
    """
    File not found error with suggestions for similar files.

    This error includes:
    - Suggestions for similar filenames
    - Absolute path recommendation
    - Directory listing command
    - Common causes

    Args:
        path: Path to file that was not found
        context: Description of what the file is (e.g., "input SID file")
        suggestions: Optional list of custom suggestions
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        path: str,
        context: str = "file",
        suggestions: Optional[List[str]] = None,
        docs_link: Optional[str] = None
    ):
        self.path = path
        self.context = context

        # Find similar files
        similar = self._find_similar_files(path)

        what_happened = f"Could not find the {context}: {path}"

        why_happened = [
            "File path may be incorrect or contains typos",
            "File may have been moved or deleted",
            "Working directory may be wrong",
            "Using relative path when absolute is needed"
        ]

        # Default suggestions if none provided
        if suggestions is None:
            abs_path = os.path.abspath(path)
            directory = os.path.dirname(path) or "."

            suggestions = [
                f"Check the file exists: ls {path} (or dir {path} on Windows)",
                f"Use absolute path: {abs_path}",
                f"List directory contents: ls {directory}/ (or dir {directory}\\ on Windows)",
                "Check current directory: pwd (or cd on Windows)"
            ]

        alternatives = None
        if similar:
            alternatives = ["Similar files found in the same directory:"]
            alternatives.extend([f"  • {f}" for f in similar[:5]])

        super().__init__(
            message=f"{context.title()} Not Found",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md#1-file-not-found-issues",
            alternatives=alternatives,
            technical_details=f"Full path checked: {os.path.abspath(path)}"
        )

    @staticmethod
    def _find_similar_files(path: str, threshold: float = 0.6) -> List[str]:
        """
        Find files with similar names in the same directory.

        Args:
            path: Path to file to find matches for
            threshold: Similarity threshold (0.0 to 1.0)

        Returns:
            List of similar filenames with paths
        """
        try:
            directory = os.path.dirname(path) or "."
            filename = os.path.basename(path)

            if not os.path.exists(directory):
                return []

            # Get all files in directory
            files = [
                f for f in os.listdir(directory)
                if os.path.isfile(os.path.join(directory, f))
            ]

            # Find similar filenames using difflib
            matches = difflib.get_close_matches(
                filename,
                files,
                n=5,
                cutoff=threshold
            )

            # Return with full paths
            return [os.path.join(directory, m) for m in matches]

        except Exception:
            return []


class InvalidInputError(SIDMError):
    """
    Invalid input error with validation guidance.

    Use this for:
    - Invalid file formats
    - Corrupted data
    - Unsupported formats
    - Failed validation

    Args:
        input_type: Type of input (e.g., "SID file", "configuration")
        value: The invalid value
        expected: Description of what was expected
        got: Description of what was received
        suggestions: Optional list of suggestions
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        input_type: str,
        value: Any,
        expected: Optional[str] = None,
        got: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        docs_link: Optional[str] = None
    ):
        what_happened = f"The {input_type} is invalid or not supported"

        if expected and got:
            what_happened += f"\n  Expected: {expected}\n  Got: {got}"

        why_happened = [
            f"{input_type} format is incorrect",
            f"{input_type} is corrupted or incomplete",
            f"{input_type} is not supported",
            "File downloaded incorrectly or truncated"
        ]

        if suggestions is None:
            suggestions = [
                f"Verify the {input_type} is valid",
                "Try re-downloading or re-creating the file",
                "Check file size and format",
                "Use a validation tool if available"
            ]

        super().__init__(
            message=f"Invalid {input_type}",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md#2-invalid-sid-files",
            technical_details=f"Value: {value}"
        )


class MissingDependencyError(SIDMError):
    """
    Missing dependency error with installation instructions.

    Use this for:
    - Missing Python modules
    - Missing external tools
    - Missing system libraries

    Args:
        dependency: Name of missing dependency
        install_command: Command to install dependency
        alternatives: Optional list of alternative approaches
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        dependency: str,
        install_command: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
        docs_link: Optional[str] = None
    ):
        what_happened = f"Required dependency not available: {dependency}"

        why_happened = [
            f"{dependency} is not installed",
            "Installation is incomplete",
            "Python path is not configured correctly",
            "Virtual environment is not activated"
        ]

        suggestions = []

        if install_command:
            suggestions.append(f"Install dependency: {install_command}")

        suggestions.extend([
            f"Verify installation: python -c 'import {dependency}'",
            "Check Python path: python -c 'import sys; print(sys.path)'",
            "Reinstall package: pip install -e .",
            "Check requirements: cat requirements.txt"
        ])

        super().__init__(
            message=f"Missing Dependency: {dependency}",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md#3-missing-dependencies",
            alternatives=alternatives
        )


class PermissionError(SIDMError):
    """
    Permission/access error with platform-specific guidance.

    Use this for:
    - Cannot read file
    - Cannot write file
    - Cannot create directory
    - Access denied

    Args:
        operation: Operation that failed (e.g., "read", "write")
        path: Path that couldn't be accessed
        platform_hints: Platform-specific suggestions
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        operation: str,
        path: str,
        platform_hints: Optional[Dict[str, List[str]]] = None,
        docs_link: Optional[str] = None
    ):
        what_happened = f"Permission denied while trying to {operation}: {path}"

        why_happened = [
            "Insufficient permissions for the operation",
            "File/directory is locked by another process",
            "File/directory is read-only",
            "Running without administrator/sudo privileges"
        ]

        # Detect platform
        platform = sys.platform

        # Platform-specific suggestions
        if platform_hints and platform in platform_hints:
            suggestions = platform_hints[platform]
        else:
            if platform == 'win32':
                suggestions = [
                    "Run as Administrator: Right-click → Run as administrator",
                    f"Check file properties: Right-click {path} → Properties → Security",
                    "Close programs that may be using the file",
                    f"Try different location: Use C:\\Users\\YourName\\Documents"
                ]
            else:  # Linux/Mac
                suggestions = [
                    f"Check permissions: ls -la {path}",
                    f"Change permissions: chmod 644 {path} (or 755 for directories)",
                    f"Use sudo if needed: sudo python scripts/...",
                    f"Change ownership: sudo chown $USER {path}"
                ]

        super().__init__(
            message=f"Permission Denied ({operation})",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md#5-permission-problems",
            technical_details=f"Platform: {platform}, Path: {os.path.abspath(path)}"
        )


class ConfigurationError(SIDMError):
    """
    Configuration error with examples and validation.

    Use this for:
    - Invalid configuration values
    - Missing required config
    - Conflicting settings

    Args:
        setting: Name of configuration setting
        value: Invalid value
        valid_options: List of valid options
        example: Example of correct configuration
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        setting: str,
        value: Any,
        valid_options: Optional[List[str]] = None,
        example: Optional[str] = None,
        docs_link: Optional[str] = None
    ):
        what_happened = f"Invalid configuration for '{setting}': {value}"

        why_happened = [
            f"'{value}' is not a valid option for '{setting}'",
            "Configuration file may be outdated",
            "Typo in configuration value",
            "Using incompatible settings together"
        ]

        suggestions = []

        if valid_options:
            options_str = ", ".join(valid_options)
            suggestions.append(f"Use one of: {options_str}")

        if example:
            suggestions.append(f"Example: {example}")

        suggestions.extend([
            "Check configuration file syntax",
            "Refer to documentation for valid options",
            "Use default configuration to test"
        ])

        alternatives = None
        if valid_options:
            alternatives = [
                "Valid options:",
                *[f"  • {opt}" for opt in valid_options]
            ]

        super().__init__(
            message=f"Invalid Configuration: {setting}",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md",
            alternatives=alternatives,
            technical_details=f"Setting: {setting}, Value: {value}"
        )


class ConversionError(SIDMError):
    """
    Conversion error with diagnosis and recovery.

    Use this for:
    - SID to SF2 conversion failures
    - SF2 to SID packing failures
    - Data extraction failures

    Args:
        stage: Stage where conversion failed
        reason: Reason for failure
        input_file: Input file that failed
        suggestions: Optional recovery suggestions
        docs_link: Optional documentation link
    """

    def __init__(
        self,
        stage: str,
        reason: str,
        input_file: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        docs_link: Optional[str] = None
    ):
        what_happened = f"Conversion failed during {stage}"

        if input_file:
            what_happened += f"\n  File: {input_file}"

        what_happened += f"\n  Reason: {reason}"

        why_happened = [
            f"Error during {stage} stage",
            "Input file may be incompatible",
            "Unsupported player format",
            "Corrupted or incomplete data"
        ]

        if suggestions is None:
            suggestions = [
                "Check if file is a valid SID file: tools/player-id.exe input.sid",
                "Try a different driver: --driver driver11 or --driver np20",
                "Enable debug logging: --verbose",
                "Report issue with file details"
            ]

        super().__init__(
            message=f"Conversion Failed: {stage}",
            what_happened=what_happened,
            why_happened=why_happened,
            how_to_fix=suggestions,
            docs_link=docs_link or "guides/TROUBLESHOOTING.md#4-conversion-failures",
            technical_details=f"Stage: {stage}, Reason: {reason}"
        )


# Convenience function for common errors
def file_not_found(path: str, context: str = "file", **kwargs) -> FileNotFoundError:
    """Convenience function to raise FileNotFoundError."""
    return FileNotFoundError(path=path, context=context, **kwargs)


def invalid_input(input_type: str, value: Any, **kwargs) -> InvalidInputError:
    """Convenience function to raise InvalidInputError."""
    return InvalidInputError(input_type=input_type, value=value, **kwargs)


def missing_dependency(dependency: str, **kwargs) -> MissingDependencyError:
    """Convenience function to raise MissingDependencyError."""
    return MissingDependencyError(dependency=dependency, **kwargs)


def permission_denied(operation: str, path: str, **kwargs) -> PermissionError:
    """Convenience function to raise PermissionError."""
    return PermissionError(operation=operation, path=path, **kwargs)


def config_error(setting: str, value: Any, **kwargs) -> ConfigurationError:
    """Convenience function to raise ConfigurationError."""
    return ConfigurationError(setting=setting, value=value, **kwargs)


def conversion_failed(stage: str, reason: str, **kwargs) -> ConversionError:
    """Convenience function to raise ConversionError."""
    return ConversionError(stage=stage, reason=reason, **kwargs)
