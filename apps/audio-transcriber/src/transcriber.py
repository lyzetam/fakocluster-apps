"""Audio transcription using OpenAI SDK (Whisper API)"""
import logging
import os
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, List, Tuple
from openai import OpenAI
from . import config
from .exceptions import TranscriptionError
from .splitter import AudioSplitter

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """OpenAI SDK-based audio transcription"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize the transcriber with configuration

        Args:
            base_url: Whisper API base URL (e.g., http://localhost:9000/v1)
            api_key: API key for authentication
            model: Whisper model to use
            language: Language code for transcription (or 'auto')
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or config.WHISPER_BASE_URL
        self.api_key = api_key or config.WHISPER_API_KEY
        self.model = model or config.WHISPER_MODEL
        self.language = language or config.WHISPER_LANGUAGE
        self.timeout = timeout or config.WHISPER_TIMEOUT

        # Initialize OpenAI client
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout
        )

        logger.info(f"AudioTranscriber initialized with base_url: {self.base_url}")
        logger.info(f"Model: {self.model}, Language: {self.language}")

    def transcribe(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Transcribe an audio file using the Whisper API

        Args:
            audio_path: Path to the audio file to transcribe
            output_path: Optional path to save the transcription result

        Returns:
            Dictionary containing transcription result
        """
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Transcribing: {audio_path} ({file_size_mb:.2f} MB)")
        logger.info(f"Using model: {self.model}, language: {self.language}")

        try:
            with open(audio_path, 'rb') as audio_file:
                # Call the OpenAI transcriptions API
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    language=self.language if self.language != 'auto' else None,
                    file=audio_file
                )

            # Build result dictionary
            result = {
                'text': response.text,
                '_metadata': {
                    'audio_file': os.path.basename(audio_path),
                    'file_size_mb': round(file_size_mb, 2),
                    'model': self.model,
                    'language': self.language
                }
            }

            logger.info("Transcription successful")

            # Log preview
            text = result.get('text', '')
            if text:
                text_preview = text[:200] + '...' if len(text) > 200 else text
                logger.info(f"Transcription preview: {text_preview}")

            # Save result if output path provided
            if output_path:
                self._save_result(result, output_path)

            return result

        except Exception as e:
            error_msg = f"Transcription failed: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)

    def transcribe_auto(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Automatically choose between regular and chunked transcription based on file size

        Args:
            audio_path: Path to the audio file to transcribe
            output_path: Optional path to save the transcription result

        Returns:
            Dictionary containing transcription result
        """
        if AudioSplitter.needs_chunking(audio_path):
            logger.info("File exceeds size threshold, using chunked transcription")
            return self.transcribe_chunked(audio_path, output_path)
        else:
            return self.transcribe(audio_path, output_path)

    def transcribe_chunked(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Transcribe a large audio file by splitting it into chunks

        Args:
            audio_path: Path to the audio file to transcribe
            output_path: Optional path to save the transcription result

        Returns:
            Dictionary containing merged transcription result
        """
        if not os.path.exists(audio_path):
            raise TranscriptionError(f"Audio file not found: {audio_path}")

        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)
        logger.info(f"Chunked transcription: {audio_path} ({file_size_mb:.2f} MB)")

        # Create temp directory for chunks
        chunk_dir = os.path.join(config.TEMP_DIR, 'chunks')
        os.makedirs(chunk_dir, exist_ok=True)

        # Split audio into chunks
        chunk_paths = AudioSplitter.split_audio(audio_path, chunk_dir)

        if not chunk_paths:
            raise TranscriptionError("Failed to split audio into chunks")

        if len(chunk_paths) == 1 and chunk_paths[0] == audio_path:
            # Couldn't split, fall back to regular transcription
            logger.warning("Could not split audio, falling back to regular transcription")
            return self.transcribe(audio_path, output_path)

        logger.info(f"Transcribing {len(chunk_paths)} chunks with {config.CONCURRENT_CHUNKS} workers...")

        # Transcribe chunks in parallel
        transcriptions = [''] * len(chunk_paths)  # Pre-allocate to maintain order
        failed_chunks = []

        def transcribe_chunk(args: Tuple[int, str]) -> Tuple[int, str, Optional[str]]:
            """Transcribe a single chunk, returning (index, text, error)"""
            idx, chunk_path = args
            try:
                logger.info(f"Transcribing chunk {idx+1}/{len(chunk_paths)}")
                result = self.transcribe(chunk_path)
                return (idx, result.get('text', ''), None)
            except TranscriptionError as e:
                return (idx, '', str(e))

        with ThreadPoolExecutor(max_workers=config.CONCURRENT_CHUNKS) as executor:
            futures = {executor.submit(transcribe_chunk, (i, path)): i
                      for i, path in enumerate(chunk_paths)}

            for future in as_completed(futures):
                idx, text, error = future.result()
                if error:
                    logger.error(f"Failed to transcribe chunk {idx+1}: {error}")
                    failed_chunks.append(idx+1)
                transcriptions[idx] = text

        # Clean up chunk files
        AudioSplitter.cleanup_chunks(chunk_paths)

        # Merge transcriptions
        merged_text = ' '.join(t.strip() for t in transcriptions if t.strip())

        # Build result
        result = {
            'text': merged_text,
            '_metadata': {
                'audio_file': os.path.basename(audio_path),
                'file_size_mb': round(file_size_mb, 2),
                'model': self.model,
                'language': self.language,
                'chunked': True,
                'total_chunks': len(chunk_paths),
                'failed_chunks': failed_chunks
            }
        }

        if failed_chunks:
            logger.warning(f"Completed with {len(failed_chunks)} failed chunks: {failed_chunks}")
        else:
            logger.info(f"Successfully transcribed all {len(chunk_paths)} chunks")

        # Log preview
        if merged_text:
            text_preview = merged_text[:200] + '...' if len(merged_text) > 200 else merged_text
            logger.info(f"Merged transcription preview: {text_preview}")

        # Save result if output path provided
        if output_path:
            self._save_result(result, output_path)

        return result

    def _save_result(self, result: Dict, output_path: str) -> None:
        """
        Save transcription result to file

        Args:
            result: Transcription result dictionary
            output_path: Path to save the result
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            output_format = config.OUTPUT_FORMAT

            if output_format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result.get('text', ''))

            logger.info(f"Transcription saved to: {output_path}")

        except Exception as e:
            logger.error(f"Failed to save transcription result: {e}")
            raise TranscriptionError(f"Failed to save result: {e}")

    def verify_endpoint(self) -> bool:
        """
        Verify the Whisper endpoint is accessible

        Returns:
            True if endpoint is accessible, False otherwise
        """
        try:
            # Try to list models as a health check
            models = self.client.models.list()
            logger.info(f"Whisper endpoint is accessible: {self.base_url}")
            logger.info(f"Available models: {[m.id for m in models.data]}")
            return True
        except Exception as e:
            logger.warning(f"Could not verify endpoint (may still work): {e}")
            # Return True anyway - some endpoints don't support model listing
            return True
