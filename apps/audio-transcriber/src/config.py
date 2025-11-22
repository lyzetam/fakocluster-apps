"""Configuration for audio transcription service"""
import os

# Input Configuration
INPUT_DIR = os.environ.get('INPUT_DIR', '/data/compressed')
AUDIO_EXTENSIONS = os.environ.get('AUDIO_EXTENSIONS', '.mp3,.wav,.m4a,.flac,.ogg').split(',')

# Output Configuration
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/data/transcriptions')
OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # Options: 'json', 'text', 'srt', 'vtt'

# Whisper API Configuration (OpenAI SDK format)
WHISPER_BASE_URL = os.environ.get('WHISPER_BASE_URL', 'http://localhost:9000/v1')
WHISPER_API_KEY = os.environ.get('WHISPER_API_KEY')  # Required - no default
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'whisper-1')
WHISPER_LANGUAGE = os.environ.get('WHISPER_LANGUAGE', 'auto')
WHISPER_TIMEOUT = int(os.environ.get('WHISPER_TIMEOUT', '600'))  # 10 minutes default

# Processing Configuration
SKIP_PROCESSED = os.environ.get('SKIP_PROCESSED', 'true').lower() == 'true'
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '500'))  # Skip files larger than this
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '0'))  # 0 = process all, >0 = limit per run

# Retry Configuration
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.environ.get('RETRY_DELAY', '10'))  # seconds

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Temp directory for processing
TEMP_DIR = os.environ.get('TEMP_DIR', '/tmp/audio-transcription')
