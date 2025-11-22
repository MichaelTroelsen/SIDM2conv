"""
SF2 file writer - writes SID Factory II project files.

This module is imported from the main sid_to_sf2.py to maintain
all the complex SF2 writing functionality in one place.
"""

# The SF2Writer class is complex and tightly coupled with the main converter.
# For now, we import it from the original file to avoid duplication.
# Future work: fully modularize this class.

import sys
import os

# Add parent directory to path for importing from sid_to_sf2
_parent_dir = os.path.dirname(os.path.dirname(__file__))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Import the SF2Writer class from the original module
# This is a temporary measure until full modularization is complete
try:
    from sid_to_sf2 import SF2Writer
except ImportError:
    # If circular import occurs, define a placeholder
    class SF2Writer:
        """Placeholder SF2Writer - import from sid_to_sf2.py directly"""
        def __init__(self, *args, **kwargs):
            raise ImportError("Please import SF2Writer from sid_to_sf2.py directly")
