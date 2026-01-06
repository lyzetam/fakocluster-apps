"""Configuration for audio transcription service"""
import os

# Input Configuration
INPUT_DIR = os.environ.get('INPUT_DIR', '/data/compressed')
AUDIO_EXTENSIONS = os.environ.get('AUDIO_EXTENSIONS', '.mp3,.wav,.m4a,.flac,.ogg').split(',')

# Output Configuration
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/data/transcriptions')
OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # Options: 'json', 'text', 'srt', 'vtt'

# Whisper API Configuration
WHISPER_API_TYPE = os.environ.get('WHISPER_API_TYPE', 'openai')  # Options: 'openai', 'whisperx'
WHISPER_BASE_URL = os.environ.get('WHISPER_BASE_URL', 'http://localhost:9000/v1')
WHISPER_API_KEY = os.environ.get('WHISPER_API_KEY')  # Required for OpenAI, optional for WhisperX
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'whisper-1')
WHISPER_LANGUAGE = os.environ.get('WHISPER_LANGUAGE', 'auto')
WHISPER_TIMEOUT = int(os.environ.get('WHISPER_TIMEOUT', '600'))  # 10 minutes default

# WhisperX-specific Configuration
WHISPERX_ALIGN = os.environ.get('WHISPERX_ALIGN', 'true').lower() == 'true'
WHISPERX_DIARIZE = os.environ.get('WHISPERX_DIARIZE', 'false').lower() == 'true'
WHISPERX_MIN_SPEAKERS = os.environ.get('WHISPERX_MIN_SPEAKERS')  # Optional int
WHISPERX_MAX_SPEAKERS = os.environ.get('WHISPERX_MAX_SPEAKERS')  # Optional int

# Processing Configuration
SKIP_PROCESSED = os.environ.get('SKIP_PROCESSED', 'true').lower() == 'true'
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '500'))  # Skip files larger than this
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '0'))  # 0 = process all, >0 = limit per run

# Audio Chunking Configuration
ENABLE_CHUNKING = os.environ.get('ENABLE_CHUNKING', 'true').lower() == 'true'
CHUNK_DURATION_SECONDS = int(os.environ.get('CHUNK_DURATION_SECONDS', '300'))  # 5 minutes per chunk
CHUNK_OVERLAP_SECONDS = int(os.environ.get('CHUNK_OVERLAP_SECONDS', '5'))  # Overlap for context
MAX_FILE_SIZE_FOR_CHUNKING_MB = int(os.environ.get('MAX_FILE_SIZE_FOR_CHUNKING_MB', '24'))  # Chunk files larger than this
CONCURRENT_CHUNKS = int(os.environ.get('CONCURRENT_CHUNKS', '4'))  # Parallel chunk transcription

# Retry Configuration
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.environ.get('RETRY_DELAY', '10'))  # seconds

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Temp directory for processing
TEMP_DIR = os.environ.get('TEMP_DIR', '/tmp/audio-transcription')
