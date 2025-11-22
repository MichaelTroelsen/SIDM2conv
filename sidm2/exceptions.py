"""
Custom exceptions for SID to SF2 conversion.
"""


class SIDError(Exception):
    """Base exception for SID operations"""
    pass


class SIDParseError(SIDError):
    """Error parsing SID file"""
    pass


class TableExtractionError(SIDError):
    """Error extracting table data"""
    pass


class SF2WriteError(SIDError):
    """Error writing SF2 file"""
    pass


class InvalidSIDFileError(SIDParseError):
    """Invalid or corrupted SID file"""
    pass


class UnsupportedPlayerError(SIDError):
    """SID uses unsupported player format"""
    pass


class TemplateNotFoundError(SF2WriteError):
    """Required SF2 template not found"""
    pass
