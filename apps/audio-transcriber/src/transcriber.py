"""Audio transcription using OpenAI SDK or WhisperX native API"""
import logging
import os
import json
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional, List, Tuple
from openai import OpenAI
from . import config
from .exceptions import TranscriptionError
from .splitter import AudioSplitter

logger = logging.getLogger(__name__)


def _create_multipart_form(file_path: str, language: Optional[str], align: bool, diarize: bool,
                           min_speakers: Optional[int], max_speakers: Optional[int]) -> Tuple[bytes, str]:
    """Create multipart/form-data request body for WhisperX API"""
    import uuid
    boundary = f'----WebKitFormBoundary{uuid.uuid4().hex}'

    body_parts = []

    # Add file part
    filename = os.path.basename(file_path)
    with open(file_path, 'rb') as f:
        file_data = f.read()

    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: audio/mpeg\r\n\r\n'.encode('utf-8') + file_data + b'\r\n'
    )

    # Add language if specified
    if language and language != 'auto':
        body_parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="language"\r\n\r\n'
            f'{language}\r\n'.encode('utf-8')
        )

    # Add align parameter
    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="align"\r\n\r\n'
        f'{"true" if align else "false"}\r\n'.encode('utf-8')
    )

    # Add diarize parameter
    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="diarize"\r\n\r\n'
        f'{"true" if diarize else "false"}\r\n'.encode('utf-8')
    )

    # Add speaker parameters if diarization is enabled
    if diarize:
        if min_speakers is not None:
            body_parts.append(
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="min_speakers"\r\n\r\n'
                f'{min_speakers}\r\n'.encode('utf-8')
            )
        if max_speakers is not None:
            body_parts.append(
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="max_speakers"\r\n\r\n'
                f'{max_speakers}\r\n'.encode('utf-8')
            )

    # Close boundary
    body_parts.append(f'--{boundary}--\r\n'.encode('utf-8'))

    body = b''.join(body_parts)
    content_type = f'multipart/form-data; boundary={boundary}'

    return body, content_type


class AudioTranscriber:
    """Audio transcription supporting OpenAI SDK and WhisperX native API"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        language: Optional[str] = None,
        timeout: Optional[int] = None,
        api_type: Optional[str] = None
    ):
        """
        Initialize the transcriber with configuration

        Args:
            base_url: Whisper API base URL (e.g., http://localhost:9000/v1 or http://whisperx:8000)
            api_key: API key for authentication
            model: Whisper model to use
            language: Language code for transcription (or 'auto')
            timeout: Request timeout in seconds
            api_type: API type ('openai' or 'whisperx')
        """
        self.api_type = api_type or config.WHISPER_API_TYPE
        self.base_url = base_url or config.WHISPER_BASE_URL
        self.api_key = api_key or config.WHISPER_API_KEY
        self.model = model or config.WHISPER_MODEL
        self.language = language or config.WHISPER_LANGUAGE
        self.timeout = timeout or config.WHISPER_TIMEOUT

        # WhisperX-specific settings
        self.whisperx_align = config.WHISPERX_ALIGN
        self.whisperx_diarize = config.WHISPERX_DIARIZE
        self.whisperx_min_speakers = int(config.WHISPERX_MIN_SPEAKERS) if config.WHISPERX_MIN_SPEAKERS else None
        self.whisperx_max_speakers = int(config.WHISPERX_MAX_SPEAKERS) if config.WHISPERX_MAX_SPEAKERS else None

        # Initialize OpenAI client only for OpenAI API type
        self.client = None
        if self.api_type == 'openai':
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )

        logger.info(f"AudioTranscriber initialized with API type: {self.api_type}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Model: {self.model}, Language: {self.language}")
        if self.api_type == 'whisperx':
            logger.info(f"WhisperX settings: align={self.whisperx_align}, diarize={self.whisperx_diarize}")

    def transcribe(
        self,
        audio_path: str,
        output_path: Optional[str] = None
    ) -> Dict:
        """
        Transcribe an audio file using the configured Whisper API

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
        logger.info(f"Using API type: {self.api_type}, language: {self.language}")

        # Route to appropriate implementation
        if self.api_type == 'whisperx':
            result = self._transcribe_whisperx(audio_path, file_size_mb)
        else:
            result = self._transcribe_openai(audio_path, file_size_mb)

        # Save result if output path provided
        if output_path:
            self._save_result(result, output_path)

        return result

    def _transcribe_openai(self, audio_path: str, file_size_mb: float) -> Dict:
        """Transcribe using OpenAI SDK (OpenAI-compatible APIs)"""
        logger.info(f"Using OpenAI SDK with model: {self.model}")

        try:
            with open(audio_path, 'rb') as audio_file:
                response = self.client.audio.transcriptions.create(
                    model=self.model,
                    language=self.language if self.language != 'auto' else None,
                    file=audio_file
                )

            result = {
                'text': response.text,
                '_metadata': {
                    'audio_file': os.path.basename(audio_path),
                    'file_size_mb': round(file_size_mb, 2),
                    'model': self.model,
                    'language': self.language,
                    'api_type': 'openai'
                }
            }

            logger.info("Transcription successful (OpenAI)")
            self._log_preview(result.get('text', ''))
            return result

        except Exception as e:
            error_msg = f"OpenAI transcription failed: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)

    def _transcribe_whisperx(self, audio_path: str, file_size_mb: float) -> Dict:
        """Transcribe using WhisperX native API"""
        logger.info(f"Using WhisperX API at {self.base_url}")

        try:
            # Build the WhisperX endpoint URL
            base = self.base_url.rstrip('/')
            url = f"{base}/transcribe"

            # Create multipart form data
            body, content_type = _create_multipart_form(
                file_path=audio_path,
                language=self.language if self.language != 'auto' else None,
                align=self.whisperx_align,
                diarize=self.whisperx_diarize,
                min_speakers=self.whisperx_min_speakers,
                max_speakers=self.whisperx_max_speakers
            )

            # Create request
            request = urllib.request.Request(url, data=body, method='POST')
            request.add_header('Content-Type', content_type)
            request.add_header('Content-Length', str(len(body)))

            logger.info(f"Sending request to {url}")

            # Send request with timeout
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                response_data = json.loads(response.read().decode('utf-8'))

            # Extract text from WhisperX response
            # WhisperX returns: {"segments": [...], "language": "...", "word_segments": [...]}
            segments = response_data.get('segments', [])
            text = ' '.join(seg.get('text', '').strip() for seg in segments)

            result = {
                'text': text,
                'segments': segments,
                'language': response_data.get('language'),
                'word_segments': response_data.get('word_segments'),
                '_metadata': {
                    'audio_file': os.path.basename(audio_path),
                    'file_size_mb': round(file_size_mb, 2),
                    'model': 'whisperx',
                    'language': self.language,
                    'api_type': 'whisperx',
                    'align': self.whisperx_align,
                    'diarize': self.whisperx_diarize
                }
            }

            logger.info("Transcription successful (WhisperX)")
            self._log_preview(text)
            return result

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'No response body'
            error_msg = f"WhisperX HTTP error {e.code}: {e.reason}. Body: {error_body}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)
        except urllib.error.URLError as e:
            error_msg = f"WhisperX URL error: {e.reason}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)
        except Exception as e:
            error_msg = f"WhisperX transcription failed: {e}"
            logger.error(error_msg)
            raise TranscriptionError(error_msg)

    def _log_preview(self, text: str) -> None:
        """Log a preview of the transcription text"""
        if text:
            text_preview = text[:200] + '...' if len(text) > 200 else text
            logger.info(f"Transcription preview: {text_preview}")

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
        if self.api_type == 'whisperx':
            return self._verify_whisperx_endpoint()
        else:
            return self._verify_openai_endpoint()

    def _verify_openai_endpoint(self) -> bool:
        """Verify OpenAI-compatible endpoint"""
        try:
            models = self.client.models.list()
            logger.info(f"OpenAI endpoint is accessible: {self.base_url}")
            logger.info(f"Available models: {[m.id for m in models.data]}")
            return True
        except Exception as e:
            logger.warning(f"Could not verify OpenAI endpoint (may still work): {e}")
            return True

    def _verify_whisperx_endpoint(self) -> bool:
        """Verify WhisperX endpoint by checking /docs or /openapi.json"""
        try:
            base = self.base_url.rstrip('/')
            url = f"{base}/openapi.json"
            request = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status == 200:
                    logger.info(f"WhisperX endpoint is accessible: {self.base_url}")
                    return True
        except Exception as e:
            logger.warning(f"Could not verify WhisperX endpoint (may still work): {e}")
        return True
