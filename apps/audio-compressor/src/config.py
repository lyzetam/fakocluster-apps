"""Configuration for audio compression service"""
import os

# SFTP Configuration
SFTP_HOST = os.environ.get('SFTP_HOST')
SFTP_PORT = int(os.environ.get('SFTP_PORT', '22'))
SFTP_REMOTE_PATH = os.environ.get('SFTP_REMOTE_PATH', '/audio')

# AWS Secrets Configuration
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
SFTP_SECRETS_NAME = os.environ.get('SFTP_SECRETS_NAME', 'sftp/audio-server')

# Storage Configuration
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/data/compressed')
KEEP_ORIGINALS = os.environ.get('KEEP_ORIGINALS', 'false').lower() == 'true'

# Storage Backend Configuration
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'local').lower()  # Options: 'local', 'sftp'
SFTP_DEST_PATH = os.environ.get('SFTP_DEST_PATH', '/compressed')  # Remote path when STORAGE_BACKEND='sftp'

# Upload Retry Configuration (for SFTP storage backend)
UPLOAD_RETRY_ATTEMPTS = int(os.environ.get('UPLOAD_RETRY_ATTEMPTS', '3'))
UPLOAD_RETRY_DELAY = int(os.environ.get('UPLOAD_RETRY_DELAY', '5'))  # seconds

# Compression Configuration
SAMPLE_RATE = int(os.environ.get('SAMPLE_RATE', '16000'))  # 16kHz for speech
CHANNELS = int(os.environ.get('CHANNELS', '1'))  # Mono
BITRATE = os.environ.get('BITRATE', '32k')  # 32 kbps
AUDIO_FORMAT = os.environ.get('AUDIO_FORMAT', 'mp3')  # mp3 for smaller files, wav for lossless

# Processing Configuration
AUDIO_FILENAME = os.environ.get('AUDIO_FILENAME', 'StereoMix.wav')
METADATA_FILENAME = os.environ.get('METADATA_FILENAME', 'Meta.xml')
COPY_METADATA = os.environ.get('COPY_METADATA', 'true').lower() == 'true'
SKIP_PROCESSED = os.environ.get('SKIP_PROCESSED', 'true').lower() == 'true'
DIR_PATTERN = os.environ.get('DIR_PATTERN', r'^\d{2}-\d{2}-\d{2}(-\d{2})?$')
MAX_FILE_SIZE_MB = int(os.environ.get('MAX_FILE_SIZE_MB', '10000'))  # Skip if larger (10 GB default)

# Retry Configuration
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY = int(os.environ.get('RETRY_DELAY', '5'))  # seconds

# Logging Configuration
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

# Temp directory for processing
TEMP_DIR = os.environ.get('TEMP_DIR', '/tmp/audio-processing')
