"""Configuration for audio transcription service"""
import os

# Input Configuration
INPUT_DIR = os.environ.get('INPUT_DIR', '/data/compressed')
AUDIO_EXTENSIONS = os.environ.get('AUDIO_EXTENSIONS', '.mp3,.wav,.m4a,.flac,.ogg').split(',')

# Output Configuration
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/data/transcriptions')
OUTPUT_FORMAT = os.environ.get('OUTPUT_FORMAT', 'json')  # Options: 'json', 'text', 'srt', 'vtt'

# Whisper API Configuration
WHISPER_ENDPOINT = os.environ.get('WHISPER_ENDPOINT', 'http://localhost:9000/asr')
WHISPER_MODEL = os.environ.get('WHISPER_MODEL', 'base')
WHISPER_LANGUAGE = os.environ.get('WHISPER_LANGUAGE', 'en')
WHISPER_TASK = os.environ.get('WHISPER_TASK', 'transcribe')  # Options: 'transcribe', 'translate'
WHISPER_TIMEOUT = int(os.environ.get('WHISPER_TIMEOUT', '600'))  # 10 minutes default
WHISPER_WORD_TIMESTAMPS = os.environ.get('WHISPER_WORD_TIMESTAMPS', 'false').lower() == 'true'

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
