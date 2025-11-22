"""Custom exceptions for audio transcription service"""


class AudioTranscriberError(Exception):
    """Base exception for audio transcriber errors"""
    pass


class TranscriptionError(AudioTranscriberError):
    """Raised when transcription fails"""
    pass


class ConfigurationError(AudioTranscriberError):
    """Raised when configuration is invalid"""
    pass


class StorageError(AudioTranscriberError):
    """Raised when storage operations fail"""
    pass
