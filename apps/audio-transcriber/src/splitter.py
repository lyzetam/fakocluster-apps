"""Audio splitting using FFmpeg"""
import logging
import os
import subprocess
import json
from typing import List, Tuple
from . import config

logger = logging.getLogger(__name__)


class AudioSplitter:
    """FFmpeg-based audio splitting for chunked transcription"""

    @staticmethod
    def get_audio_duration(file_path: str) -> float:
        """
        Get the duration of an audio file in seconds

        Args:
            file_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'json',
                    file_path
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False
            )

            if result.returncode == 0:
                data = json.loads(result.stdout.decode('utf-8'))
                duration = float(data.get('format', {}).get('duration', 0))
                return duration
            else:
                logger.warning(f"Failed to get duration for {file_path}")
                return 0

        except Exception as e:
            logger.warning(f"Error getting audio duration: {e}")
            return 0

    @staticmethod
    def needs_chunking(file_path: str) -> bool:
        """
        Check if a file needs to be chunked based on size

        Args:
            file_path: Path to audio file

        Returns:
            True if file should be chunked
        """
        if not config.ENABLE_CHUNKING:
            return False

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return file_size_mb > config.MAX_FILE_SIZE_FOR_CHUNKING_MB

    @staticmethod
    def split_audio(
        input_path: str,
        output_dir: str,
        chunk_duration: int = None,
        overlap: int = None
    ) -> List[str]:
        """
        Split an audio file into chunks using FFmpeg

        Args:
            input_path: Path to input audio file
            output_dir: Directory to save chunks
            chunk_duration: Duration of each chunk in seconds
            overlap: Overlap between chunks in seconds

        Returns:
            List of chunk file paths in order
        """
        chunk_duration = chunk_duration or config.CHUNK_DURATION_SECONDS
        overlap = overlap or config.CHUNK_OVERLAP_SECONDS

        # Get audio duration
        total_duration = AudioSplitter.get_audio_duration(input_path)
        if total_duration == 0:
            logger.error(f"Could not determine duration of {input_path}")
            return [input_path]  # Return original file if we can't get duration

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        logger.info(f"Splitting audio: {input_path}")
        logger.info(f"Total duration: {total_duration:.1f}s, Size: {file_size_mb:.2f} MB")
        logger.info(f"Chunk duration: {chunk_duration}s, Overlap: {overlap}s")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Calculate chunk start times
        chunks = []
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        ext = os.path.splitext(input_path)[1]

        start_time = 0
        chunk_index = 0

        while start_time < total_duration:
            # Calculate end time for this chunk
            end_time = min(start_time + chunk_duration, total_duration)
            actual_duration = end_time - start_time

            # Output file path
            chunk_path = os.path.join(
                output_dir,
                f"{base_name}_chunk_{chunk_index:03d}{ext}"
            )

            # Build FFmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(actual_duration),
                '-c', 'copy',  # Copy codec for speed
                '-y',  # Overwrite output
                chunk_path
            ]

            try:
                result = subprocess.run(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=120,
                    check=False
                )

                if result.returncode != 0:
                    stderr = result.stderr.decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg failed for chunk {chunk_index}: {stderr[-200:]}")
                    # Try without codec copy (re-encode)
                    ffmpeg_cmd_reencode = [
                        'ffmpeg',
                        '-i', input_path,
                        '-ss', str(start_time),
                        '-t', str(actual_duration),
                        '-y',
                        chunk_path
                    ]
                    result = subprocess.run(
                        ffmpeg_cmd_reencode,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=300,
                        check=False
                    )
                    if result.returncode != 0:
                        logger.error(f"Re-encode also failed for chunk {chunk_index}")
                        continue

                if os.path.exists(chunk_path):
                    chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)
                    logger.info(f"Created chunk {chunk_index}: {start_time:.1f}s - {end_time:.1f}s ({chunk_size_mb:.2f} MB)")
                    chunks.append(chunk_path)
                else:
                    logger.error(f"Chunk file not created: {chunk_path}")

            except subprocess.TimeoutExpired:
                logger.error(f"Timeout creating chunk {chunk_index}")
            except Exception as e:
                logger.error(f"Error creating chunk {chunk_index}: {e}")

            # Move to next chunk (with overlap consideration)
            start_time = end_time - overlap if end_time < total_duration else total_duration
            chunk_index += 1

        logger.info(f"Split complete: {len(chunks)} chunks created")
        return chunks

    @staticmethod
    def cleanup_chunks(chunk_paths: List[str]) -> None:
        """
        Clean up temporary chunk files

        Args:
            chunk_paths: List of chunk file paths to delete
        """
        for chunk_path in chunk_paths:
            try:
                if os.path.exists(chunk_path):
                    os.unlink(chunk_path)
                    logger.debug(f"Deleted chunk: {chunk_path}")
            except Exception as e:
                logger.warning(f"Failed to delete chunk {chunk_path}: {e}")

    @staticmethod
    def verify_ffmpeg() -> bool:
        """Verify FFmpeg is installed and accessible"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                check=False
            )

            if result.returncode == 0:
                version_info = result.stdout.decode('utf-8').split('\n')[0]
                logger.info(f"FFmpeg found: {version_info}")
                return True
            else:
                logger.error("FFmpeg command failed")
                return False

        except FileNotFoundError:
            logger.error("FFmpeg not found in PATH")
            return False
        except Exception as e:
            logger.error(f"Error checking FFmpeg: {e}")
            return False
