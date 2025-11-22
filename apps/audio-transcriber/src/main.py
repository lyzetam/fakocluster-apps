"""Main entry point for audio transcription service"""
import logging
import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List

from . import config
from .transcriber import AudioTranscriber
from .exceptions import (
    AudioTranscriberError,
    TranscriptionError,
    ConfigurationError
)

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_configuration() -> None:
    """Validate required configuration"""
    required_configs = {
        'INPUT_DIR': config.INPUT_DIR,
        'OUTPUT_DIR': config.OUTPUT_DIR,
        'WHISPER_ENDPOINT': config.WHISPER_ENDPOINT,
    }

    missing = [key for key, value in required_configs.items() if not value]

    if missing:
        raise ConfigurationError(f"Missing required configuration: {', '.join(missing)}")

    # Check input directory exists
    if not os.path.exists(config.INPUT_DIR):
        raise ConfigurationError(f"Input directory does not exist: {config.INPUT_DIR}")

    logger.info("Configuration validated successfully")


def find_audio_files(input_dir: str) -> List[str]:
    """
    Find all audio files in the input directory

    Args:
        input_dir: Directory to scan for audio files

    Returns:
        List of audio file paths
    """
    audio_files = []
    extensions = [ext.strip().lower() for ext in config.AUDIO_EXTENSIONS]

    logger.info(f"Scanning {input_dir} for audio files...")
    logger.info(f"Looking for extensions: {extensions}")

    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            if any(filename.lower().endswith(ext) for ext in extensions):
                filepath = os.path.join(root, filename)

                # Check file size
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                if file_size_mb > config.MAX_FILE_SIZE_MB:
                    logger.warning(f"Skipping {filename} - too large ({file_size_mb:.1f} MB > {config.MAX_FILE_SIZE_MB} MB)")
                    continue

                audio_files.append(filepath)

    # Sort by modification time (oldest first)
    audio_files.sort(key=lambda x: os.path.getmtime(x))

    return audio_files


def get_output_path(audio_path: str) -> str:
    """
    Generate output path for transcription result

    Args:
        audio_path: Path to audio file

    Returns:
        Path to save transcription result
    """
    # Get relative path from input directory
    rel_path = os.path.relpath(audio_path, config.INPUT_DIR)

    # Change extension based on output format
    base_name = os.path.splitext(rel_path)[0]

    ext_map = {
        'json': '.json',
        'text': '.txt',
        'srt': '.srt',
        'vtt': '.vtt'
    }
    extension = ext_map.get(config.OUTPUT_FORMAT, '.json')

    return os.path.join(config.OUTPUT_DIR, base_name + extension)


def is_already_processed(audio_path: str) -> bool:
    """
    Check if audio file has already been transcribed

    Args:
        audio_path: Path to audio file

    Returns:
        True if already processed, False otherwise
    """
    if not config.SKIP_PROCESSED:
        return False

    output_path = get_output_path(audio_path)
    return os.path.exists(output_path)


def process_file(
    audio_path: str,
    transcriber: AudioTranscriber
) -> Dict:
    """
    Process a single audio file

    Args:
        audio_path: Path to audio file
        transcriber: AudioTranscriber instance

    Returns:
        Dictionary with processing result
    """
    filename = os.path.basename(audio_path)
    file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

    result = {
        'file': filename,
        'path': audio_path,
        'size_mb': round(file_size_mb, 2),
        'status': 'pending',
        'error': None,
        'duration_seconds': 0
    }

    logger.info(f"\n{'='*60}")
    logger.info(f"Processing: {filename} ({file_size_mb:.2f} MB)")
    logger.info(f"{'='*60}")

    # Check if already processed
    if is_already_processed(audio_path):
        logger.info(f"SKIPPED - Already transcribed")
        result['status'] = 'skipped'
        return result

    output_path = get_output_path(audio_path)
    start_time = time.time()

    # Retry logic
    last_error = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.info(f"Attempt {attempt}/{config.MAX_RETRIES}")

            # Transcribe
            transcription = transcriber.transcribe(audio_path, output_path)

            elapsed = time.time() - start_time
            result['status'] = 'success'
            result['duration_seconds'] = round(elapsed, 1)
            result['output_path'] = output_path

            # Get text length for stats
            text = transcription.get('text', '')
            result['text_length'] = len(text)
            result['word_count'] = len(text.split())

            logger.info(f"SUCCESS - Transcribed in {elapsed:.1f}s")
            logger.info(f"Output: {output_path}")
            logger.info(f"Words: {result['word_count']}")

            return result

        except TranscriptionError as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt} failed: {e}")

            if attempt < config.MAX_RETRIES:
                logger.info(f"Retrying in {config.RETRY_DELAY} seconds...")
                time.sleep(config.RETRY_DELAY)

        except Exception as e:
            last_error = str(e)
            logger.error(f"Unexpected error: {e}")
            break

    # All retries failed
    elapsed = time.time() - start_time
    result['status'] = 'failed'
    result['error'] = last_error
    result['duration_seconds'] = round(elapsed, 1)

    logger.error(f"FAILED - {filename}: {last_error}")

    return result


def main() -> int:
    """Main execution function"""
    start_time = time.time()

    logger.info("="*60)
    logger.info("Audio Transcription Service Starting")
    logger.info("="*60)
    logger.info(f"Start time: {datetime.now().isoformat()}")

    try:
        # Validate configuration
        validate_configuration()

        logger.info(f"Input directory: {config.INPUT_DIR}")
        logger.info(f"Output directory: {config.OUTPUT_DIR}")
        logger.info(f"Whisper endpoint: {config.WHISPER_ENDPOINT}")
        logger.info(f"Model: {config.WHISPER_MODEL}")
        logger.info(f"Language: {config.WHISPER_LANGUAGE}")
        logger.info(f"Output format: {config.OUTPUT_FORMAT}")

        # Create output directory
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

        # Initialize transcriber
        transcriber = AudioTranscriber()

        # Verify endpoint is accessible
        if not transcriber.verify_endpoint():
            logger.error("Whisper endpoint is not accessible")
            return 2

        # Find audio files
        audio_files = find_audio_files(config.INPUT_DIR)

        if not audio_files:
            logger.warning("No audio files found to transcribe")
            logger.info("Processing complete - no work to do")
            return 0

        logger.info(f"Found {len(audio_files)} audio files to process")

        # Apply batch size limit if configured
        if config.BATCH_SIZE > 0 and len(audio_files) > config.BATCH_SIZE:
            logger.info(f"Limiting to {config.BATCH_SIZE} files (batch size)")
            audio_files = audio_files[:config.BATCH_SIZE]

        # Process each file
        results = []
        for idx, audio_path in enumerate(audio_files, 1):
            logger.info(f"\nProgress: {idx}/{len(audio_files)}")
            result = process_file(audio_path, transcriber)
            results.append(result)

        # Generate summary report
        elapsed_time = time.time() - start_time

        logger.info("\n" + "="*60)
        logger.info("Transcription Summary")
        logger.info("="*60)

        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = sum(1 for r in results if r['status'] == 'failed')
        skipped_count = sum(1 for r in results if r['status'] == 'skipped')

        total_size_mb = sum(r['size_mb'] for r in results)
        total_words = sum(r.get('word_count', 0) for r in results if r['status'] == 'success')
        total_duration = sum(r.get('duration_seconds', 0) for r in results if r['status'] == 'success')

        logger.info(f"Total files found: {len(audio_files)}")
        logger.info(f"Successfully transcribed: {success_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Skipped (already done): {skipped_count}")
        logger.info(f"Total audio size: {total_size_mb:.2f} MB")
        logger.info(f"Total words transcribed: {total_words:,}")
        logger.info(f"Total transcription time: {total_duration:.1f}s")

        if success_count > 0 and total_duration > 0:
            avg_speed = total_size_mb / (total_duration / 60)
            logger.info(f"Average speed: {avg_speed:.2f} MB/min")

        logger.info(f"Total elapsed time: {elapsed_time:.1f}s")

        # List failed files if any
        if failed_count > 0:
            logger.warning("\nFailed files:")
            for result in results:
                if result['status'] == 'failed':
                    logger.warning(f"  - {result['file']}: {result['error']}")

        # Save manifest
        manifest_path = os.path.join(config.OUTPUT_DIR, 'manifest.json')
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(audio_files),
                'success': success_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'total_words': total_words,
                'elapsed_seconds': round(elapsed_time, 1)
            },
            'results': results
        }

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"\nManifest saved to: {manifest_path}")

        logger.info("\n" + "="*60)
        logger.info("Audio Transcription Service Complete")
        logger.info("="*60)

        # Return appropriate exit code
        if failed_count == len(audio_files):
            return 2  # Total failure
        elif failed_count > 0:
            return 1  # Partial failure
        else:
            return 0  # Success

    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        return 130
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        return 2
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
