"""Inline the latest CHANGELOG.md version section into star.html.

star.html embeds the changelog content in a <script id="changelog-data">
block so it works from a file:// origin (no fetch CORS dance). Run this
script after updating CHANGELOG.md to refresh the embedded content.

Usage:  py -3 pyscript/update_star_html.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
STAR_HTML = ROOT / "star.html"

START_MARKER = '<script id="changelog-data" type="text/plain">'
END_MARKER   = '</script>'

def extract_latest_section(md: str) -> str:
    """Return the text of the latest `## [X.Y.Z]` section."""
    m = re.search(r'(## \[\d+(?:\.\d+){0,3}\][^\n]*\n)', md)
    if not m:
        sys.exit("ERROR: no `## [X.Y.Z]` heading found in CHANGELOG.md")
    start = m.start()
    after_first = start + len(m.group())
    m2 = re.search(r'\n## \[\d', md[after_first:])
    end = after_first + m2.start() if m2 else len(md)
    return md[start:end].rstrip()

def main() -> None:
    md = CHANGELOG.read_text(encoding="utf-8")
    section = extract_latest_section(md)
    print(f"Latest section: {section.splitlines()[0]} ({len(section)} chars)")

    html = STAR_HTML.read_text(encoding="utf-8")
    if START_MARKER not in html:
        sys.exit(f"ERROR: {STAR_HTML.name} has no {START_MARKER} block to update")

    # Replace the contents of the script block (anything between the
    # opening tag and the next </script> following it).
    pre, _, after = html.partition(START_MARKER)
    inside, _, post = after.partition(END_MARKER)
    new_html = pre + START_MARKER + "\n" + section + "\n" + END_MARKER + post
    STAR_HTML.write_text(new_html, encoding="utf-8")
    print(f"Updated {STAR_HTML.name} ({len(new_html)} bytes)")

if __name__ == "__main__":
    main()
