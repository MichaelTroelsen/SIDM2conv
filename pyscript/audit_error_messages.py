#!/usr/bin/env python3
"""
Error Message Audit Tool

Analyzes all error messages in the codebase and generates a report
with improvement suggestions.

Usage:
    python pyscript/audit_error_messages.py
    python pyscript/audit_error_messages.py --output report.md
    python pyscript/audit_error_messages.py --verbose
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
import argparse


class ErrorMessageAuditor:
    """Audit error messages in Python codebase"""

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.findings = defaultdict(list)

    def audit(self, directories: List[str] = None) -> Dict:
        """Audit all Python files in specified directories

        Args:
            directories: List of directories to audit (default: ['sidm2', 'scripts'])

        Returns:
            Dict with categorized findings
        """
        if directories is None:
            directories = ['sidm2', 'scripts']

        for directory in directories:
            dir_path = self.root_dir / directory
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob('*.py'):
                self._audit_file(py_file)

        return self._generate_report()

    def _audit_file(self, file_path: Path):
        """Audit a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            rel_path = file_path.relative_to(self.root_dir)

            # Pattern 1: Generic exceptions without context
            self._find_generic_exceptions(rel_path, lines)

            # Pattern 2: logger.error without suggestions
            self._find_bare_logger_errors(rel_path, lines)

            # Pattern 3: Missing documentation links
            self._find_missing_doc_links(rel_path, lines)

            # Pattern 4: Technical jargon without explanation
            self._find_technical_jargon(rel_path, lines)

            # Pattern 5: No alternative suggestions
            self._find_missing_alternatives(rel_path, lines)

        except Exception as e:
            print(f"Warning: Could not audit {file_path}: {e}")

    def _find_generic_exceptions(self, file_path: Path, lines: List[str]):
        """Find generic exceptions that should use rich error classes"""
        generic_patterns = [
            (r'raise\s+ValueError\s*\(', 'ValueError'),
            (r'raise\s+RuntimeError\s*\(', 'RuntimeError'),
            (r'raise\s+IOError\s*\(', 'IOError'),
            (r'raise\s+Exception\s*\(', 'Exception'),
            (r'raise\s+FileNotFoundError\s*\(', 'FileNotFoundError (stdlib)'),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, exc_type in generic_patterns:
                if re.search(pattern, line):
                    # Check if it's using rich error class
                    if 'sidm2.errors' not in '\n'.join(lines[:line_num]):
                        self.findings['generic_exceptions'].append({
                            'file': str(file_path),
                            'line': line_num,
                            'type': exc_type,
                            'code': line.strip(),
                            'severity': 'medium',
                            'suggestion': f'Replace with rich error class from sidm2.errors'
                        })

    def _find_bare_logger_errors(self, file_path: Path, lines: List[str]):
        """Find logger.error calls without structured information"""
        logger_pattern = r'logger\.(error|warning)\s*\('

        for line_num, line in enumerate(lines, 1):
            if re.search(logger_pattern, line):
                # Check if message provides actionable information
                has_suggestion = any(word in line.lower() for word in [
                    'try', 'use', 'check', 'run', 'install', 'see'
                ])

                has_doc_link = 'docs/' in line or 'TROUBLESHOOTING' in line

                if not (has_suggestion or has_doc_link):
                    self.findings['bare_logger_errors'].append({
                        'file': str(file_path),
                        'line': line_num,
                        'code': line.strip(),
                        'severity': 'low',
                        'suggestion': 'Add actionable suggestion or documentation link'
                    })

    def _find_missing_doc_links(self, file_path: Path, lines: List[str]):
        """Find error messages without documentation links"""
        error_patterns = [
            r'raise\s+\w+Error\s*\(',
            r'logger\.error\s*\(',
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern in error_patterns:
                if re.search(pattern, line):
                    # Check surrounding lines for doc links
                    context_start = max(0, line_num - 5)
                    context_end = min(len(lines), line_num + 5)
                    context = '\n'.join(lines[context_start:context_end])

                    has_doc_link = (
                        'docs/' in context or
                        'TROUBLESHOOTING' in context or
                        'docs_link' in context or
                        'README' in context
                    )

                    if not has_doc_link and 'test' not in str(file_path).lower():
                        self.findings['missing_doc_links'].append({
                            'file': str(file_path),
                            'line': line_num,
                            'code': line.strip(),
                            'severity': 'low',
                            'suggestion': 'Add documentation link for user reference'
                        })

    def _find_technical_jargon(self, file_path: Path, lines: List[str]):
        """Find technical jargon that needs explanation"""
        jargon_words = [
            'PSID', 'RSID', 'orderlist', 'sequence', 'waveform',
            'pulse width', 'filter cutoff', 'ADSR', 'gate',
            'transpose', 'arpeggio', 'vibrato'
        ]

        error_pattern = r'(raise\s+\w+Error|logger\.error)\s*\('

        for line_num, line in enumerate(lines, 1):
            if re.search(error_pattern, line):
                # Check if line contains jargon without explanation
                for jargon in jargon_words:
                    if jargon.lower() in line.lower():
                        # Check if there's an explanation nearby
                        context_start = max(0, line_num - 3)
                        context_end = min(len(lines), line_num + 3)
                        context = '\n'.join(lines[context_start:context_end])

                        has_explanation = (
                            'what_happened' in context or
                            'explanation' in context or
                            '"""' in context  # Docstring nearby
                        )

                        if not has_explanation:
                            self.findings['technical_jargon'].append({
                                'file': str(file_path),
                                'line': line_num,
                                'jargon': jargon,
                                'code': line.strip(),
                                'severity': 'low',
                                'suggestion': f'Explain technical term "{jargon}"'
                            })
                            break  # Only report once per line

    def _find_missing_alternatives(self, file_path: Path, lines: List[str]):
        """Find error messages without alternative suggestions"""
        error_pattern = r'raise\s+\w+Error\s*\('

        for line_num, line in enumerate(lines, 1):
            if re.search(error_pattern, line):
                # Check if alternatives are provided
                context_start = max(0, line_num - 10)
                context_end = min(len(lines), line_num + 10)
                context = '\n'.join(lines[context_start:context_end])

                has_alternatives = (
                    'alternatives' in context or
                    'alternative' in context or
                    'instead' in context or
                    'try.*instead' in context.lower()
                )

                if not has_alternatives and 'test' not in str(file_path).lower():
                    self.findings['missing_alternatives'].append({
                        'file': str(file_path),
                        'line': line_num,
                        'code': line.strip(),
                        'severity': 'low',
                        'suggestion': 'Consider providing alternative approach'
                    })

    def _generate_report(self) -> Dict:
        """Generate summary report"""
        total_issues = sum(len(issues) for issues in self.findings.values())

        summary = {
            'total_files_audited': len(set(
                f['file'] for category in self.findings.values()
                for f in category
            )),
            'total_issues': total_issues,
            'by_category': {
                category: len(issues)
                for category, issues in self.findings.items()
            },
            'by_severity': defaultdict(int),
            'findings': dict(self.findings)
        }

        # Count by severity
        for category in self.findings.values():
            for issue in category:
                severity = issue.get('severity', 'unknown')
                summary['by_severity'][severity] += 1

        return summary


def format_markdown_report(report: Dict) -> str:
    """Format audit report as Markdown"""
    lines = []

    lines.append("# Error Message Audit Report")
    lines.append("")
    lines.append(f"**Date**: {Path(__file__).stat().st_mtime}")
    lines.append(f"**Files Audited**: {report['total_files_audited']}")
    lines.append(f"**Total Issues Found**: {report['total_issues']}")
    lines.append("")

    # Summary by category
    lines.append("## Issues by Category")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for category, count in sorted(report['by_category'].items(),
                                   key=lambda x: x[1], reverse=True):
        category_name = category.replace('_', ' ').title()
        lines.append(f"| {category_name} | {count} |")
    lines.append("")

    # Summary by severity
    lines.append("## Issues by Severity")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for severity, count in sorted(report['by_severity'].items()):
        lines.append(f"| {severity.title()} | {count} |")
    lines.append("")

    # Detailed findings
    lines.append("## Detailed Findings")
    lines.append("")

    for category, issues in report['findings'].items():
        if not issues:
            continue

        category_name = category.replace('_', ' ').title()
        lines.append(f"### {category_name} ({len(issues)} issues)")
        lines.append("")

        # Group by file
        by_file = defaultdict(list)
        for issue in issues:
            by_file[issue['file']].append(issue)

        for file_path, file_issues in sorted(by_file.items()):
            lines.append(f"#### {file_path}")
            lines.append("")

            for issue in file_issues[:10]:  # Limit to 10 per file
                lines.append(f"**Line {issue['line']}** ({issue['severity']})")
                lines.append("```python")
                lines.append(issue['code'])
                lines.append("```")
                lines.append(f"**Suggestion**: {issue['suggestion']}")
                lines.append("")

            if len(file_issues) > 10:
                lines.append(f"*... and {len(file_issues) - 10} more issues in this file*")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    lines.append("### High Priority")
    lines.append("")
    lines.append("1. **Replace Generic Exceptions**")
    lines.append("   - Use `sidm2.errors` rich error classes")
    lines.append("   - Provide context, suggestions, and documentation links")
    lines.append("   - Example: Replace `ValueError` with `InvalidInputError`")
    lines.append("")
    lines.append("2. **Enhance Logger Errors**")
    lines.append("   - Add actionable suggestions to all error logs")
    lines.append("   - Include troubleshooting steps")
    lines.append("   - Link to relevant documentation")
    lines.append("")
    lines.append("### Medium Priority")
    lines.append("")
    lines.append("3. **Add Documentation Links**")
    lines.append("   - Link errors to TROUBLESHOOTING.md sections")
    lines.append("   - Provide direct links to relevant guides")
    lines.append("")
    lines.append("4. **Explain Technical Jargon**")
    lines.append("   - Define technical terms in error messages")
    lines.append("   - Provide context for domain-specific concepts")
    lines.append("")
    lines.append("### Low Priority")
    lines.append("")
    lines.append("5. **Add Alternative Approaches**")
    lines.append("   - Suggest fallback options")
    lines.append("   - Provide workarounds when available")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Audit error messages in SIDM2 codebase',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file for report (default: stdout)',
        type=Path
    )
    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Find root directory
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    print(f"Auditing error messages in: {root_dir}")
    print("=" * 60)

    # Run audit
    auditor = ErrorMessageAuditor(root_dir)
    report = auditor.audit()

    # Print summary
    print(f"\nFiles audited: {report['total_files_audited']}")
    print(f"Total issues found: {report['total_issues']}")
    print("\nIssues by category:")
    for category, count in sorted(report['by_category'].items(),
                                   key=lambda x: x[1], reverse=True):
        print(f"  {category.replace('_', ' ').title()}: {count}")

    # Generate output
    if args.format == 'markdown':
        output = format_markdown_report(report)
    else:  # json
        import json
        output = json.dumps(report, indent=2)

    # Write output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\nReport written to: {args.output}")
    else:
        print("\n" + "=" * 60)
        print(output)


if __name__ == '__main__':
    main()
