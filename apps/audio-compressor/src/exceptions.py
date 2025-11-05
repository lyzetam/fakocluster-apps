"""Custom exceptions for audio compression service"""


class AudioCompressorError(Exception):
    """Base exception for audio compressor errors"""
    pass


class SFTPConnectionError(AudioCompressorError):
    """Raised when SFTP connection fails"""
    pass


class AudioDownloadError(AudioCompressorError):
    """Raised when audio file download fails"""
    pass


class CompressionError(AudioCompressorError):
    """Raised when audio compression fails"""
    pass


class StorageError(AudioCompressorError):
    """Raised when writing to storage fails"""
    pass


class ConfigurationError(AudioCompressorError):
    """Raised when configuration is invalid"""
    pass
